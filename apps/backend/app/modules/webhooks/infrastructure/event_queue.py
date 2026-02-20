"""Event queue implementation using Redis."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import redis

logger = logging.getLogger(__name__)


class WebhookEventQueue:
    """Redis-based queue for webhook deliveries."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

        self.queue_key = "webhooks:deliveries:pending"
        self.processing_key = "webhooks:deliveries:processing"

    def enqueue(
        self,
        delivery_id: UUID,
        subscription_id: UUID,
        target_url: str,
        secret: str,
        payload: dict[str, Any],
        attempt_number: int = 1,
    ) -> bool:
        """Enqueue a webhook delivery."""
        if not self.redis_client:
            logger.error("Redis client not available")
            return False

        try:
            message = {
                "delivery_id": str(delivery_id),
                "subscription_id": str(subscription_id),
                "target_url": target_url,
                "secret": secret,
                "payload": payload,
                "attempt_number": attempt_number,
                "enqueued_at": datetime.utcnow().isoformat(),
            }

            self.redis_client.rpush(self.queue_key, json.dumps(message))
            logger.info(f"Enqueued webhook delivery: {delivery_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to enqueue webhook: {e}")
            return False

    def dequeue(self) -> dict[str, Any] | None:
        """Dequeue next pending delivery."""
        if not self.redis_client:
            return None

        try:
            message = self.redis_client.lpop(self.queue_key)
            if message:
                return json.loads(message)
            return None

        except Exception as e:
            logger.exception(f"Failed to dequeue webhook: {e}")
            return None

    def move_to_processing(self, message: dict[str, Any]) -> None:
        """Move message to processing set."""
        if not self.redis_client:
            return

        try:
            delivery_id = message.get("delivery_id")
            self.redis_client.sadd(self.processing_key, delivery_id)
        except Exception as e:
            logger.exception(f"Failed to move to processing: {e}")

    def mark_processed(self, delivery_id: str) -> None:
        """Remove from processing set."""
        if not self.redis_client:
            return

        try:
            self.redis_client.srem(self.processing_key, delivery_id)
        except Exception as e:
            logger.exception(f"Failed to mark processed: {e}")

    def queue_size(self) -> int:
        """Get number of pending deliveries."""
        if not self.redis_client:
            return 0

        try:
            return self.redis_client.llen(self.queue_key)
        except Exception as e:
            logger.exception(f"Failed to get queue size: {e}")
            return 0

    def processing_count(self) -> int:
        """Get number of deliveries being processed."""
        if not self.redis_client:
            return 0

        try:
            return self.redis_client.scard(self.processing_key)
        except Exception as e:
            logger.exception(f"Failed to get processing count: {e}")
            return 0

    def clear(self) -> None:
        """Clear all pending deliveries."""
        if not self.redis_client:
            return

        try:
            self.redis_client.delete(self.queue_key)
            logger.warning("Cleared webhook delivery queue")
        except Exception as e:
            logger.exception(f"Failed to clear queue: {e}")
