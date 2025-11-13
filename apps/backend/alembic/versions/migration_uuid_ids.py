"""Migrate all int IDs to UUID for consistency

Revision ID: uuid_migration_001
Revises: 
Create Date: 2025-11-11 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = "uuid_migration_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop and recreate tables with UUID PKs
    
    # 1. Migrate modulos_modulo
    op.execute("""
        CREATE TABLE modulos_modulo_new (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            old_id INTEGER UNIQUE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT true,
            icono VARCHAR(100) DEFAULT '📦',
            url VARCHAR(255),
            plantilla_inicial VARCHAR(255) NOT NULL,
            context_type VARCHAR(10) DEFAULT 'none',
            modelo_objetivo VARCHAR(255),
            filtros_contexto JSONB,
            categoria VARCHAR(50)
        )
    """)
    op.execute("""
        INSERT INTO modulos_modulo_new (
            id, old_id, name, description, active, icono, url, plantilla_inicial, context_type, modelo_objetivo, filtros_contexto, categoria
        )
        SELECT gen_random_uuid(), id, name, description, active, icono, url, plantilla_inicial, context_type, modelo_objetivo, filtros_contexto, categoria
        FROM modulos_modulo
    """)

    op.execute("""
        CREATE TABLE modulos_empresamodulo_new (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            modulo_id UUID REFERENCES modulos_modulo_new(id),
            activo BOOLEAN DEFAULT true,
            fecha_activacion DATE DEFAULT now(),
            fecha_expiracion DATE,
            plantilla_inicial VARCHAR(255)
        )
    """)
    op.execute("""
        INSERT INTO modulos_empresamodulo_new (
            tenant_id, modulo_id, activo, fecha_activacion, fecha_expiracion, plantilla_inicial
        )
        SELECT e.tenant_id, m.id, e.activo, e.fecha_activacion, e.fecha_expiracion, e.plantilla_inicial
        FROM modulos_empresamodulo e
        JOIN modulos_modulo_new m ON m.old_id = e.modulo_id
    """)

    op.execute("""
        CREATE TABLE modulos_moduloasignado_new (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            usuario_id UUID REFERENCES usuarios_usuarioempresa(id),
            modulo_id UUID REFERENCES modulos_modulo_new(id),
            fecha_asignacion TIMESTAMP DEFAULT now(),
            ver_modulo_auto BOOLEAN DEFAULT true,
            UNIQUE(usuario_id, modulo_id, tenant_id)
        )
    """)
    op.execute("""
        INSERT INTO modulos_moduloasignado_new (
            tenant_id, usuario_id, modulo_id, fecha_asignacion, ver_modulo_auto
        )
        SELECT a.tenant_id, a.usuario_id, m.id, a.fecha_asignacion, a.ver_modulo_auto
        FROM modulos_moduloasignado a
        JOIN modulos_modulo_new m ON m.old_id = a.modulo_id
    """)

    op.execute("DROP TABLE modulos_empresamodulo CASCADE")
    op.execute("DROP TABLE modulos_moduloasignado CASCADE")
    op.execute("DROP TABLE modulos_modulo CASCADE")

    op.execute("ALTER TABLE modulos_modulo_new RENAME TO modulos_modulo")
    op.execute("ALTER TABLE modulos_empresamodulo_new RENAME TO modulos_empresamodulo")
    op.execute("ALTER TABLE modulos_moduloasignado_new RENAME TO modulos_moduloasignado")
    op.execute("ALTER TABLE modulos_modulo DROP COLUMN IF EXISTS old_id")
    
    # 4. Migrate core_rolempresa
    op.execute("""
        CREATE TABLE core_rolempresa_new (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            nombre VARCHAR(100) NOT NULL,
            descripcion TEXT,
            permisos JSONB DEFAULT '{}',
            rol_base_id UUID,
            creado_por_empresa BOOLEAN DEFAULT false,
            UNIQUE(tenant_id, nombre)
        )
    """)
    op.execute("INSERT INTO core_rolempresa_new (tenant_id, nombre, descripcion, permisos, rol_base_id, creado_por_empresa) SELECT tenant_id, nombre, descripcion, permisos, NULL, creado_por_empresa FROM core_rolempresa")
    op.execute("DROP TABLE core_rolempresa CASCADE")
    op.execute("ALTER TABLE core_rolempresa_new RENAME TO core_rolempresa")
    
    # 5. Update PerfilUsuario to reference UUID usuario_id
    op.execute("ALTER TABLE core_perfilusuario DROP CONSTRAINT core_perfilusuario_usuario_id_fkey")
    op.execute("ALTER TABLE core_perfilusuario ALTER COLUMN usuario_id TYPE UUID USING usuario_id::UUID")
    op.execute("ALTER TABLE core_perfilusuario ADD CONSTRAINT core_perfilusuario_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES usuarios_usuarioempresa(id)")


def downgrade() -> None:
    # Revert changes - restore int-based IDs
    op.execute("DROP TABLE IF EXISTS modulos_modulo CASCADE")
    op.execute("DROP TABLE IF EXISTS modulos_empresamodulo CASCADE")
    op.execute("DROP TABLE IF EXISTS modulos_moduloasignado CASCADE")
    op.execute("DROP TABLE IF EXISTS core_rolempresa CASCADE")
    
    # Restore original tables with int PKs (data will be lost in local environment)
    # In production, you'd preserve old table and migrate data more carefully
