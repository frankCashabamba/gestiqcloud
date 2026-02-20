"""Tests for EventService — event outbox publishing"""

import uuid

import app.models.core.event_outbox  # noqa: F401


class TestEventService:
    def _make_tenant(self, db):
        from app.models.tenant import Tenant

        tid = uuid.uuid4()
        t = Tenant(id=tid, name="Event Test", slug=f"evt-{tid.hex[:8]}")
        db.add(t)
        db.flush()
        return tid

    def test_publish_creates_event(self, db):
        from app.services.event_service import EventService

        tid = self._make_tenant(db)
        event = EventService.publish(
            db,
            tid,
            "sale.posted",
            payload={"sale_id": str(uuid.uuid4()), "date": "2026-02-14"},
            aggregate_type="sale",
        )
        db.flush()
        assert event is not None
        assert event.event_type == "sale.posted"
        assert event.published_at is None
        assert event.payload["date"] == "2026-02-14"

    def test_mark_published(self, db):
        from app.services.event_service import EventService

        tid = self._make_tenant(db)
        event = EventService.publish(db, tid, "test.event", payload={"key": "val"})
        db.flush()
        assert event.published_at is None
        EventService.mark_published(db, event.id)
        db.flush()
        db.refresh(event)
        assert event.published_at is not None

    def test_mark_failed(self, db):
        from app.services.event_service import EventService

        tid = self._make_tenant(db)
        event = EventService.publish(db, tid, "fail.event", payload={})
        db.flush()
        EventService.mark_failed(db, event.id, "Connection timeout")
        db.flush()
        db.refresh(event)
        assert event.retry_count == 1
        assert event.last_error == "Connection timeout"

    def test_mark_failed_increments_retry(self, db):
        from app.services.event_service import EventService

        tid = self._make_tenant(db)
        event = EventService.publish(db, tid, "retry.event", payload={})
        db.flush()
        EventService.mark_failed(db, event.id, "err1")
        db.flush()
        EventService.mark_failed(db, event.id, "err2")
        db.flush()
        db.refresh(event)
        assert event.retry_count == 2
        assert event.last_error == "err2"

    def test_get_unpublished(self, db):
        from app.services.event_service import EventService

        tid = self._make_tenant(db)
        EventService.publish(db, tid, "a.event", payload={"n": 1})
        EventService.publish(db, tid, "b.event", payload={"n": 2})
        e3 = EventService.publish(db, tid, "c.event", payload={"n": 3})
        db.flush()
        # Mark one as published
        EventService.mark_published(db, e3.id)
        db.flush()
        unpublished = EventService.get_unpublished(db)
        # Should get 2 unpublished
        event_types = {e.event_type for e in unpublished}
        assert "a.event" in event_types
        assert "b.event" in event_types
        assert "c.event" not in event_types

    def test_get_unpublished_respects_max_retries(self, db):
        from app.services.event_service import EventService

        tid = self._make_tenant(db)
        event = EventService.publish(db, tid, "exhaust.event", payload={})
        db.flush()
        # Fail 5 times (max_retries default)
        for i in range(5):
            EventService.mark_failed(db, event.id, f"err{i}")
            db.flush()
        unpublished = EventService.get_unpublished(db, max_retries=5)
        assert all(e.id != event.id for e in unpublished)


class TestEventOutboxWorker:
    def test_poll_and_process_empty(self, db):
        from app.workers.event_outbox_worker import poll_and_process

        # Should not error on empty outbox
        count = poll_and_process(batch_size=10)
        assert count >= 0
