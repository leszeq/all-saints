"""
Alembic environment configuration.

Uses SQLAlchemy 2.0 async engine with synchronous Alembic migrations
via run_sync() for online mode.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import settings and all models (so Alembic can detect schema changes)
from src.core.config import settings
from src.domain.base import Base

# Import all model modules to register their tables with Base.metadata.
from src.domain.geography.models import (  # noqa: F401
    Church,
    Country,
    Diocese,
    Place,
    Region,
    ReligiousOrder,
)
from src.domain.hagiography.embedding_model import PersonEmbedding  # noqa: F401
from src.domain.hagiography.models import (  # noqa: F401
    Beatification,
    Canonization,
    Category,
    Miracle,
    Occupation,
    Patronage,
    Person,
    PersonCategory,
    PersonOccupation,
    PersonOrder,
    PersonQuote,
    PersonRelationship,
    PersonTag,
    PersonTranslation,
    PersonVersion,
    Pope,
    Relic,
    StateOfLife,
    Tag,
)
from src.domain.identity.models import (  # noqa: F401
    AuditLog,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)
from src.domain.liturgy.models import (  # noqa: F401
    Feast,
    LiturgicalCalendar,
    LiturgicalObservance,
)
from src.domain.sources.models import (  # noqa: F401
    Bibliography,
    Document,
    HistoricalSource,
    Image,
    PersonSource,
)

# Alembic Config
config = context.config

# This environment uses ``async_engine_from_config``, so it must receive the
# asyncpg DSN rather than the synchronous psycopg2 DSN.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)  # type: ignore[arg-type]

# Python logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = Base.metadata

# Column/table comments are developer documentation and were not consistently
# migrated in the historical revisions. Excluding only the comments plugin
# keeps ``alembic check`` focused on executable schema: tables, types, defaults,
# constraints and indexes.
AUTOGENERATE_PLUGINS = (
    "alembic.autogenerate.schemas",
    "alembic.autogenerate.tables",
    "alembic.autogenerate.types",
    "alembic.autogenerate.constraints",
    "alembic.autogenerate.defaults",
    "alembic.autogenerate.checkconstraint_byname",
)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with just a URL, without creating an Engine.
    Useful for generating migration scripts without a live database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        autogenerate_plugins=AUTOGENERATE_PLUGINS,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations with a live connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        autogenerate_plugins=AUTOGENERATE_PLUGINS,
        # Custom rendering for JSONB, UUID, etc.
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations asynchronously using the async engine.

    We use run_sync() to run the synchronous migration code within
    the async context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a live database connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
