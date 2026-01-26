# File: app/core/cache.py
"""
Módulo de cache con Redis para GestiqCloud.

Proporciona:
- Decorador @cached para endpoints
- Funciones de invalidación por patrón
- Soporte para cache por tenant
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar
from collections.abc import Callable

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_redis_available: bool | None = None

CACHE_VERSION = "v1"
CACHE_PREFIX = f"cache:{CACHE_VERSION}"


class CacheTTL(IntEnum):
    """TTLs predefinidos en segundos."""

    PRODUCTOS = 300  # 5 minutos
    CATALOGOS = 3600  # 1 hora
    EMPRESA_CONFIG = 600  # 10 minutos
    PERMISOS = 300  # 5 minutos
    TIPOS_CAMBIO = 900  # 15 minutos
    SHORT = 60  # 1 minuto
    MEDIUM = 300  # 5 minutos
    LONG = 3600  # 1 hora


async def get_redis_client():
    """
    Obtiene el cliente Redis. Retorna None si Redis no está configurado.
    """
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        from app.config.settings import get_settings

        settings = get_settings()

        if not settings.REDIS_URL:
            _redis_available = False
            logger.info("Redis no configurado (REDIS_URL vacío). Cache deshabilitado.")
            return None

        import redis.asyncio as redis

        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        await _redis_client.ping()
        _redis_available = True
        logger.info("Conexión a Redis establecida correctamente.")
        return _redis_client

    except ImportError:
        _redis_available = False
        logger.warning("redis-py no instalado. Cache deshabilitado.")
        return None
    except Exception as e:
        _redis_available = False
        logger.warning(f"No se pudo conectar a Redis: {e}. Cache deshabilitado.")
        return None


def build_cache_key(tenant_id: str | UUID, domain: str, *parts: str) -> str:
    """
    Construye una clave de cache con formato consistente.

    Args:
        tenant_id: ID del tenant
        domain: Dominio del cache (productos, catalogos, empresa, etc.)
        *parts: Partes adicionales de la clave

    Returns:
        Clave formateada: cache:v1:tenant:{tenant_id}:{domain}:{parts...}
    """
    key_parts = [CACHE_PREFIX, "tenant", str(tenant_id), domain]
    key_parts.extend(str(p) for p in parts)
    return ":".join(key_parts)


def hash_params(**params: Any) -> str:
    """Genera un hash de los parámetros para usar en claves de cache."""
    sorted_params = sorted(params.items())
    param_str = json.dumps(sorted_params, sort_keys=True, default=str)
    return hashlib.md5(param_str.encode()).hexdigest()[:12]


async def cache_get(key: str) -> Any | None:
    """
    Obtiene un valor del cache.

    Args:
        key: Clave del cache

    Returns:
        Valor deserializado o None si no existe/error
    """
    client = await get_redis_client()
    if not client:
        return None

    try:
        value = await client.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Error leyendo cache [{key}]: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = CacheTTL.MEDIUM) -> bool:
    """
    Guarda un valor en el cache.

    Args:
        key: Clave del cache
        value: Valor a guardar (será serializado a JSON)
        ttl: Tiempo de vida en segundos

    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    client = await get_redis_client()
    if not client:
        return False

    try:
        serialized = json.dumps(value, default=str)
        await client.setex(key, ttl, serialized)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Error escribiendo cache [{key}]: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """
    Elimina una clave del cache.

    Args:
        key: Clave a eliminar

    Returns:
        True si se eliminó, False en caso contrario
    """
    client = await get_redis_client()
    if not client:
        return False

    try:
        await client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except Exception as e:
        logger.warning(f"Error eliminando cache [{key}]: {e}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """
    Invalida todas las claves que coincidan con el patrón.

    Args:
        pattern: Patrón de claves (e.g., "cache:v1:tenant:123:productos:*")

    Returns:
        Número de claves eliminadas
    """
    client = await get_redis_client()
    if not client:
        return 0

    try:
        deleted = 0
        cursor = 0

        while True:
            cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        if deleted > 0:
            logger.info(f"Cache INVALIDATE: {pattern} ({deleted} claves)")
        return deleted
    except Exception as e:
        logger.warning(f"Error invalidando cache [{pattern}]: {e}")
        return 0


async def invalidate_tenant_domain(tenant_id: str | UUID, domain: str) -> int:
    """
    Invalida todo el cache de un dominio para un tenant.

    Args:
        tenant_id: ID del tenant
        domain: Dominio (productos, catalogos, empresa, etc.)

    Returns:
        Número de claves eliminadas
    """
    pattern = build_cache_key(tenant_id, domain, "*")
    return await invalidate_pattern(pattern)


async def invalidate_tenant_all(tenant_id: str | UUID) -> int:
    """
    Invalida TODO el cache de un tenant.

    Args:
        tenant_id: ID del tenant

    Returns:
        Número de claves eliminadas
    """
    pattern = f"{CACHE_PREFIX}:tenant:{tenant_id}:*"
    return await invalidate_pattern(pattern)


P = ParamSpec("P")
R = TypeVar("R")


def cached(
    ttl: int = CacheTTL.MEDIUM,
    key_builder: Callable[..., str] | None = None,
    domain: str = "default",
    include_params: list[str] | None = None,
    exclude_params: list[str] | None = None,
):
    """
    Decorador para cachear resultados de funciones/endpoints.

    Args:
        ttl: Tiempo de vida en segundos
        key_builder: Función opcional para construir la clave.
                     Recibe (tenant_id, **kwargs) y retorna string.
        domain: Dominio para la clave (default: "default")
        include_params: Lista de parámetros a incluir en la clave
        exclude_params: Lista de parámetros a excluir de la clave

    Ejemplo:
        @cached(ttl=CacheTTL.PRODUCTOS, domain="productos")
        async def listar_productos(tenant_id: UUID, skip: int = 0):
            ...

        @cached(
            ttl=CacheTTL.CATALOGOS,
            key_builder=lambda tenant_id, tipo, **_: f"catalogos:{tipo}"
        )
        async def obtener_catalogo(tenant_id: UUID, tipo: str):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Extraer tenant_id de kwargs o args
            tenant_id = kwargs.get("tenant_id")
            if tenant_id is None and args:
                tenant_id = args[0]

            if tenant_id is None:
                logger.debug(f"Cache SKIP: {func.__name__} (no tenant_id)")
                return await func(*args, **kwargs)

            # Construir clave
            if key_builder:
                key_suffix = key_builder(tenant_id=tenant_id, **kwargs)
                cache_key = build_cache_key(tenant_id, domain, key_suffix)
            else:
                # Filtrar parámetros
                cache_params = dict(kwargs)
                cache_params.pop("tenant_id", None)

                if include_params:
                    cache_params = {k: v for k, v in cache_params.items() if k in include_params}
                elif exclude_params:
                    cache_params = {
                        k: v for k, v in cache_params.items() if k not in exclude_params
                    }

                param_hash = hash_params(**cache_params) if cache_params else "default"
                cache_key = build_cache_key(tenant_id, domain, func.__name__, param_hash)

            # Intentar obtener del cache
            cached_value = await cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Ejecutar función y cachear resultado
            result = await func(*args, **kwargs)

            # Solo cachear si hay resultado
            if result is not None:
                await cache_set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


class CacheInvalidator:
    """
    Helper para invalidar cache en operaciones CRUD.

    Ejemplo:
        invalidator = CacheInvalidator(tenant_id)
        await invalidator.productos()  # Invalida cache de productos
        await invalidator.empresa()    # Invalida cache de empresa
    """

    def __init__(self, tenant_id: str | UUID):
        self.tenant_id = tenant_id

    async def productos(self) -> int:
        """Invalida cache de productos."""
        return await invalidate_tenant_domain(self.tenant_id, "productos")

    async def catalogos(self, tipo: str | None = None) -> int:
        """Invalida cache de catálogos (todos o uno específico)."""
        if tipo:
            key = build_cache_key(self.tenant_id, "catalogos", tipo)
            return 1 if await cache_delete(key) else 0
        return await invalidate_tenant_domain(self.tenant_id, "catalogos")

    async def empresa(self) -> int:
        """Invalida cache de configuración de empresa."""
        return await invalidate_tenant_domain(self.tenant_id, "empresa")

    async def permisos(self) -> int:
        """Invalida cache de permisos."""
        return await invalidate_tenant_domain(self.tenant_id, "permisos")

    async def all(self) -> int:
        """Invalida todo el cache del tenant."""
        return await invalidate_tenant_all(self.tenant_id)


async def health_check() -> dict[str, Any]:
    """
    Verifica el estado de la conexión a Redis.

    Returns:
        Dict con estado de salud del cache
    """
    client = await get_redis_client()

    if client is None:
        return {
            "status": "disabled",
            "message": "Redis no configurado o no disponible",
        }

    try:
        info = await client.info("server")
        memory = await client.info("memory")

        return {
            "status": "healthy",
            "redis_version": info.get("redis_version"),
            "used_memory_human": memory.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
