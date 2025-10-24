"""
Create tenants table and backfill from core_empresa (idempotent)

Revision ID: a20005_tenants_bootstrap
Revises: a20000_schema_snapshot
Create Date: 2025-10-10
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a20005_tenants_bootstrap"
down_revision = "a20000_schema_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - DDL heavy
    op.execute(
        """
        -- Ensure required extension for gen_random_uuid
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";

        -- Create tenants table if missing
        CREATE TABLE IF NOT EXISTS public.tenants (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            empresa_id integer UNIQUE NOT NULL REFERENCES public.core_empresa(id) ON DELETE CASCADE,
            slug text UNIQUE,
            base_currency text,
            country_code text,
            created_at timestamptz DEFAULT now()
        );

        -- Backfill tenants from existing empresas (idempotent)
        INSERT INTO public.tenants (empresa_id, slug)
        SELECT e.id, e.slug
        FROM public.core_empresa e
        ON CONFLICT (empresa_id) DO NOTHING;
        """
    )


def downgrade() -> None:  # pragma: no cover - not automatically dropping tenants
    pass

