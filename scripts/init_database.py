#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialización completa de base de datos.

Elimina y recrea TODO el esquema desde cero usando complete_schema.sql
¡ADVERTENCIA! Esto BORRARÁ TODOS LOS DATOS.

Uso:
    python scripts/init_database.py                    # Dev (local)
    python scripts/init_database.py --confirm          # Requiere confirmación
    python scripts/init_database.py --env production   # Producción (con doble confirmación)
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Fix Windows encoding
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Colores para terminal (desactivados en Windows si hay problemas)
USE_COLORS = sys.platform != "win32" and os.getenv("NO_COLOR") is None


class Colors:
    RED = "\033[91m" if USE_COLORS else ""
    GREEN = "\033[92m" if USE_COLORS else ""
    YELLOW = "\033[93m" if USE_COLORS else ""
    BLUE = "\033[94m" if USE_COLORS else ""
    MAGENTA = "\033[95m" if USE_COLORS else ""
    CYAN = "\033[96m" if USE_COLORS else ""
    END = "\033[0m" if USE_COLORS else ""
    BOLD = "\033[1m" if USE_COLORS else ""


def print_step(msg: str, level: str = "info"):
    """Imprime mensaje con color según nivel."""
    color = {
        "info": Colors.BLUE,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED,
        "title": Colors.MAGENTA + Colors.BOLD,
    }.get(level, Colors.CYAN)

    print(f"{color}{msg}{Colors.END}")


def get_db_connection_string() -> str:
    """Obtiene string de conexión desde variable de entorno."""
    db_url = os.getenv("DB_DSN") or os.getenv("DATABASE_URL")

    if not db_url:
        # Valores por defecto para desarrollo
        db_url = "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
        print_step(f"⚠️ DB_DSN no encontrado. Usando: {db_url}", "warning")

    return db_url


def parse_connection_string(db_url: str) -> dict:
    """Parsea connection string a componentes."""
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(db_url)

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
        "sslmode": parse_qs(parsed.query).get("sslmode", ["prefer"])[0],
    }


def drop_all_tables(conn):
    """Elimina TODAS las tablas, tipos y extensiones."""
    print_step("\n[DROP] Eliminando schema existente...", "warning")

    with conn.cursor() as cur:
        # Deshabilitar RLS temporalmente
        cur.execute("""
            DO $$ 
            DECLARE r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
                LOOP
                    EXECUTE 'ALTER TABLE IF EXISTS ' || quote_ident(r.tablename) || ' DISABLE ROW LEVEL SECURITY';
                END LOOP;
            END $$;
        """)

        # Drop todas las tablas
        cur.execute("""
            DROP SCHEMA IF EXISTS public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
        """)

        conn.commit()
        print_step("   ✓ Todas las tablas eliminadas", "success")


def create_schema_from_file(conn, schema_file: Path):
    """Ejecuta el archivo complete_schema.sql."""
    print_step(f"\n[SQL] Ejecutando schema: {schema_file.name}", "info")

    if not schema_file.exists():
        print_step(f"❌ Archivo no encontrado: {schema_file}", "error")
        sys.exit(1)

    sql_content = schema_file.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        try:
            cur.execute(sql_content)
            conn.commit()
            print_step("   ✓ Schema creado exitosamente", "success")
        except Exception as e:
            conn.rollback()
            print_step(f"❌ Error ejecutando SQL: {e}", "error")
            raise


