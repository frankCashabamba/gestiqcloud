"""Tests for app/schemas/base.py and app/utils/time.py — simple pure-python tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

# ── app/utils/time.py ─────────────────────────────────────────────────────────


def test_utcnow_returns_aware_datetime():
    from app.utils.time import utcnow

    result = utcnow()
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result.tzinfo == UTC


def test_utcnow_is_recent():
    from app.utils.time import utcnow

    before = datetime.now(UTC)
    result = utcnow()
    after = datetime.now(UTC)
    assert before <= result <= after


# ── app/schemas/base.py ───────────────────────────────────────────────────────


def test_uuid_base_schema():
    from app.schemas.base import UUIDBase

    uid = uuid.uuid4()
    obj = UUIDBase(id=uid)
    assert obj.id == uid


def test_tenant_mixin_schema():
    from app.schemas.base import TenantMixin

    tid = uuid.uuid4()
    obj = TenantMixin(tenant_id=tid)
    assert obj.tenant_id == tid


def test_base_entity_schema():
    from app.schemas.base import BaseEntity

    uid = uuid.uuid4()
    tid = uuid.uuid4()
    obj = BaseEntity(id=uid, tenant_id=tid)
    assert obj.id == uid
    assert obj.tenant_id == tid
