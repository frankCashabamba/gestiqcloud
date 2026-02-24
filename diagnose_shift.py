
import os, sys

SHIFT_ID = "3747a1b0-a665-420c-8de4-4f970af27d49"

# Leer DATABASE_URL
with open(".env.local") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

db_url = os.environ.get("DATABASE_URL", "")
print("DB_URL:", db_url[:80])

try:
    import psycopg2
    from urllib.parse import urlparse
except ImportError:
    print("psycopg2 no instalado, intentando con sqlalchemy...")
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url)
    with engine.connect() as conn:

        # 1. Estado del turno
        r = conn.execute(text("SELECT id, status FROM pos_shifts WHERE id = :sid"), {"sid": SHIFT_ID}).fetchone()
        print("Turno:", r)

        # 2. Tenant del turno
        r = conn.execute(text("""
            SELECT ps.status, pr.tenant_id
            FROM pos_shifts ps JOIN pos_registers pr ON pr.id = ps.register_id
            WHERE ps.id = :sid
        """), {"sid": SHIFT_ID}).fetchone()
        print("Status + tenant_id:", r)
        tenant_id = str(r[1]) if r else None

        if tenant_id:
            # 3. Config contable
            r = conn.execute(text(
                "SELECT cash_account_id, bank_account_id, sales_bakery_account_id, vat_output_account_id, loss_account_id "
                "FROM tenant_accounting_settings WHERE tenant_id = :tid"
            ), {"tid": tenant_id}).fetchone()
            print("Accounting settings:", r)

            # 4. Metodos de pago en el turno
            rows = conn.execute(text("""
                SELECT pp.method, SUM(pp.amount) as total
                FROM pos_payments pp JOIN pos_receipts pr ON pr.id = pp.receipt_id
                WHERE pr.shift_id = :sid AND pr.status = 'paid'
                GROUP BY pp.method
            """), {"sid": SHIFT_ID}).fetchall()
            print("Payment methods en turno:", rows)

            # 5. Asiento ya existente
            r = conn.execute(text(
                "SELECT id FROM journal_entries WHERE ref_doc_type = 'POS_SHIFT' AND ref_doc_id = :sid AND tenant_id = :tid"
            ), {"sid": SHIFT_ID, "tid": tenant_id}).fetchone()
            print("Existing journal entry:", r)

            # 6. Payment methods configurados para este tenant
            rows = conn.execute(text(
                "SELECT name, account_id, is_active FROM payment_methods WHERE tenant_id = :tid"
            ), {"tid": tenant_id}).fetchall()
            print("Payment methods config:", rows)
    sys.exit(0)

# Con psycopg2
u = urlparse(db_url)
conn = psycopg2.connect(
    host=u.hostname, port=u.port or 5432,
    dbname=u.path.lstrip("/"),
    user=u.username, password=u.password
)
cur = conn.cursor()

# 1. Estado del turno
cur.execute("SELECT id, status FROM pos_shifts WHERE id = %s", (SHIFT_ID,))
r = cur.fetchone()
print("Turno:", r)

# 2. Tenant del turno
cur.execute("""
    SELECT ps.status, pr.tenant_id
    FROM pos_shifts ps JOIN pos_registers pr ON pr.id = ps.register_id
    WHERE ps.id = %s
""", (SHIFT_ID,))
r = cur.fetchone()
print("Status + tenant_id:", r)
tenant_id = str(r[1]) if r else None

if tenant_id:
    # 3. Config contable
    cur.execute(
        "SELECT cash_account_id, bank_account_id, sales_bakery_account_id, vat_output_account_id, loss_account_id "
        "FROM tenant_accounting_settings WHERE tenant_id = %s", (tenant_id,)
    )
    r = cur.fetchone()
    print("Accounting settings:", r)

    # 4. Metodos de pago en turno
    cur.execute("""
        SELECT pp.method, SUM(pp.amount) as total
        FROM pos_payments pp JOIN pos_receipts pr ON pr.id = pp.receipt_id
        WHERE pr.shift_id = %s AND pr.status = 'paid'
        GROUP BY pp.method
    """, (SHIFT_ID,))
    rows = cur.fetchall()
    print("Payment methods en turno:", rows)

    # 5. Asiento ya existente
    cur.execute(
        "SELECT id FROM journal_entries WHERE ref_doc_type = 'POS_SHIFT' AND ref_doc_id = %s AND tenant_id = %s",
        (SHIFT_ID, tenant_id)
    )
    r = cur.fetchone()
    print("Existing journal entry:", r)

    # 6. Payment methods configurados
    cur.execute(
        "SELECT name, account_id, is_active FROM payment_methods WHERE tenant_id = %s", (tenant_id,)
    )
    rows = cur.fetchall()
    print("Payment methods config:", rows)

cur.close()
conn.close()
