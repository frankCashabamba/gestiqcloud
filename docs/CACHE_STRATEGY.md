# Estrategia de Cache con Redis

## Resumen

GestiqCloud utiliza Redis como capa de cache para mejorar el rendimiento y reducir la carga en la base de datos. Esta documentación describe los endpoints que usan cache, TTLs recomendados y estrategias de invalidación.

## Configuración de Redis

### Variables de Entorno

```bash
# .env
REDIS_URL=redis://localhost:6379/0

# Producción (con autenticación)
REDIS_URL=redis://:password@redis-host:6379/0

# Con SSL (Render, Railway, etc.)
REDIS_URL=rediss://:password@redis-host:6379/0
```

### Configuración Recomendada de Redis

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
```

## TTLs por Tipo de Dato

| Tipo de Dato | TTL | Justificación |
|--------------|-----|---------------|
| **Productos** | 5 min (300s) | Cambios frecuentes en stock/precios |
| **Catálogos** | 1 hora (3600s) | Datos semi-estáticos (categorías, unidades) |
| **Configuración Empresa** | 10 min (600s) | Cambios poco frecuentes pero críticos |
| **Sesiones** | 30 días | Manejado por el sistema de autenticación |
| **Tipos de Cambio** | 15 min (900s) | Datos externos con actualización periódica |
| **Permisos Usuario** | 5 min (300s) | Balance entre seguridad y rendimiento |

## Endpoints que Usan Cache

### Productos (`/api/v1/products`)

```python
# GET /api/v1/products - Lista de productos
# Key: cache:tenant:{tenant_id}:productos:list:{hash_params}
# TTL: 300 segundos

# GET /api/v1/products/{id} - Producto individual
# Key: cache:tenant:{tenant_id}:productos:detail:{id}
# TTL: 300 segundos
```

### Catálogos (`/api/v1/catalogos`)

```python
# GET /api/v1/catalogos/categorias
# Key: cache:tenant:{tenant_id}:catalogos:categorias
# TTL: 3600 segundos

# GET /api/v1/catalogos/unidades
# Key: cache:tenant:{tenant_id}:catalogos:unidades
# TTL: 3600 segundos

# GET /api/v1/catalogos/tipos-documento
# Key: cache:tenant:{tenant_id}:catalogos:tipos_documento
# TTL: 3600 segundos
```

### Configuración de Empresa (`/api/v1/empresas`)

```python
# GET /api/v1/empresas/{id}/configuracion
# Key: cache:tenant:{tenant_id}:empresa:config
# TTL: 600 segundos

# GET /api/v1/empresas/{id}/sucursales
# Key: cache:tenant:{tenant_id}:empresa:sucursales
# TTL: 600 segundos
```

## Estrategia de Invalidación

### Por Patrón (Recomendado)

Cuando se modifica un recurso, invalidar todos los caches relacionados:

```python
# Al crear/actualizar/eliminar un producto
await cache.invalidate_pattern(f"cache:tenant:{tenant_id}:productos:*")

# Al modificar configuración de empresa
await cache.invalidate_pattern(f"cache:tenant:{tenant_id}:empresa:*")
```

### Por Clave Específica

Para invalidación precisa:

```python
# Invalidar producto específico
await cache.delete(f"cache:tenant:{tenant_id}:productos:detail:{producto_id}")
```

### Eventos de Invalidación

| Evento | Claves a Invalidar |
|--------|-------------------|
| `producto.created` | `productos:list:*` |
| `producto.updated` | `productos:list:*`, `productos:detail:{id}` |
| `producto.deleted` | `productos:list:*`, `productos:detail:{id}` |
| `empresa.config_updated` | `empresa:config`, `empresa:*` |
| `catalogo.updated` | `catalogos:{tipo}` |

## Estructura de Claves

Formato: `cache:tenant:{tenant_id}:{dominio}:{subtipo}:{identificador}`

```
cache:tenant:550e8400-e29b-41d4-a716-446655440000:productos:list:abc123
cache:tenant:550e8400-e29b-41d4-a716-446655440000:productos:detail:42
cache:tenant:550e8400-e29b-41d4-a716-446655440000:catalogos:categorias
cache:tenant:550e8400-e29b-41d4-a716-446655440000:empresa:config
```

## Uso del Decorador @cached

```python
from app.core.cache import cached, CacheTTL

@router.get("/products")
@cached(ttl=CacheTTL.PRODUCTOS, key_builder=lambda tenant_id, **kwargs: f"productos:list:{hash(frozenset(kwargs.items()))}")
async def listar_productos(
    tenant_id: UUID = Depends(get_current_tenant),
    skip: int = 0,
    limit: int = 100,
):
    return await producto_service.listar(tenant_id, skip, limit)
```

## Consideraciones Multi-Tenant

- **SIEMPRE** incluir `tenant_id` en la clave de cache
- Nunca compartir cache entre tenants
- Usar prefijo `cache:tenant:{tenant_id}:` para todas las claves
- Al eliminar un tenant, limpiar `cache:tenant:{tenant_id}:*`

## Monitoreo

### Métricas Importantes

- `cache_hit_rate`: Tasa de aciertos (objetivo: >80%)
- `cache_miss_rate`: Tasa de fallos
- `cache_latency_ms`: Latencia de operaciones
- `cache_memory_usage`: Uso de memoria Redis

### Logs

```python
# Habilitar logs de cache en desarrollo
LOG_LEVEL=DEBUG
```

## Fallback sin Redis

Si Redis no está disponible, el sistema funciona sin cache:

```python
# En settings.py
REDIS_URL: str | None = None  # Opcional

# El decorador @cached opera en modo pass-through si no hay Redis
```

## Migración y Versionado

Para cambios en estructura de datos cacheados:

1. Incrementar versión en prefijo de clave
2. Claves antiguas expirarán naturalmente

```python
CACHE_VERSION = "v1"
key = f"cache:{CACHE_VERSION}:tenant:{tenant_id}:..."
```
