# Migración 200: Limpieza Legacy - UUID Puro

**Fecha**: 2025-10-28
**Prioridad**: Alta
**Estado**: Limpieza arquitectural

## Objetivo

Eliminar toda referencia a `tenant_id INTEGER` y dejar el sistema 100% UUID.

## Problema Identificado

- Tabla `tenants` tenía columna redundante `tenant_id INTEGER` (legacy)
- Código de conversión int→UUID en `middleware/tenant.py` innecesario
- Confusión entre `id UUID` (real) y `tenant_id INTEGER` (legacy)

## Solución

### Base de Datos
1. ✅ Elimina columna `tenant_id INTEGER` de tabla `tenants`
2. ✅ Drop índice `uq_tenants_tenant_id`
3. ✅ Verifica que auth_user NO tenga tenant_id (tabla global)
4. ✅ Verifica que modulos_modulo NO tenga tenant_id (catálogo global)
5. ✅ Valida que todas las demás tablas usen `tenant_id UUID`

### Código (siguiente paso)
1. 🔄 Eliminar función `_resolve_tenant_uuid()` de middleware/tenant.py
2. 🔄 Simplificar `get_current_user()` para solo UUID
3. 🔄 Actualizar generación de tokens JWT para solo UUID

## Estado Antes de Migración

```
tenants:
  ├─ id UUID (PK)              ← SE USA
  └─ tenant_id INTEGER         ← LEGACY (eliminar)

44 tablas multi-tenant:
  └─ tenant_id UUID → tenants.id  ✅

3 tablas globales (sin tenant_id):
  ├─ auth_user                 ✅
  ├─ modulos_modulo            ✅
  └─ core_tipoempresa          ✅
```

## Estado Después de Migración

```
tenants:
  └─ id UUID (PK)              ← ÚNICO IDENTIFICADOR

44 tablas multi-tenant:
  └─ tenant_id UUID → tenants.id  ✅

3 tablas globales (sin tenant_id):
  ├─ auth_user                 ✅
  ├─ modulos_modulo            ✅
  └─ core_tipoempresa          ✅
```

## Impacto

**Base de datos**: ✅ Seguro
- Solo elimina columna no usada
- Todas las FKs apuntan a `tenants.id` (UUID)
- NO afecta datos existentes

**Código**: 🔄 Requiere actualización
- Eliminar conversiones int→UUID
- Simplificar autenticación
- Tokens JWT solo UUID

## Testing

```bash
# 1. Verificar estado antes
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d+ tenants"

# 2. Aplicar migración
python scripts/py/bootstrap_imports.py --dir ops/migrations

# 3. Verificar estado después
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d+ tenants"

# 4. Verificar FKs
docker exec db psql -U postgres -d gestiqclouddb_dev -c "
SELECT conname, conrelid::regclass
FROM pg_constraint
WHERE confrelid = 'tenants'::regclass AND contype = 'f';"
```

## Rollback

⚠️ **NO RECOMENDADO** - El rollback restaura la columna vacía.
Si necesitas rollback, usa backup de BD.

```bash
# Solo si absolutamente necesario
psql -f ops/migrations/2025-10-28_200_cleanup_tenant_legacy/down.sql
```

## Siguiente Paso: Limpieza de Código

Ver: `CLEANUP_CODE_PLAN.md` (a crear)

- [ ] Simplificar `middleware/tenant.py`
- [ ] Actualizar generación de JWT
- [ ] Eliminar referencias a tenant_id (int) en código
- [ ] Tests de integración
