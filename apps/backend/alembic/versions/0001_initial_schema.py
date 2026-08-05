"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-05 18:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # --------------------------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------------------------
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resource', 'action', name='uq_permission_resource_action')
    )
    op.create_index('ix_permissions_resource', 'permissions', ['resource'], unique=False)
    op.create_index('ix_permissions_id', 'permissions', ['id'], unique=False)

    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_role_name')
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=False)
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)

    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission')
    )

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=300), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending_verification'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), nullable=False, server_default='pl'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('two_factor_secret', sa.String(length=100), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_user_email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_status', 'users', ['status'], unique=False)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)

    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role')
    )

    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=False)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_email', sa.String(length=320), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)

    # --------------------------------------------------------------------------
    # GEOGRAPHY
    # --------------------------------------------------------------------------
    op.create_table(
        'countries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name_pl', sa.String(length=200), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('name_la', sa.String(length=200), nullable=True),
        sa.Column('name_local', sa.String(length=200), nullable=True),
        sa.Column('iso_code_alpha2', sa.String(length=2), nullable=True),
        sa.Column('iso_code_alpha3', sa.String(length=3), nullable=True),
        sa.Column('continent', sa.String(length=50), nullable=True),
        sa.Column('capital', sa.String(length=200), nullable=True),
        sa.Column('flag_emoji', sa.String(length=10), nullable=True),
        sa.Column('is_historical', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('historical_period', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iso_code_alpha2', name='uq_country_iso2'),
        sa.UniqueConstraint('iso_code_alpha3', name='uq_country_iso3')
    )
    op.create_index('ix_countries_name_pl', 'countries', ['name_pl'], unique=False)

    op.create_table(
        'regions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('name_local', sa.String(length=300), nullable=True),
        sa.Column('country_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_regions_country_id', 'regions', ['country_id'], unique=False)

    op.create_table(
        'dioceses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=400), nullable=False),
        sa.Column('name_la', sa.String(length=400), nullable=True),
        sa.Column('is_archdiocese', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('country_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('founded_year', sa.Integer(), nullable=True),
        sa.Column('suppressed_year', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dioceses_country_id', 'dioceses', ['country_id'], unique=False)

    op.create_table(
        'places',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=400), nullable=False),
        sa.Column('name_la', sa.String(length=400), nullable=True),
        sa.Column('name_local', sa.String(length=400), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('country_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('diocese_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['diocese_id'], ['dioceses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['region_id'], ['regions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_places_country_id', 'places', ['country_id'], unique=False)
    op.create_index('ix_places_name', 'places', ['name'], unique=False)

    op.create_table(
        'religious_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('name_la', sa.String(length=500), nullable=True),
        sa.Column('name_local', sa.String(length=500), nullable=True),
        sa.Column('abbreviation', sa.String(length=20), nullable=True),
        sa.Column('founded_year', sa.Integer(), nullable=True),
        sa.Column('founded_place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('founder_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('suppressed_year', sa.Integer(), nullable=True),
        sa.Column('charism', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('description_en', sa.Text(), nullable=True),
        sa.Column('papal_approval_year', sa.Integer(), nullable=True),
        sa.Column('is_suppressed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['founded_place_id'], ['places.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_religious_orders_abbreviation', 'religious_orders', ['abbreviation'], unique=False)

    op.create_table(
        'churches',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('name_la', sa.String(length=500), nullable=True),
        sa.Column('church_type', sa.String(length=30), nullable=False, server_default='parish'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('diocese_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('construction_year', sa.Integer(), nullable=True),
        sa.Column('consecration_year', sa.Integer(), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('is_pilgrimage_site', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_national_sanctuary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['diocese_id'], ['dioceses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['place_id'], ['places.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_churches_place_id', 'churches', ['place_id'], unique=False)
    op.create_index('ix_churches_type', 'churches', ['church_type'], unique=False)

    # --------------------------------------------------------------------------
    # TAXONOMY & HAGIOGRAPHY BASE
    # --------------------------------------------------------------------------
    op.create_table(
        'states_of_life',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name_pl', sa.String(length=200), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('name_la', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'occupations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name_pl', sa.String(length=300), nullable=False),
        sa.Column('name_en', sa.String(length=300), nullable=False),
        sa.Column('name_la', sa.String(length=300), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name_pl', sa.String(length=300), nullable=False),
        sa.Column('name_en', sa.String(length=300), nullable=False),
        sa.Column('slug', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_categories_parent_id', 'categories', ['parent_id'], unique=False)

    op.create_table(
        'tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name_pl', sa.String(length=200), nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_tag_slug')
    )

    # --------------------------------------------------------------------------
    # PERSONS (CORE)
    # --------------------------------------------------------------------------
    op.create_table(
        'persons',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_type', sa.String(length=30), nullable=False, server_default='saint'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('canonical_name', sa.String(length=500), nullable=False),
        sa.Column('canonical_name_en', sa.String(length=500), nullable=True),
        sa.Column('latin_name', sa.String(length=500), nullable=True),
        sa.Column('original_name', sa.String(length=500), nullable=True),
        sa.Column('surnames', sa.String(length=500), nullable=True),
        sa.Column('religious_name', sa.String(length=300), nullable=True),
        sa.Column('epithets', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('slug', sa.String(length=600), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=False, server_default='unknown'),
        sa.Column('era', sa.String(length=30), nullable=True),
        sa.Column('century', sa.SmallInteger(), nullable=True),
        sa.Column('birth_date', sa.String(length=50), nullable=True),
        sa.Column('birth_year', sa.Integer(), nullable=True),
        sa.Column('death_date', sa.String(length=50), nullable=True),
        sa.Column('death_year', sa.Integer(), nullable=True),
        sa.Column('birth_place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('death_place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('birth_country_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('death_country_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('nationality_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('state_of_life_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('summary_pl', sa.Text(), nullable=True),
        sa.Column('biography_pl', sa.Text(), nullable=True),
        sa.Column('summary_en', sa.Text(), nullable=True),
        sa.Column('biography_en', sa.Text(), nullable=True),
        sa.Column('iconographic_attributes', sa.Text(), nullable=True),
        sa.Column('prayers', sa.Text(), nullable=True),
        sa.Column('works', sa.Text(), nullable=True),
        sa.Column('liturgical_color', sa.String(length=10), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('embedding_vector', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('ai_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_name', sa.String(length=600), nullable=True),
        sa.Column('external_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['birth_country_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['birth_place_id'], ['places.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['death_country_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['death_place_id'], ['places.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['nationality_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['state_of_life_id'], ['states_of_life.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_persons_birth_country_id', 'persons', ['birth_country_id'], unique=False)
    op.create_index('ix_persons_canonical_name', 'persons', ['canonical_name'], unique=False)
    op.create_index('ix_persons_death_country_id', 'persons', ['death_country_id'], unique=False)
    op.create_index('ix_persons_era', 'persons', ['era'], unique=False)
    op.create_index('ix_persons_gender', 'persons', ['gender'], unique=False)
    op.create_index('ix_persons_person_type', 'persons', ['person_type'], unique=False)
    op.create_index('ix_persons_search_vector', 'persons', ['search_vector'], postgresql_using='gin')
    op.create_index('ix_persons_slug', 'persons', ['slug'], unique=False)
    op.create_index('ix_persons_sort_name', 'persons', ['sort_name'], unique=False)
    op.create_index('ix_persons_status', 'persons', ['status'], unique=False)

    # --------------------------------------------------------------------------
    # POPES, CANONIZATIONS, BEATIFICATIONS
    # --------------------------------------------------------------------------
    op.create_table(
        'popes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('papal_name', sa.String(length=300), nullable=False),
        sa.Column('pontificate_start', sa.String(length=50), nullable=True),
        sa.Column('pontificate_end', sa.String(length=50), nullable=True),
        sa.Column('pontificate_start_year', sa.Integer(), nullable=True),
        sa.Column('pontificate_end_year', sa.Integer(), nullable=True),
        sa.Column('regnal_number', sa.Integer(), nullable=True),
        sa.Column('birth_name', sa.String(length=300), nullable=True),
        sa.Column('nationality_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['nationality_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('papal_name', 'pontificate_start', name='uq_pope_pontificate')
    )

    op.create_table(
        'canonizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pope_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('canonization_date', sa.String(length=50), nullable=True),
        sa.Column('canonization_year', sa.Integer(), nullable=True),
        sa.Column('place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('decree_number', sa.String(length=200), nullable=True),
        sa.Column('acta_reference', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['place_id'], ['places.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pope_id'], ['popes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', name='uq_canonization_person')
    )

    op.create_table(
        'beatifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pope_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('beatification_date', sa.String(length=50), nullable=True),
        sa.Column('beatification_year', sa.Integer(), nullable=True),
        sa.Column('place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('decree_number', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['place_id'], ['places.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pope_id'], ['popes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', name='uq_beatification_person')
    )

    op.create_table(
        'miracles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verification_status', sa.String(length=30), nullable=False, server_default='reported'),
        sa.Column('used_for_beatification', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_for_canonization', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('source_reference', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['place_id'], ['places.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_miracles_person_id', 'miracles', ['person_id'], unique=False)
    op.create_index('ix_miracles_status', 'miracles', ['verification_status'], unique=False)

    op.create_table(
        'patronages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patronage_type', sa.String(length=50), nullable=False),
        sa.Column('name_pl', sa.String(length=500), nullable=False),
        sa.Column('name_en', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('country_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_official', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_patronages_person_id', 'patronages', ['person_id'], unique=False)
    op.create_index('ix_patronages_type', 'patronages', ['patronage_type'], unique=False)

    op.create_table(
        'relics',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relic_class', sa.String(length=10), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('church_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('place_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_authenticated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('authentication_document', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['church_id'], ['churches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['place_id'], ['places.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_relics_person_id', 'relics', ['person_id'], unique=False)

    op.create_table(
        'person_quotes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quote_pl', sa.Text(), nullable=False),
        sa.Column('quote_en', sa.Text(), nullable=True),
        sa.Column('quote_la', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=500), nullable=True),
        sa.Column('is_attributed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'person_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_a_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_b_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_bidirectional', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_a_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_b_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_person_relationships_a', 'person_relationships', ['person_a_id'], unique=False)
    op.create_index('ix_person_relationships_b', 'person_relationships', ['person_b_id'], unique=False)

    op.create_table(
        'person_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('changed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('changed_at', sa.String(length=50), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', 'version_number', name='uq_person_version_number')
    )
    op.create_index('ix_person_versions_person_id', 'person_versions', ['person_id'], unique=False)

    # Many-to-many person associations
    op.create_table(
        'person_translations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('canonical_name', sa.String(length=500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('biography', sa.Text(), nullable=True),
        sa.Column('prayers', sa.Text(), nullable=True),
        sa.Column('iconographic_attributes', sa.Text(), nullable=True),
        sa.Column('translated_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['translated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', 'language_code', name='uq_person_translation_lang')
    )
    op.create_index('ix_person_translations_person_id', 'person_translations', ['person_id'], unique=False)

    op.create_table(
        'person_occupations',
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('occupation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['occupation_id'], ['occupations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'occupation_id')
    )

    op.create_table(
        'person_orders',
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entry_date', sa.String(length=50), nullable=True),
        sa.Column('exit_date', sa.String(length=50), nullable=True),
        sa.Column('is_founder', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['order_id'], ['religious_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'order_id')
    )

    op.create_table(
        'person_categories',
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'category_id')
    )

    op.create_table(
        'person_tags',
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'tag_id')
    )

    # --------------------------------------------------------------------------
    # SOURCES
    # --------------------------------------------------------------------------
    op.create_table(
        'bibliography',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_type', sa.String(length=30), nullable=False, server_default='book'),
        sa.Column('title', sa.String(length=1000), nullable=False),
        sa.Column('subtitle', sa.String(length=500), nullable=True),
        sa.Column('authors', sa.String(length=1000), nullable=True),
        sa.Column('editor', sa.String(length=500), nullable=True),
        sa.Column('publisher', sa.String(length=500), nullable=True),
        sa.Column('place_of_publication', sa.String(length=300), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('edition', sa.String(length=100), nullable=True),
        sa.Column('volume', sa.String(length=100), nullable=True),
        sa.Column('pages', sa.String(length=100), nullable=True),
        sa.Column('isbn', sa.String(length=20), nullable=True),
        sa.Column('issn', sa.String(length=20), nullable=True),
        sa.Column('doi', sa.String(length=500), nullable=True),
        sa.Column('url', sa.String(length=2000), nullable=True),
        sa.Column('url_access_date', sa.String(length=50), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('reliability_score', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bibliography_source_type', 'bibliography', ['source_type'], unique=False)
    op.create_index('ix_bibliography_year', 'bibliography', ['year'], unique=False)

    op.create_table(
        'historical_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('title', sa.String(length=1000), nullable=False),
        sa.Column('original_title', sa.String(length=1000), nullable=True),
        sa.Column('source_type', sa.String(length=30), nullable=False, server_default='manuscript'),
        sa.Column('repository', sa.String(length=500), nullable=True),
        sa.Column('call_number', sa.String(length=200), nullable=True),
        sa.Column('date_range', sa.String(length=100), nullable=True),
        sa.Column('language', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('digitization_url', sa.String(length=2000), nullable=True),
        sa.Column('is_digitized', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_historical_sources_repository', 'historical_sources', ['repository'], unique=False)

    op.create_table(
        'person_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bibliography_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('historical_source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('page_reference', sa.String(length=200), nullable=True),
        sa.Column('quote', sa.Text(), nullable=True),
        sa.Column('relevance_score', sa.Integer(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['bibliography_id'], ['bibliography.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['historical_source_id'], ['historical_sources.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_person_sources_bibliography_id', 'person_sources', ['bibliography_id'], unique=False)
    op.create_index('ix_person_sources_person_id', 'person_sources', ['person_id'], unique=False)

    op.create_table(
        'images',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('url', sa.String(length=2000), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=2000), nullable=True),
        sa.Column('storage_key', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_type', sa.String(length=50), nullable=True),
        sa.Column('license', sa.String(length=30), nullable=False, server_default='unknown'),
        sa.Column('photographer', sa.String(length=300), nullable=True),
        sa.Column('source_url', sa.String(length=2000), nullable=True),
        sa.Column('year_created', sa.Integer(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('width_px', sa.Integer(), nullable=True),
        sa.Column('height_px', sa.Integer(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_images_is_primary', 'images', ['is_primary'], unique=False)
    op.create_index('ix_images_person_id', 'images', ['person_id'], unique=False)

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('document_type', sa.String(length=30), nullable=False, server_default='other'),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_url', sa.String(length=2000), nullable=True),
        sa.Column('storage_key', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_person_id', 'documents', ['person_id'], unique=False)

    # --------------------------------------------------------------------------
    # LITURGY
    # --------------------------------------------------------------------------
    op.create_table(
        'liturgical_calendars',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('rite', sa.String(length=100), nullable=False, server_default='roman'),
        sa.Column('scope', sa.String(length=30), nullable=False, server_default='universal'),
        sa.Column('country_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('religious_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['religious_order_id'], ['religious_orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_liturgical_calendar_code')
    )

    op.create_table(
        'feasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calendar_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('month', sa.SmallInteger(), nullable=True),
        sa.Column('day', sa.SmallInteger(), nullable=True),
        sa.Column('day_of_year', sa.Integer(), nullable=True),
        sa.Column('date_note', sa.String(length=200), nullable=True),
        sa.Column('is_moveable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rank', sa.String(length=30), nullable=False, server_default='memorial'),
        sa.Column('liturgical_color', sa.String(length=10), nullable=True),
        sa.Column('is_suppressed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.ForeignKeyConstraint(['calendar_id'], ['liturgical_calendars.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_feasts_calendar_id', 'feasts', ['calendar_id'], unique=False)
    op.create_index('ix_feasts_day_of_year', 'feasts', ['day_of_year'], unique=False)
    op.create_index('ix_feasts_month', 'feasts', ['month'], unique=False)
    op.create_index('ix_feasts_person_id', 'feasts', ['person_id'], unique=False)


def downgrade() -> None:
    op.drop_table('feasts')
    op.drop_table('liturgical_calendars')
    op.drop_table('documents')
    op.drop_table('images')
    op.drop_table('person_sources')
    op.drop_table('historical_sources')
    op.drop_table('bibliography')
    op.drop_table('person_tags')
    op.drop_table('person_categories')
    op.drop_table('person_orders')
    op.drop_table('person_occupations')
    op.drop_table('person_translations')
    op.drop_table('person_versions')
    op.drop_table('person_relationships')
    op.drop_table('person_quotes')
    op.drop_table('relics')
    op.drop_table('patronages')
    op.drop_table('miracles')
    op.drop_table('beatifications')
    op.drop_table('canonizations')
    op.drop_table('popes')
    op.drop_table('persons')
    op.drop_table('tags')
    op.drop_table('categories')
    op.drop_table('occupations')
    op.drop_table('states_of_life')
    op.drop_table('churches')
    op.drop_table('religious_orders')
    op.drop_table('places')
    op.drop_table('dioceses')
    op.drop_table('regions')
    op.drop_table('countries')
    op.drop_table('audit_logs')
    op.drop_table('refresh_tokens')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
