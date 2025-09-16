"""populate empresa slug and enforce not null

Revision ID: 202409150001
Revises: fa834ea47e28
Create Date: 2025-09-15 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import re


# revision identifiers, used by Alembic.
revision = '202409150001'
down_revision = 'fa834ea47e28'
branch_labels = None
depends_on = None


def _slugify(value: str) -> str:
    value = value or ''
    # basic ascii slugify: lowercase, strip accents, replace non-alnum with hyphen
    try:
        import unicodedata
        value = unicodedata.normalize('NFKD', value)
        value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    except Exception:
        pass
    value = value.lower()
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    value = re.sub(r'-{2,}', '-', value)
    return value or 'empresa'


def upgrade() -> None:
    bind = op.get_bind()
    # Fetch empresas with NULL slug
    empresas = list(bind.execute(text("SELECT id, nombre FROM core_empresa WHERE slug IS NULL OR slug = ''")).fetchall())

    # Build existing slugs set to ensure uniqueness
    existing = set(row[0] for row in bind.execute(text("SELECT slug FROM core_empresa WHERE slug IS NOT NULL AND slug <> ''")).fetchall())

    for row in empresas:
        emp_id, nombre = row[0], row[1]
        base = _slugify(nombre or f"empresa-{emp_id}")
        slug = base
        i = 2
        while slug in existing:
            slug = f"{base}-{i}"
            i += 1
        bind.execute(text("UPDATE core_empresa SET slug = :slug WHERE id = :id"), {"slug": slug, "id": emp_id})
        existing.add(slug)

    # Enforce NOT NULL on slug and ensure unique constraint exists
    with op.batch_alter_table('core_empresa') as batch_op:
        batch_op.alter_column('slug', existing_type=sa.String(length=100), nullable=False)
        # Create unique constraint if it doesn't exist; name chosen deterministically
        try:
            batch_op.create_unique_constraint('uq_core_empresa_slug', ['slug'])
        except Exception:
            # Constraint may already exist; ignore
            pass


def downgrade() -> None:
    # Relax NOT NULL (cannot safely drop unique without knowing prior name)
    with op.batch_alter_table('core_empresa') as batch_op:
        batch_op.alter_column('slug', existing_type=sa.String(length=100), nullable=True)
        try:
            batch_op.drop_constraint('uq_core_empresa_slug', type_='unique')
        except Exception:
            pass

