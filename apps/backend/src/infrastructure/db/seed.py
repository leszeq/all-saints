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
import uuid
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import is_strong_password, password_hasher
from src.domain.geography import models as geography_models  # noqa: F401
from src.domain.hagiography import embedding_model as embedding_models  # noqa: F401
from src.domain.hagiography.models import StateOfLife
from src.domain.identity.models import (
    Permission,
    Role,
    RolePermission,
    SystemRole,
    User,
    UserRole,
    UserStatus,
)
from src.domain.identity.rbac import (
    PERMISSIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSIONS,
    split_permission_key,
)
from src.domain.liturgy.models import LiturgicalCalendar
from src.domain.sources import models as source_models  # noqa: F401
from src.infrastructure.db.session import enable_pgvector, get_engine

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
    ("roman_martyrology", "Martyrologium Rzymskie", "roman", "universal"),
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

    for definition in PERMISSIONS:
        resource, action = definition.resource, definition.action
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
                description=definition.description,
            )
            session.add(perm)
        else:
            perm.description = definition.description
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
    now = datetime.now(UTC)

    for role_name, definition in ROLE_DEFINITIONS.items():
        result = await session.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(
                name=role_name,
                display_name=definition.display_name,
                description=definition.description,
                is_system=True,
            )
            session.add(role)
            await session.flush()
        else:
            role.display_name = definition.display_name
            role.description = definition.description
            role.is_system = True

        desired_permission_ids: set[uuid.UUID] = set()
        for key in ROLE_PERMISSIONS.get(role_name, frozenset()):
            resource, action = split_permission_key(key)
            perm = permission_map.get((resource, action))
            if perm:
                desired_permission_ids.add(perm.id)

        current_result = await session.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
        current_assignments = current_result.scalars().all()
        current_permission_ids = {assignment.permission_id for assignment in current_assignments}
        stale_permission_ids = current_permission_ids - desired_permission_ids
        if stale_permission_ids:
            await session.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id.in_(stale_permission_ids),
                )
            )
        for permission_id in desired_permission_ids - current_permission_ids:
            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission_id,
                    granted_at=now,
                )
            )

        role_map[role_name] = role

    await session.flush()
    logger.info(f"✓ Synchronized {len(ROLE_DEFINITIONS)} system roles")
    return role_map


async def seed_admin_user(
    session: AsyncSession,
    role_map: dict[str, Role],
) -> User:
    """Create the initial Super Admin user."""
    logger.info("Seeding admin user...")
    now = datetime.now(UTC)

    super_admin_role = role_map[SystemRole.SUPER_ADMIN]
    existing_super_admins = (
        await session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id == super_admin_role.id)
            .where(User.deleted_at.is_(None))
        )
    ).scalars().all()
    if len(existing_super_admins) > 1:
        raise RuntimeError("W bazie istnieje więcej niż jeden aktywny superadministrator")
    if existing_super_admins:
        user = existing_super_admins[0]
        if user.email != settings.INITIAL_ADMIN_EMAIL.lower():
            logger.warning(
                "Initial admin email differs from the existing superadministrator; "
                "the existing account remains the sole owner"
            )
        return user

    result = await session.execute(
        select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL.lower())
    )
    initial_user = result.scalar_one_or_none()
    if initial_user is None:
        user = User(
            email=settings.INITIAL_ADMIN_EMAIL.lower(),
            hashed_password=password_hasher.hash(settings.INITIAL_ADMIN_PASSWORD or "Admin123!"),
            full_name=settings.INITIAL_ADMIN_FULL_NAME,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        session.add(user)
        await session.flush()
    else:
        user = initial_user

    # Assign Super Admin role
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


async def seed_demo_users(
    session: AsyncSession,
    role_map: dict[str, Role],
) -> None:
    """Create deterministic workflow accounts only in development/testing."""
    if not settings.SEED_DEMO_USERS:
        return
    if settings.is_production:
        raise RuntimeError("Konta demonstracyjne nie mogą być tworzone w produkcji")

    password_is_strong, password_errors = is_strong_password(settings.DEMO_USER_PASSWORD)
    if not password_is_strong:
        raise RuntimeError(
            "DEMO_USER_PASSWORD nie spełnia polityki haseł: " + ", ".join(password_errors)
        )

    demo_accounts = (
        ("admin.test@encyklopedia.pl", "Testowy Administrator", SystemRole.ADMIN),
        ("redaktor.test@encyklopedia.pl", "Testowy Redaktor", SystemRole.EDITOR),
        ("recenzent.test@encyklopedia.pl", "Testowy Recenzent", SystemRole.REVIEWER),
    )
    now = datetime.now(UTC)
    password_hash = password_hasher.hash(settings.DEMO_USER_PASSWORD)

    for email, full_name, role_name in demo_accounts:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                hashed_password=password_hash,
                full_name=full_name,
                status=UserStatus.ACTIVE,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
        else:
            if user.has_role(SystemRole.SUPER_ADMIN):
                raise RuntimeError(f"Konto demonstracyjne {email} nie może być superadministratorem")
            user.hashed_password = password_hash
            user.full_name = full_name
            user.status = UserStatus.ACTIVE
            user.is_verified = True
            user.deleted_at = None

        await session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        session.add(
            UserRole(
                user_id=user.id,
                role_id=role_map[role_name].id,
                assigned_at=now,
                assigned_by_id=None,
            )
        )

    await session.flush()
    logger.info("✓ Synchronized development workflow accounts")


async def seed_states_of_life(session: AsyncSession) -> None:
    """Create reference states of life."""
    logger.info("Seeding states of life...")
    for name_pl, name_en, name_la in STATES_OF_LIFE:
        result = await session.execute(select(StateOfLife).where(StateOfLife.name_pl == name_pl))
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
            await seed_demo_users(session, role_map)
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
