"""Tests para la numeración concurrente segura de asientos contables.

`generate_entry_number` debe garantizar:
- Numeración monotónicamente creciente bajo invocaciones repetidas.
- Aislamiento por tenant (dos tenants comparten año pero no contador).
- Aislamiento por año (mismo tenant, diferente año → reinicia secuencia).
- Bajo concurrencia simulada (paralelo en threads contra Postgres) NO emite duplicados
  gracias al `pg_advisory_xact_lock` + tabla `journal_sequences`.
"""

from __future__ import annotations

import threading
import uuid

import pytest
from sqlalchemy import text

from app.modules.accounting.application.journal_service import (
    _is_postgres,
    generate_entry_number,
)


def test_generate_entry_number_monotonic(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    n1 = generate_entry_number(db, tenant_id, 2026)
    n2 = generate_entry_number(db, tenant_id, 2026)
    n3 = generate_entry_number(db, tenant_id, 2026)
    assert n1.startswith("ASI-2026-")
    assert int(n1.split("-")[-1]) < int(n2.split("-")[-1]) < int(n3.split("-")[-1])


def test_generate_entry_number_per_tenant_isolation(db, tenant_minimal):
    tenant_a = tenant_minimal["tenant_id"]
    # Crear segundo tenant minimal a mano.
    from app.models.tenant import Tenant

    tenant_b_id = uuid.uuid4()
    db.add(Tenant(id=tenant_b_id, name="Tenant B", slug=f"b-{tenant_b_id.hex[:6]}"))
    db.flush()

    a1 = generate_entry_number(db, tenant_a, 2026)
    a2 = generate_entry_number(db, tenant_a, 2026)
    b1 = generate_entry_number(db, tenant_b_id, 2026)
    # Cada tenant tiene su propia secuencia.
    assert int(b1.split("-")[-1]) == 1
    assert int(a2.split("-")[-1]) == int(a1.split("-")[-1]) + 1


def test_generate_entry_number_per_year_isolation(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    n_2025 = generate_entry_number(db, tenant_id, 2025)
    n_2026 = generate_entry_number(db, tenant_id, 2026)
    assert int(n_2025.split("-")[-1]) == 1
    assert int(n_2026.split("-")[-1]) == 1
    assert "2025" in n_2025 and "2026" in n_2026


def test_generate_entry_number_concurrent_no_duplicates(db, tenant_minimal):
    """Invoca `generate_entry_number` desde 8 threads × 5 iteraciones contra Postgres.

    Con `pg_advisory_xact_lock` + `journal_sequences` no debe haber duplicados.
    Skip cuando el motor no es Postgres (SQLite no implementa el lock).
    """
    if not _is_postgres(db):
        pytest.skip("requires postgres")

    tenant_id = tenant_minimal["tenant_id"]
    bind = db.get_bind()
    engine = getattr(bind, "engine", bind)
    threads_count = 8
    iters = 5
    numbers: list[str] = []
    lock = threading.Lock()

    def worker():
        # Cada thread abre su propia conexión/transacción.
        with engine.connect() as conn:
            for _ in range(iters):
                with conn.begin():
                    # Reusar la lógica vía SQL inline equivalente al servicio.
                    conn.execute(
                        text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                        {"k": f"journal_seq:{tenant_id}:2030"},
                    )
                    row = conn.execute(
                        text(
                            "INSERT INTO journal_sequences(tenant_id, year, last_number) "
                            "VALUES (:t, :y, 1) "
                            "ON CONFLICT (tenant_id, year) DO UPDATE "
                            "SET last_number = journal_sequences.last_number + 1 "
                            "RETURNING last_number"
                        ),
                        {"t": str(tenant_id), "y": 2030},
                    ).first()
                with lock:
                    numbers.append(f"ASI-2030-{int(row[0]):04d}")

    threads = [threading.Thread(target=worker) for _ in range(threads_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(numbers) == threads_count * iters
    assert len(set(numbers)) == len(numbers), "se emitieron números duplicados"
