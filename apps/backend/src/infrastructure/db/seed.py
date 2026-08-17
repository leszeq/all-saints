"""
Database seed – initial data.

Seeds:
1. PostgreSQL extensions (vector, pg_trgm, unaccent)
2. System roles and permissions
3. Initial Super Admin user
4. Reference data (liturgical calendars, states of life, etc.)

Run with: python -m src.infrastructure.db.seed
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import password_hasher
from src.domain.geography import models as geography_models  # noqa: F401
from src.domain.identity.models import (
    AuditAction,
    Permission,
    Role,
    RolePermission,
    SystemRole,
    User,
    UserRole,
    UserStatus,
)
from src.domain.liturgy.models import CalendarScope, LiturgicalCalendar
from src.domain.hagiography.models import StateOfLife
from src.domain.sources import models as source_models  # noqa: F401
from src.infrastructure.db.session import enable_pgvector, get_engine
from src.domain.base import Base

# ==============================================================================
# PERMISSIONS MATRIX
# ==============================================================================

PERMISSIONS: list[tuple[str, str, str]] = [
    # (resource, action, description)
    # Persons
    ("persons", "read", "Przeglądanie osób"),
    ("persons", "create", "Tworzenie nowych osób"),
    ("persons", "update", "Edycja osób"),
    ("persons", "delete", "Usuwanie osób"),
    ("persons", "publish", "Publikowanie osób"),
    ("persons", "restore", "Przywracanie usuniętych osób"),
    # Sources
    ("sources", "read", "Przeglądanie źródeł"),
    ("sources", "create", "Tworzenie źródeł"),
    ("sources", "update", "Edycja źródeł"),
    ("sources", "delete", "Usuwanie źródeł"),
    # Geography
    ("geography", "read", "Przeglądanie geografii"),
    ("geography", "create", "Tworzenie lokalizacji"),
    ("geography", "update", "Edycja lokalizacji"),
    ("geography", "delete", "Usuwanie lokalizacji"),
    # Orders
    ("orders", "read", "Przeglądanie zakonów"),
    ("orders", "create", "Tworzenie zakonów"),
    ("orders", "update", "Edycja zakonów"),
    ("orders", "delete", "Usuwanie zakonów"),
    # Images
    ("images", "read", "Przeglądanie zdjęć"),
    ("images", "create", "Dodawanie zdjęć"),
    ("images", "update", "Edycja zdjęć"),
    ("images", "delete", "Usuwanie zdjęć"),
    # Export
    ("export", "read", "Pobieranie eksportów"),
    ("export", "create", "Generowanie eksportów"),
    # Import
    ("import", "create", "Importowanie danych"),
    # Users
    ("users", "read", "Przeglądanie użytkowników"),
    ("users", "create", "Tworzenie użytkowników"),
    ("users", "update", "Edycja użytkowników"),
    ("users", "delete", "Usuwanie użytkowników"),
    # Roles
    ("roles", "read", "Przeglądanie ról"),
    ("roles", "create", "Tworzenie ról"),
    ("roles", "update", "Edycja ról"),
    ("roles", "delete", "Usuwanie ról"),
    # Audit
    ("audit", "read", "Przeglądanie logów audytu"),
    # Translations
    ("translations", "read", "Przeglądanie tłumaczeń"),
    ("translations", "create", "Tworzenie tłumaczeń"),
    ("translations", "update", "Edycja tłumaczeń"),
    # Calendar
    ("calendar", "read", "Przeglądanie kalendarza"),
    ("calendar", "create", "Tworzenie wpisów kalendarza"),
    ("calendar", "update", "Edycja kalendarza"),
    ("calendar", "delete", "Usuwanie wpisów kalendarza"),
]


# Permissions per role
ROLE_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    SystemRole.SUPER_ADMIN: [(r, a) for r, a, _ in PERMISSIONS],  # All permissions
    SystemRole.ADMIN: [
        ("persons", "read"), ("persons", "create"), ("persons", "update"),
        ("persons", "delete"), ("persons", "publish"), ("persons", "restore"),
        ("sources", "read"), ("sources", "create"), ("sources", "update"), ("sources", "delete"),
        ("geography", "read"), ("geography", "create"), ("geography", "update"), ("geography", "delete"),
        ("orders", "read"), ("orders", "create"), ("orders", "update"), ("orders", "delete"),
        ("images", "read"), ("images", "create"), ("images", "update"), ("images", "delete"),
        ("export", "read"), ("export", "create"),
        ("import", "create"),
        ("users", "read"),
        ("audit", "read"),
        ("translations", "read"), ("translations", "create"), ("translations", "update"),
        ("calendar", "read"), ("calendar", "create"), ("calendar", "update"), ("calendar", "delete"),
    ],
    SystemRole.EDITOR: [
        ("persons", "read"), ("persons", "create"), ("persons", "update"),
        ("sources", "read"), ("sources", "create"), ("sources", "update"),
        ("geography", "read"), ("geography", "create"),
        ("orders", "read"),
        ("images", "read"), ("images", "create"), ("images", "update"),
        ("export", "read"), ("export", "create"),
        ("calendar", "read"),
    ],
    SystemRole.REVIEWER: [
        ("persons", "read"), ("persons", "update"),
        ("sources", "read"),
        ("geography", "read"),
        ("images", "read"),
        ("export", "read"),
        ("calendar", "read"),
    ],
    SystemRole.TRANSLATOR: [
        ("persons", "read"),
        ("translations", "read"), ("translations", "create"), ("translations", "update"),
        ("geography", "read"),
        ("calendar", "read"),
    ],
    SystemRole.READER: [
        ("persons", "read"),
        ("sources", "read"),
        ("geography", "read"),
        ("images", "read"),
        ("export", "read"),
        ("calendar", "read"),
    ],
    SystemRole.GUEST: [
        ("persons", "read"),
        ("geography", "read"),
    ],
}


ROLE_METADATA: dict[str, tuple[str, str]] = {
    SystemRole.SUPER_ADMIN: ("Super Administrator", "Pełny dostęp do systemu"),
    SystemRole.ADMIN: ("Administrator", "Zarządzanie treściami i użytkownikami"),
    SystemRole.EDITOR: ("Redaktor", "Tworzenie i edycja treści"),
    SystemRole.REVIEWER: ("Recenzent", "Przegląd i weryfikacja treści"),
    SystemRole.TRANSLATOR: ("Tłumacz", "Tłumaczenie treści"),
    SystemRole.READER: ("Czytelnik", "Dostęp tylko do odczytu"),
    SystemRole.GUEST: ("Gość", "Ograniczony dostęp publiczny"),
}


# ==============================================================================
# REFERENCE DATA
# ==============================================================================

STATES_OF_LIFE: list[tuple[str, str, str]] = [
    ("Kapłan", "Priest", "Presbyter"),
    ("Biskup", "Bishop", "Episcopus"),
    ("Papież", "Pope", "Pontifex"),
    ("Diakon", "Deacon", "Diaconus"),
    ("Zakonnik / Mnich", "Religious (Male)", "Monachus"),
    ("Zakonnica", "Religious (Female)", "Monialis"),
    ("Osoba konsekrowana", "Consecrated Person", "Persona consecrata"),
    ("Świecki mężczyzna", "Lay Man", "Laicus"),
    ("Świecka kobieta", "Lay Woman", "Laica"),
    ("Pustelnik", "Hermit", "Eremita"),
    ("Dziewica konsekrowana", "Consecrated Virgin", "Virgo consecrata"),
    ("Wdowa / Wdowiec", "Widow / Widower", "Vidua"),
    ("Dziecko / Młodzieniec", "Child / Youth", "Puer / Iuvenis"),
    ("Nieznany", "Unknown", "Ignotus"),
]

LITURGICAL_CALENDARS: list[tuple[str, str, str, str]] = [
    ("roman_universal", "Ogólny Kalendarz Rzymski", "roman", "universal"),
    ("roman_pl", "Kalendarz Polski", "roman", "national"),
    ("roman_dominican", "Kalendarz Dominikański", "roman", "religious"),
    ("roman_franciscan", "Kalendarz Franciszkański", "roman", "religious"),
    ("roman_jesuit", "Kalendarz Jezuicki", "roman", "religious"),
    ("roman_benedictine", "Kalendarz Benedyktyński", "roman", "religious"),
]


# ==============================================================================
# SEED FUNCTIONS
# ==============================================================================


async def seed_permissions(session: AsyncSession) -> dict[tuple[str, str], Permission]:
    """Create all permissions and return a map of (resource, action) → Permission."""
    logger.info("Seeding permissions...")
    permission_map: dict[tuple[str, str], Permission] = {}

    for resource, action, description in PERMISSIONS:
        result = await session.execute(
            select(Permission).where(
                Permission.resource == resource,
                Permission.action == action,
            )
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(
                resource=resource,
                action=action,
                description=description,
            )
            session.add(perm)
        else:
            perm.description = description
        permission_map[(resource, action)] = perm

    await session.flush()
    logger.info(f"✓ Created {len(PERMISSIONS)} permissions")
    return permission_map


async def seed_roles(
    session: AsyncSession,
    permission_map: dict[tuple[str, str], Permission],
) -> dict[str, Role]:
    """Create all system roles with their permissions."""
    logger.info("Seeding roles...")
    role_map: dict[str, Role] = {}
    now = datetime.now(timezone.utc)

    for role_name, (display_name, description) in ROLE_METADATA.items():
        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(
                name=role_name,
                display_name=display_name,
                description=description,
                is_system=True,
            )
            session.add(role)
            await session.flush()
        else:
            role.display_name = display_name
            role.description = description
            role.is_system = True

        # Assign permissions
        for resource, action in ROLE_PERMISSIONS.get(role_name, []):
            perm = permission_map.get((resource, action))
            if perm:
                existing = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    )
                )
                if existing.scalar_one_or_none() is None:
                    session.add(
                        RolePermission(
                            role_id=role.id,
                            permission_id=perm.id,
                            granted_at=now,
                        )
                    )

        role_map[role_name] = role

    await session.flush()
    logger.info(f"✓ Created {len(ROLE_METADATA)} roles")
    return role_map


async def seed_admin_user(
    session: AsyncSession,
    role_map: dict[str, Role],
) -> User:
    """Create the initial Super Admin user."""
    logger.info("Seeding admin user...")
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL.lower())
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=settings.INITIAL_ADMIN_EMAIL.lower(),
            hashed_password=password_hasher.hash(
                settings.INITIAL_ADMIN_PASSWORD or "Admin123!"
            ),
            full_name=settings.INITIAL_ADMIN_FULL_NAME,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

    # Assign Super Admin role
    super_admin_role = role_map[SystemRole.SUPER_ADMIN]
    existing_role = await session.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == super_admin_role.id,
        )
    )
    if existing_role.scalar_one_or_none() is None:
        session.add(
            UserRole(
                user_id=user.id,
                role_id=super_admin_role.id,
                assigned_at=now,
                assigned_by_id=None,
            )
        )
    await session.flush()

    logger.info(f"✓ Created admin user: {settings.INITIAL_ADMIN_EMAIL}")
    return user


async def seed_states_of_life(session: AsyncSession) -> None:
    """Create reference states of life."""
    logger.info("Seeding states of life...")
    for name_pl, name_en, name_la in STATES_OF_LIFE:
        result = await session.execute(
            select(StateOfLife).where(StateOfLife.name_pl == name_pl)
        )
        sol = result.scalar_one_or_none()
        if sol is None:
            session.add(
                StateOfLife(
                    name_pl=name_pl,
                    name_en=name_en,
                    name_la=name_la,
                )
            )
        else:
            sol.name_en = name_en
            sol.name_la = name_la
    await session.flush()
    logger.info(f"✓ Created {len(STATES_OF_LIFE)} states of life")


async def seed_liturgical_calendars(session: AsyncSession) -> None:
    """Create reference liturgical calendars."""
    logger.info("Seeding liturgical calendars...")
    for code, name, rite, scope in LITURGICAL_CALENDARS:
        result = await session.execute(
            select(LiturgicalCalendar).where(LiturgicalCalendar.code == code)
        )
        cal = result.scalar_one_or_none()
        if cal is None:
            session.add(
                LiturgicalCalendar(
                    code=code,
                    name=name,
                    rite=rite,
                    scope=scope,
                    is_active=True,
                )
            )
        else:
            cal.name = name
            cal.rite = rite
            cal.scope = scope
            cal.is_active = True
    await session.flush()
    logger.info(f"✓ Created {len(LITURGICAL_CALENDARS)} liturgical calendars")


# ==============================================================================
# MAIN
# ==============================================================================


async def run_seed() -> None:
    """Run all seed operations within a single transaction."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        try:
            logger.info("Starting database seed...")

            # Enable PostgreSQL extensions
            await enable_pgvector(session)

            # Seed reference data
            permission_map = await seed_permissions(session)
            role_map = await seed_roles(session, permission_map)
            await seed_admin_user(session, role_map)
            await seed_states_of_life(session)
            await seed_liturgical_calendars(session)

            await session.commit()
            logger.info("✓ Database seed completed successfully")

        except Exception as exc:
            await session.rollback()
            logger.exception(f"Seed failed: {exc}")
            raise
        finally:
            await session.close()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_seed())
