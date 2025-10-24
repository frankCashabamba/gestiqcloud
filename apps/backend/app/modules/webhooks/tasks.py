from __future__ import annotations

import json
import time
import hmac
import hashlib
from typing import Any, Dict

import requests
from celery import shared_task
from sqlalchemy import text

from app.config.database import SessionLocal


def _sign(secret: str, payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return sig


@shared_task(name="apps.backend.app.modules.webhooks.tasks.deliver")
def deliver(delivery_id: str) -> dict:
    with SessionLocal() as db:
        row = db.execute(
            text(
                "SELECT d.id::text, d.event, d.payload, d.target_url, s.secret FROM webhook_deliveries d LEFT JOIN webhook_subscriptions s ON s.tenant_id=d.tenant_id AND s.event=d.event WHERE d.id=CAST(:id AS uuid)"
            ),
            {"id": delivery_id},
        ).first()
        if not row:
            return {"ok": False, "error": "delivery_not_found"}
        did, event, payload, url, secret = row
        headers = {"Content-Type": "application/json", "X-Event": str(event)}
        if secret:
            headers["X-Signature"] = _sign(secret, payload)
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if 200 <= r.status_code < 300:
                db.execute(text("UPDATE webhook_deliveries SET status='SENT', attempts=attempts+1 WHERE id=CAST(:id AS uuid)"), {"id": did})
                db.commit()
                return {"ok": True}
            else:
                db.execute(text("UPDATE webhook_deliveries SET status='FAILED', attempts=attempts+1, last_error=:e WHERE id=CAST(:id AS uuid)"), {"id": did, "e": f"HTTP {r.status_code}"})
                db.commit()
                return {"ok": False, "status": r.status_code}
        except Exception as e:
            db.execute(text("UPDATE webhook_deliveries SET status='FAILED', attempts=attempts+1, last_error=:e WHERE id=CAST(:id AS uuid)"), {"id": did, "e": str(e)})
            db.commit()
            return {"ok": False, "error": str(e)}
