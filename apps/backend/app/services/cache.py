"""Cache service for sector configurations and other dynamic data."""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger("services.cache")

# In-memory cache for sector configurations
# TODO: Migrar a Redis cuando sea necesario para multi-instance
_SECTOR_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_TTL = timedelta(minutes=5)  # 5 minutos


class SectorConfigCache:
    """In-memory cache para configuraciones de sector."""

    @staticmethod
    def get(sector_code: str) -> dict[str, Any] | None:
        """Obtener config en cache."""
        key = f"sector_config:{sector_code}"

        if key not in _SECTOR_CACHE:
            return None

        entry = _SECTOR_CACHE[key]
        cached_at = datetime.fromisoformat(entry["cached_at"])

        # Verificar si expiró
        if datetime.now() - cached_at > _CACHE_TTL:
            del _SECTOR_CACHE[key]
            logger.debug(f"Cache entry expired: {key}")
            return None

        logger.debug(f"Cache hit: {key}")
        return entry["data"]

    @staticmethod
    def set(sector_code: str, config: dict[str, Any]) -> None:
        """Guardar config en cache."""
        key = f"sector_config:{sector_code}"
        _SECTOR_CACHE[key] = {"data": config, "cached_at": datetime.now().isoformat()}
        logger.debug(f"Cache set: {key}")

    @staticmethod
    def invalidate(sector_code: str) -> None:
        """Invalidar cache de un sector."""
        key = f"sector_config:{sector_code}"
        if key in _SECTOR_CACHE:
            del _SECTOR_CACHE[key]
            logger.info(f"Cache invalidated: {key}")

    @staticmethod
    def clear_all() -> None:
        """Limpiar todo el cache."""
        _SECTOR_CACHE.clear()
        logger.info("All sector cache cleared")


def invalidate_sector_cache(sector_code: str) -> None:
    """
    Invalida todos los caches relacionados a un sector.

    Se llama después de actualizar la configuración en el admin.
    """
    keys_to_invalidate = [
        f"sector_config:{sector_code}",
        f"sector_full_config:{sector_code}",
        f"sector_features:{sector_code}",
        f"sector_placeholders:{sector_code}",
        f"sector_units:{sector_code}",
        f"sector_fields:{sector_code}",
        f"sector_validations:{sector_code}",
    ]

    for key in keys_to_invalidate:
        if key in _SECTOR_CACHE:
            del _SECTOR_CACHE[key]

    logger.info(f"Invalidated {len(keys_to_invalidate)} cache keys for sector: {sector_code}")
