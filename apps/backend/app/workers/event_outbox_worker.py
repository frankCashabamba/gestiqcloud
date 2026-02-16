"""Event Outbox Poller Worker — Processes unpublished events"""
import logging
import time

from app.config.database import session_scope
from app.models.core.event_outbox import EventOutbox
from app.services.event_service import EventService

logger = logging.getLogger(__name__)

# Event handlers registry
EVENT_HANDLERS: dict[str, list] = {}


def register_handler(event_type: str, handler):
    """Register a handler for an event type."""
    EVENT_HANDLERS.setdefault(event_type, []).append(handler)


def _process_event(event: EventOutbox) -> None:
    """Process a single event by calling registered handlers."""
    handlers = EVENT_HANDLERS.get(event.event_type, [])
    if not handlers:
        # No handlers registered — still mark as published (acknowledged)
        logger.debug("No handlers for event type: %s", event.event_type)
        return

    for handler in handlers:
        try:
            handler(event)
        except Exception as e:
            logger.error(
                "Handler %s failed for event %s: %s",
                handler.__name__, event.id, e,
            )
            raise


def poll_and_process(batch_size: int = 50, max_retries: int = 5) -> int:
    """Poll for unpublished events and process them. Returns count processed."""
    processed = 0
    with session_scope() as db:
        events = EventService.get_unpublished(db, limit=batch_size, max_retries=max_retries)
        for event in events:
            try:
                _process_event(event)
                EventService.mark_published(db, event.id)
                processed += 1
            except Exception as e:
                EventService.mark_failed(db, event.id, str(e))
                logger.warning("Event %s failed: %s", event.id, e)
    return processed


def run_poller(interval_seconds: int = 30, batch_size: int = 50):
    """Run the poller loop (blocking). For use in a standalone worker process."""
    logger.info("Event outbox poller started (interval=%ds)", interval_seconds)
    while True:
        try:
            count = poll_and_process(batch_size=batch_size)
            if count > 0:
                logger.info("Processed %d events", count)
        except Exception as e:
            logger.error("Poller cycle failed: %s", e)
        time.sleep(interval_seconds)


# Register default handlers for recalculation triggers
def _handle_sale_posted(event: EventOutbox):
    """Trigger profit recalculation when a sale is posted."""
    from datetime import date as date_type

    from app.config.database import session_scope
    from app.modules.reports.application.recalculation_service import RecalculationService

    payload = event.payload or {}
    sale_date = payload.get("date")
    if not sale_date:
        return
    if isinstance(sale_date, str):
        sale_date = date_type.fromisoformat(sale_date)

    with session_scope() as db:
        svc = RecalculationService(db)
        svc.recalculate_daily(event.tenant_id, sale_date)


def _handle_expense_posted(event: EventOutbox):
    """Trigger profit recalculation when an expense is posted."""
    from datetime import date as date_type

    from app.config.database import session_scope
    from app.modules.reports.application.recalculation_service import RecalculationService

    payload = event.payload or {}
    expense_date = payload.get("date")
    if not expense_date:
        return
    if isinstance(expense_date, str):
        expense_date = date_type.fromisoformat(expense_date)

    with session_scope() as db:
        svc = RecalculationService(db)
        svc.recalculate_daily(event.tenant_id, expense_date)


# Register handlers
register_handler("sale.posted", _handle_sale_posted)
register_handler("sale.updated", _handle_sale_posted)
register_handler("expense.posted", _handle_expense_posted)
register_handler("expense.updated", _handle_expense_posted)