def verify_schema(conn):
    """Verifica que el schema se haya creado correctamente."""
    print_step("\n[CHECK] Verificando instalación...", "info")

    with conn.cursor() as cur:
        # Contar tablas
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        table_count = cur.fetchone()[0]
        print_step(f"   ✓ Tablas creadas: {table_count}", "success")

        # Verificar tablas críticas
        critical_tables = [
            "tenants",
            "products",
            "clients",
            "facturas",
            "import_batches",
        ]
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = ANY(%s)
        """,
            (critical_tables,),
        )

        found_tables = [row[0] for row in cur.fetchall()]
        missing = set(critical_tables) - set(found_tables)

        if missing:
            print_step(f"   ⚠️ Tablas faltantes: {', '.join(missing)}", "warning")
        else:
            print_step("   ✓ Todas las tablas críticas presentes", "success")

        # Verificar seed data
        cur.execute("SELECT COUNT(*) FROM core_tipoempresa")
        tipo_empresa_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM core_rolbase")
        roles_count = cur.fetchone()[0]

        print_step(f"   ✓ Tipos de empresa: {tipo_empresa_count}", "success")
        print_step(f"   ✓ Roles base: {roles_count}", "success")

        # Verificar extensiones
        cur.execute("""
            SELECT extname FROM pg_extension 
            WHERE extname IN ('uuid-ossp', 'pg_trgm')
        """)
        extensions = [row[0] for row in cur.fetchall()]
        print_step(f"   ✓ Extensiones: {', '.join(extensions)}", "success")


def create_demo_tenant(conn):
    """Crea un tenant de demostración."""
    print_step("\n[DEMO] Creando tenant demo...", "info")

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tenants (
                nombre, slug, ruc, country_code, base_currency,
                telefono, ciudad, pais, activo
            ) VALUES (
                'Empresa Demo', 'demo', 'B12345678', 'ES', 'EUR',
                '+34 900 123 456', 'Madrid', 'España', TRUE
            )
            ON CONFLICT (slug) DO NOTHING
            RETURNING id, nombre
        """)

        result = cur.fetchone()
        if result:
            tenant_id, nombre = result
            print_step(f"   ✓ Tenant creado: {nombre} ({tenant_id})", "success")

            # Crear categoría demo
            cur.execute(
                """
                INSERT INTO product_categories (tenant_id, name, description)
                VALUES (%s, 'General', 'Categoría general')
                RETURNING id
            """,
                (tenant_id,),
            )
            cat_id = cur.fetchone()[0]

            # Crear productos demo
            cur.execute(
                """
                INSERT INTO products (tenant_id, category_id, name, sku, price, stock, unit)
                VALUES 
                    (%s, %s, 'Producto Demo 1', 'DEMO-001', 10.50, 100, 'unidad'),
                    (%s, %s, 'Producto Demo 2', 'DEMO-002', 25.00, 50, 'unidad'),
                    (%s, %s, 'Producto Demo 3', 'DEMO-003', 5.99, 200, 'kg')
            """,
                (tenant_id, cat_id, tenant_id, cat_id, tenant_id, cat_id),
            )

            print_step("   ✓ 3 productos demo creados", "success")

            conn.commit()
        else:
            print_step("   ℹ️ Tenant demo ya existe", "info")


def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Inicializa la base de datos desde cero"
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Requiere confirmación manual"
    )
    parser.add_argument(
        "--env",
        default="development",
        choices=["development", "production"],
        help="Ambiente de ejecución",
    )
    parser.add_argument("--no-demo", action="store_true", help="No crear datos demo")
    args = parser.parse_args()

    # Banner
    print_step("\n" + "=" * 60, "title")
    print_step("  GESTIQCLOUD - Inicialización de Base de Datos", "title")
    print_step("=" * 60 + "\n", "title")

    # Advertencia
    print_step("[WARNING] Este script ELIMINARA TODOS LOS DATOS", "warning")
    print_step("[WARNING] Solo usar en desarrollo o con backup completo", "warning")

    # Confirmación
    if args.env == "production" or args.confirm:
        print_step("\nEstas seguro? Escribe 'BORRAR TODO' para confirmar:", "warning")
        confirmation = input("> ")
        if confirmation != "BORRAR TODO":
            print_step("[X] Cancelado por el usuario", "error")
            sys.exit(0)

    # Obtener conexión
    db_url = get_db_connection_string()
    db_params = parse_connection_string(db_url)

    print_step(
        f"\n[DB] Conectando a: {db_params['host']}:{db_params['port']}/{db_params['database']}",
        "info",
    )

    try:
        # Conectar
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Ejecutar pasos
        drop_all_tables(conn)

        schema_file = (
            Path(__file__).parent.parent / "ops" / "schema" / "complete_schema.sql"
        )
        create_schema_from_file(conn, schema_file)

        verify_schema(conn)

        if not args.no_demo:
            create_demo_tenant(conn)

        # Resumen final
        print_step("\n" + "=" * 60, "title")
        print_step("  [OK] INICIALIZACION COMPLETADA EXITOSAMENTE", "title")
        print_step("=" * 60, "title")

        print_step("\n[NEXT] Proximos pasos:", "info")
        print_step("   1. Reinicia el backend: docker-compose restart backend", "info")
        print_step("   2. Verifica con: http://localhost:8000/docs", "info")
        print_step("   3. Crea tu primer tenant via API o admin panel\n", "info")

        conn.close()

    except psycopg2.Error as e:
        print_step(f"\n[ERROR] Error de base de datos: {e}", "error")
        sys.exit(1)
    except Exception as e:
        print_step(f"\n[ERROR] Error inesperado: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
