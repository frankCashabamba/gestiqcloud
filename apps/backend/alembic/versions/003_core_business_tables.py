"""Create core business tables (clients, invoices, invoice_lines)

Revision ID: 003_core_business_tables
Revises: 002_rename_rolempresas_to_english
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_core_business_tables"
down_revision = "002_rename_rolempresas_to_english"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create clients, invoices, and invoice_lines tables."""

    # Create clients table
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tax_id", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("postal_code", sa.String(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clients_id"), "clients", ["id"], unique=False)
    op.create_index(op.f("ix_clients_tenant_id"), "clients", ["tenant_id"], unique=False)

    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.String(), nullable=False),
        sa.Column("proveedor", sa.String(), nullable=False),
        sa.Column("fecha_emision", sa.String(), nullable=False),
        sa.Column("monto", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente"),
        sa.Column("fecha_creacion", sa.String(), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subtotal", sa.Float(), nullable=False),
        sa.Column("iva", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["cliente_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_id"), "invoices", ["id"], unique=False)

    # Create invoice_lines table
    op.create_table(
        "invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("factura_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sector", sa.String(50), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("cantidad", sa.Float(), nullable=False),
        sa.Column("precio_unitario", sa.Float(), nullable=False),
        sa.Column("iva", sa.Float(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["factura_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop clients, invoices, and invoice_lines tables."""
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_clients_tenant_id"), table_name="clients")
    op.drop_index(op.f("ix_clients_id"), table_name="clients")
    op.drop_table("clients")
