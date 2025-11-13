#!/usr/bin/env python
"""
Seed simple: Receta 'Pan Tapado' usando psycopg2 directo (sin SQLAlchemy RLS issues).
"""
import os
import psycopg2

tenant_id = "3b102e93-496b-407a-bceb-0f203d3ec28b"

dsn = os.getenv("DB_DSN") or "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"

conn = psycopg2.connect(dsn)
cur = conn.cursor()

# Disable RLS
cur.execute("SET row_security = off")
cur.execute("SET app.tenant_id = %s", (tenant_id,))

# Producto final
cur.execute("""
    INSERT INTO products (tenant_id, name, price, unit, category)
    VALUES (%s, 'Pan Tapado', 0, 'unit', 'Panadería')
    ON CONFLICT DO NOTHING
    RETURNING id
""", (tenant_id,))

result = cur.fetchone()
if result:
    print(f"✔ Producto creado: {result[0]}")
else:
    print("Producto ya existe")

conn.commit()
cur.close()
conn.close()
