#!/usr/bin/env python3
import os
import sys

# Activate venv
os.chdir(r"c:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud")
sys.path.insert(
    0, r"c:\Users\frank\OneDrive\Documentos\GitHub\gestiqcloud\.venv\Lib\site-packages"
)

try:
    import psycopg2

    # Intenta conectar
    print("Intentando conectar a PostgreSQL...")
    conn = psycopg2.connect(
        dbname="gestiqclouddb_dev",
        user="postgres",
        password="root",
        host="localhost",
        port=5432,
        client_encoding="UTF8",
    )

    cur = conn.cursor()

    # Verificar encoding
    cur.execute("""
        SELECT datname, pg_encoding_to_char(encoding)
        FROM pg_database
        WHERE datname = 'gestiqclouddb_dev'
    """)
    result = cur.fetchone()
    if result:
        print(f"Base de datos: {result[0]}, Encoding: {result[1]}")
    else:
        print("No se encontró la base de datos")

    # Verificar variables de sesión
    cur.execute("SHOW client_encoding")
    client_enc = cur.fetchone()[0]
    print(f"Client encoding: {client_enc}")

    cur.close()
    conn.close()
    print("Conexión exitosa")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
