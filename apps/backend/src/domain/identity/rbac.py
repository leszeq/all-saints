"""Canonical role and permission matrix for the administration panel.

The same definitions drive database seeding and the access-control API.  This
keeps authorization policy out of presentation code and prevents the UI,
fixtures, and production data from drifting apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.identity.models import SystemRole


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    resource: str
    action: str
    description: str
    group: str

    @property
    def key(self) -> str:
        return f"{self.resource}:{self.action}"


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    display_name: str
    description: str


PERMISSIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition("persons", "read", "Przeglądanie osób", "Osoby i święci"),
    PermissionDefinition("persons", "create", "Tworzenie nowych osób", "Osoby i święci"),
    PermissionDefinition("persons", "update", "Edycja danych osób", "Osoby i święci"),
    PermissionDefinition("persons", "delete", "Usuwanie osób", "Osoby i święci"),
    PermissionDefinition(
        "persons", "submit", "Przekazywanie szkiców do recenzji", "Workflow redakcyjny"
    ),
    PermissionDefinition(
        "persons", "review", "Akceptowanie lub zwracanie recenzji", "Workflow redakcyjny"
    ),
    PermissionDefinition(
        "persons", "publish", "Wycofywanie i archiwizowanie publikacji", "Workflow redakcyjny"
    ),
    PermissionDefinition("persons", "restore", "Przywracanie usuniętych osób", "Osoby i święci"),
    PermissionDefinition("sources", "read", "Przeglądanie źródeł", "Źródła i media"),
    PermissionDefinition("sources", "create", "Tworzenie źródeł", "Źródła i media"),
    PermissionDefinition("sources", "update", "Edycja źródeł", "Źródła i media"),
    PermissionDefinition("sources", "delete", "Usuwanie źródeł", "Źródła i media"),
    PermissionDefinition("geography", "read", "Przeglądanie geografii", "Geografia"),
    PermissionDefinition("geography", "create", "Tworzenie lokalizacji", "Geografia"),
    PermissionDefinition("geography", "update", "Edycja lokalizacji", "Geografia"),
    PermissionDefinition("geography", "delete", "Usuwanie lokalizacji", "Geografia"),
    PermissionDefinition("orders", "read", "Przeglądanie zakonów", "Zakony"),
    PermissionDefinition("orders", "create", "Tworzenie zakonów", "Zakony"),
    PermissionDefinition("orders", "update", "Edycja zakonów", "Zakony"),
    PermissionDefinition("orders", "delete", "Usuwanie zakonów", "Zakony"),
    PermissionDefinition("images", "read", "Przeglądanie obrazów", "Źródła i media"),
    PermissionDefinition("images", "create", "Dodawanie obrazów", "Źródła i media"),
    PermissionDefinition("images", "update", "Edycja obrazów", "Źródła i media"),
    PermissionDefinition("images", "delete", "Usuwanie obrazów", "Źródła i media"),
    PermissionDefinition("calendar", "read", "Przeglądanie kalendarza", "Kalendarz"),
    PermissionDefinition("calendar", "create", "Tworzenie obchodów", "Kalendarz"),
    PermissionDefinition("calendar", "update", "Edycja obchodów", "Kalendarz"),
    PermissionDefinition("calendar", "delete", "Usuwanie obchodów", "Kalendarz"),
    PermissionDefinition("translations", "read", "Przeglądanie tłumaczeń", "Tłumaczenia"),
    PermissionDefinition("translations", "create", "Tworzenie tłumaczeń", "Tłumaczenia"),
    PermissionDefinition("translations", "update", "Edycja tłumaczeń", "Tłumaczenia"),
    PermissionDefinition("translations", "delete", "Usuwanie tłumaczeń", "Tłumaczenia"),
    PermissionDefinition("export", "read", "Pobieranie eksportów", "Import i eksport"),
    PermissionDefinition("export", "create", "Generowanie eksportów", "Import i eksport"),
    PermissionDefinition("import", "create", "Importowanie danych", "Import i eksport"),
    PermissionDefinition("audit", "read", "Przeglądanie dziennika audytu", "Administracja"),
    PermissionDefinition("users", "read", "Przeglądanie użytkowników", "Administracja"),
    PermissionDefinition("users", "create", "Tworzenie użytkowników", "Administracja"),
    PermissionDefinition("users", "update", "Edycja użytkowników", "Administracja"),
    PermissionDefinition("users", "delete", "Dezaktywowanie użytkowników", "Administracja"),
    PermissionDefinition("roles", "read", "Przeglądanie macierzy uprawnień", "Administracja"),
    PermissionDefinition("roles", "create", "Tworzenie ról", "Administracja"),
    PermissionDefinition("roles", "update", "Edycja ról", "Administracja"),
    PermissionDefinition("roles", "delete", "Usuwanie ról", "Administracja"),
)

ALL_PERMISSION_KEYS = frozenset(permission.key for permission in PERMISSIONS)
PROTECTED_MANAGEMENT_RESOURCES = frozenset({"users", "roles"})
CUSTOM_ROLE_PERMISSION_KEYS = frozenset(
    permission.key
    for permission in PERMISSIONS
    if permission.resource not in PROTECTED_MANAGEMENT_RESOURCES
)

ROLE_DEFINITIONS: dict[SystemRole, RoleDefinition] = {
    SystemRole.SUPER_ADMIN: RoleDefinition(
        "Superadministrator",
        "Jedyny właściciel systemu; zarządza użytkownikami, rolami i całą treścią.",
    ),
    SystemRole.ADMIN: RoleDefinition(
        "Administrator",
        "Pełne zarządzanie treścią i workflow bez dostępu do kont użytkowników i ról.",
    ),
    SystemRole.EDITOR: RoleDefinition(
        "Redaktor",
        "Tworzy i edytuje treści oraz przekazuje gotowe szkice do recenzji.",
    ),
    SystemRole.REVIEWER: RoleDefinition(
        "Recenzent",
        "Akceptuje kompletne rekordy albo zwraca je redaktorowi z komentarzem.",
    ),
    SystemRole.TRANSLATOR: RoleDefinition(
        "Tłumacz",
        "Przegląda katalog i opracowuje tłumaczenia.",
    ),
    SystemRole.READER: RoleDefinition(
        "Czytelnik wewnętrzny",
        "Ma dostęp wyłącznie do odczytu danych redakcyjnych.",
    ),
    SystemRole.GUEST: RoleDefinition(
        "Gość",
        "Ma ograniczony dostęp tylko do podstawowych danych.",
    ),
}

_ADMIN_PERMISSIONS = ALL_PERMISSION_KEYS - frozenset(
    key
    for key in ALL_PERMISSION_KEYS
    if key.split(":", maxsplit=1)[0] in PROTECTED_MANAGEMENT_RESOURCES
)

ROLE_PERMISSIONS: dict[SystemRole, frozenset[str]] = {
    SystemRole.SUPER_ADMIN: ALL_PERMISSION_KEYS,
    SystemRole.ADMIN: _ADMIN_PERMISSIONS,
    SystemRole.EDITOR: frozenset(
        {
            "persons:read",
            "persons:create",
            "persons:update",
            "persons:submit",
            "sources:read",
            "sources:create",
            "sources:update",
            "geography:read",
            "geography:create",
            "orders:read",
            "images:read",
            "images:create",
            "images:update",
            "export:read",
            "export:create",
            "calendar:read",
            "translations:read",
        }
    ),
    SystemRole.REVIEWER: frozenset(
        {
            "persons:read",
            "persons:review",
            "sources:read",
            "geography:read",
            "orders:read",
            "images:read",
            "export:read",
            "calendar:read",
            "translations:read",
        }
    ),
    SystemRole.TRANSLATOR: frozenset(
        {
            "persons:read",
            "translations:read",
            "translations:create",
            "translations:update",
            "translations:delete",
            "geography:read",
            "calendar:read",
        }
    ),
    SystemRole.READER: frozenset(
        {
            "persons:read",
            "sources:read",
            "geography:read",
            "orders:read",
            "images:read",
            "export:read",
            "calendar:read",
            "translations:read",
        }
    ),
    SystemRole.GUEST: frozenset({"persons:read", "geography:read"}),
}


def split_permission_key(key: str) -> tuple[str, str]:
    """Split a validated permission key into the database resource/action pair."""
    resource, action = key.split(":", maxsplit=1)
    return resource, action
