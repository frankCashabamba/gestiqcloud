"""Cache for AI classifications."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("imports.ai.cache")


class ClassificationCache:
    """In-memory cache for classification results."""

    def __init__(self, ttl_seconds: int = 86400):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cached entries (default: 24 hours)
        """
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: dict[str, dict[str, Any]] = {}

    def _make_key(self, text: str, parsers: list) -> str:
        """Generate cache key from text and parsers."""
        # Hash the text (limit to first 5000 chars to avoid huge hashes)
        text_hash = hashlib.sha256(text[:5000].encode()).hexdigest()
        parsers_str = ",".join(sorted(parsers))
        parsers_hash = hashlib.sha256(parsers_str.encode()).hexdigest()
        return f"{text_hash[:16]}_{parsers_hash[:16]}"

    def get(self, text: str, parsers: list) -> dict[str, Any] | None:
        """
        Retrieve cached result.

        Returns:
            Cached result dict or None if not found / expired
        """
        key = self._make_key(text, parsers)

        if key not in self.cache:
            return None

        entry = self.cache[key]

        # Check if expired
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if datetime.now() - cached_at > self.ttl:
            del self.cache[key]
            logger.debug(f"Cache entry expired: {key}")
            return None

        logger.debug(f"Cache hit: {key}")
        return entry["data"]

    def set(self, text: str, parsers: list, result: dict[str, Any]) -> None:
        """
        Store classification result in cache.
        """
        key = self._make_key(text, parsers)
        self.cache[key] = {
            "data": result,
            "cached_at": datetime.now().isoformat(),
        }
        logger.debug(f"Cache miss, storing: {key}")

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        # Count expired entries
        expired = 0
        for entry in self.cache.values():
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if datetime.now() - cached_at > self.ttl:
                expired += 1

        return {
            "total_entries": len(self.cache),
            "expired_entries": expired,
            "active_entries": len(self.cache) - expired,
            "ttl_seconds": int(self.ttl.total_seconds()),
        }
