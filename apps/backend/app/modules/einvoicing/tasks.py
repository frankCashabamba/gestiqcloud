from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from celery import shared_task
from sqlalchemy import text

from app.config.database import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SRI availability circuit-breaker
# ---------------------------------------------------------------------------
# Error codes / message fragments that indicate a network/connectivity problem
# rather than a business-logic rejection from the SRI.  Only these count
# toward the "SRI is down" heuristic.
_SRI_NETWORK_ERROR_CODES = frozenset(
    {
        "TIMEOUT",
        "CONNECTION_ERROR",
        "NETWORK_ERROR",
        "SERVICE_UNAVAILABLE",
        "GATEWAY_TIMEOUT",
    }
)


def _is_sri_available(
    tenant_id: str,
    recent_window_minutes: int = 10,
    min_sample: int = 5,
    failure_threshold: float = 0.80,
) -> bool:
    """Return False when the SRI appears to be systematically unavailable.

    Queries the *recent_window_minutes* most recent sri_submissions that
    reached a terminal state (ERROR or AUTHORIZED/RECEIVED) and returns False
    only when:
      - at least *min_sample* submissions exist in the window, AND
      - at least *failure_threshold* fraction of them failed with a
        network/connectivity error code (not a validation rejection).

    A single bad submission or a low volume of traffic will **not** trigger the
    circuit breaker — the heuristic is intentionally conservative.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=recent_window_minutes)
    with SessionLocal() as db:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        rows = db.execute(
            text(
                """
                SELECT status, error_code
                FROM sri_submissions
                WHERE tenant_id = :tid
                  AND updated_at >= :cutoff
                  AND status IN ('ERROR', 'AUTHORIZED', 'RECEIVED', 'REJECTED')
                ORDER BY updated_at DESC
                LIMIT 20
                """
            ),
            {"tid": str(tenant_id), "cutoff": cutoff},
        ).fetchall()

    if len(rows) < min_sample:
        # Not enough recent data — assume SRI is reachable.
        return True

    network_failures = sum(
        1
        for row in rows
        if row[0] == "ERROR"
        and (row[1] or "").upper() in _SRI_NETWORK_ERROR_CODES
    )
    failure_ratio = network_failures / len(rows)

    if failure_ratio >= failure_threshold:
        logger.warning(
            "SRI circuit-breaker: %.0f%% of the last %d submissions in the "
            "past %d min are network failures (threshold %.0f%%).",
            failure_ratio * 100,
            len(rows),
            recent_window_minutes,
            failure_threshold * 100,
        )
        return False

    return True


# ---------------------------------------------------------------------------
# Exponential backoff helpers
# ---------------------------------------------------------------------------

def _compute_next_retry(retry_count: int) -> datetime:
    """Return the earliest UTC datetime at which a submission may be retried.

    Delay = min(2^retry_count, 60) minutes, giving the sequence:
      attempt 0 → 1 min, 1 → 2 min, 2 → 4 min, …, 6+ → 60 min (cap).
    """
    delay_minutes = min(2**retry_count, 60)
    return datetime.now(UTC) + timedelta(minutes=delay_minutes)


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.sign_and_send")
def sign_and_send(invoice_id: int, tenant_id: str | None = None) -> dict:
    """
    Stub: signs and sends an invoice to SRI (Ecuador) asynchronously.
    Updates sri_submissions table with simulated status.
    """
    if not tenant_id:
        raise ValueError("missing_tenant_id")
    with SessionLocal() as db:
        # Scope tenant context for RLS
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        # Insert PENDING submission if not exists
        db.execute(
            text(
                """
                INSERT INTO sri_submissions(tenant_id, invoice_id, status)
                VALUES (:tid, :iid, 'PENDING')
                ON CONFLICT DO NOTHING
                """
            ),
            {"tid": str(tenant_id), "iid": invoice_id},
        )
        # Simulate success
        db.execute(
            text(
                """
                UPDATE sri_submissions
                   SET status='AUTHORIZED', authorization_number = gen_random_uuid()::text
                 WHERE invoice_id=:iid AND tenant_id=:tid
                """
            ),
            {"iid": invoice_id, "tid": str(tenant_id)},
        )
        db.commit()
    return {"invoice_id": invoice_id, "status": "AUTHORIZED"}


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.build_and_send_sii")
def build_and_send_sii(period: str, tenant_id: str | None = None) -> dict:
    """
    Stub: builds a SII batch for Spain and marks as ACCEPTED.
    """
    if not tenant_id:
        raise ValueError("missing_tenant_id")
    with SessionLocal() as db:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        res = db.execute(
            text(
                """
                INSERT INTO sii_batches(tenant_id, period, status)
                VALUES (:tid, :p, 'PENDING')
                RETURNING id
                """
            ),
            {"tid": str(tenant_id), "p": period},
        )
        batch_id = res.scalar()
        # For demo, mark accepted
        db.execute(
            text("UPDATE sii_batches SET status='ACCEPTED' WHERE id=:id AND tenant_id=:tid"),
            {"id": batch_id, "tid": str(tenant_id)},
        )
        db.commit()
    return {"batch_id": str(batch_id), "status": "ACCEPTED"}


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii")
def scheduled_build_sii() -> dict:
    """
    Beat-friendly task: computes period based on environment and enqueues a single-tenant SII build.

    Env vars:
      - EINV_SII_PERIOD_MODE: 'monthly' (YYYYMM), 'quarterly' (YYYYQn), default 'monthly'
      - EINV_TENANT_ID: tenant UUID to use (required)
    """
    import os

    tenant_id = os.getenv("EINV_TENANT_ID")
    if not tenant_id:
        return {"skipped": True, "reason": "EINV_TENANT_ID not set"}

    mode = (os.getenv("EINV_SII_PERIOD_MODE") or "monthly").lower()
    now = datetime.now(UTC)
    if mode == "quarterly":
        q = (now.month - 1) // 3 + 1
        period = f"{now.year}Q{q}"
    else:
        period = f"{now.year}{now.month:02d}"

    # run synchronously in this task to keep logs together
    return build_and_send_sii(period, tenant_id)


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.scheduled_retry")
def scheduled_retry() -> dict:
    """Retry loop for SRI/SII errors for a single tenant.

    Improvements over the naive retry:

    * **SRI circuit-breaker**: if the SRI appears to be systematically
      unavailable (≥80 % of recent submissions failed with network errors),
      the entire batch is skipped to avoid flooding the SRI with futile
      requests.

    * **Exponential backoff**: each ERROR submission tracks ``retry_count``
      and ``next_retry_at``.  Only submissions whose ``next_retry_at`` is in
      the past (or NULL) are picked up.  After a successful send the counters
      are reset; after another failure they are incremented and
      ``next_retry_at`` is pushed forward using ``min(2^retry_count, 60)``
      minutes.

    Env vars:
      - EINV_TENANT_ID: tenant UUID (required)
      - EINV_RETRY_MAX: max items per run (default 25)
      - EINV_SII_PERIOD_MODE: 'monthly'|'quarterly' (default 'monthly')
    """
    import os

    tenant_id = os.getenv("EINV_TENANT_ID")
    if not tenant_id:
        return {"skipped": True, "reason": "EINV_TENANT_ID not set"}

    max_items = int(os.getenv("EINV_RETRY_MAX", "25") or 25)

    # ------------------------------------------------------------------
    # Circuit-breaker: skip the whole batch if SRI looks unavailable.
    # ------------------------------------------------------------------
    if not _is_sri_available(tenant_id):
        logger.warning("SRI appears unavailable, skipping retry batch")
        return {"skipped": True, "reason": "sri_unavailable"}

    retried_sri: int = 0
    retried_sii: int = 0
    now_utc = datetime.now(UTC)

    # ------------------------------------------------------------------
    # SRI: fetch eligible ERROR submissions respecting next_retry_at.
    # ------------------------------------------------------------------
    with SessionLocal() as db:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        sri_rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (invoice_id)
                       invoice_id,
                       COALESCE(retry_count, 0) AS retry_count
                FROM sri_submissions
                WHERE tenant_id = :tid
                  AND status = 'ERROR'
                  AND (next_retry_at IS NULL OR next_retry_at <= :now)
                ORDER BY invoice_id, updated_at DESC
                LIMIT :lim
                """
            ),
            {"tid": str(tenant_id), "now": now_utc, "lim": max_items},
        ).fetchall()

    for r in sri_rows:
        invoice_id: int = int(r[0])
        retry_count: int = int(r[1])
        try:
            sign_and_send(invoice_id, tenant_id)
            # Success: reset backoff counters.
            with SessionLocal() as db:
                db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                db.execute(
                    text(
                        """
                        UPDATE sri_submissions
                           SET retry_count   = 0,
                               next_retry_at = NULL
                         WHERE invoice_id = :iid
                           AND tenant_id  = :tid
                        """
                    ),
                    {"iid": invoice_id, "tid": str(tenant_id)},
                )
                db.commit()
            retried_sri += 1
        except Exception:  # noqa: BLE001
            # Failure: increment counter and schedule next attempt.
            new_count = retry_count + 1
            next_retry = _compute_next_retry(new_count)
            logger.info(
                "SRI retry failed for invoice %s (attempt %d). "
                "Next retry scheduled at %s.",
                invoice_id,
                new_count,
                next_retry.isoformat(),
            )
            try:
                with SessionLocal() as db:
                    db.execute(
                        text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
                    )
                    db.execute(
                        text(
                            """
                            UPDATE sri_submissions
                               SET retry_count   = :cnt,
                                   next_retry_at = :nxt
                             WHERE invoice_id = :iid
                               AND tenant_id  = :tid
                               AND status     = 'ERROR'
                            """
                        ),
                        {
                            "cnt": new_count,
                            "nxt": next_retry,
                            "iid": invoice_id,
                            "tid": str(tenant_id),
                        },
                    )
                    db.commit()
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Could not persist backoff state for invoice %s", invoice_id
                )

    # ------------------------------------------------------------------
    # SII: rebuild batch for current period (idempotent stub).
    # ------------------------------------------------------------------
    mode = (os.getenv("EINV_SII_PERIOD_MODE") or "monthly").lower()
    now_local = datetime.now(UTC)
    if mode == "quarterly":
        q = (now_local.month - 1) // 3 + 1
        period = f"{now_local.year}Q{q}"
    else:
        period = f"{now_local.year}{now_local.month:02d}"
    try:
        build_and_send_sii(period, tenant_id)
        retried_sii = 1
    except Exception:  # noqa: BLE001
        retried_sii = 0

    return {"sri_retried": retried_sri, "sii_retried": retried_sii}
