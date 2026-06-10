# Inventario de rutas (router moderno vs legacy)

> Generado el 2026-06-10 a partir de `app.main:app.routes` (830 rutas).
> Punto 8 del plan de base técnica.

## Resumen

- **830** rutas HTTP montadas.
- **0** colisiones reales (ningún `método+path` exacto montado dos veces → el routing es determinista, no hay ambigüedad).
- **44** endpoints expuestos con la **misma función bajo dos prefijos**: `/api/v1/<x>` **y** `/api/v1/tenant/<x>`.

## Fuente de verdad

`app/platform/http/router.py` → `build_api_router()`, montado en `app/main.py` con prefix `/api/v1`. Es la fuente de verdad: los módulos tenant quedan bajo `/api/v1/tenant/...`.

**El frontend usa el prefijo `/api/v1/tenant/...`** (verificado en `apps/tenant/src`, p.ej. `useCompanySectorFullConfig.ts`, `ProductLineInput.tsx`). Los paths sin `/tenant` son **superficie legacy** que el frontend no consume.

## Superficie duplicada (legacy)

`app/main.py` montaba a mano, además de `build_api_router()`, varios routers con prefix `/api/v1` (sin `/tenant`), duplicando la superficie. Estado tras la validación contra el frontend (2026-06-10):

| Módulo | Path legacy | Path canónico | Estado |
|---|---|---|---|
| notifications | `/api/v1/notifications/*` | `/api/v1/tenant/notifications/*` | ✅ **Retirado** (frontend usa solo `/tenant`; el legacy iba sin `require_scope`) |
| reports/profit | `/api/v1/reports/profit` | `/api/v1/tenant/reports/profit` | ✅ **Retirado** (frontend usa solo `/tenant`) |
| hr | `/api/v1/hr/*` | `/api/v1/tenant/hr/*` | ⏳ **Pendiente**: el frontend usa rutas relativas (no se confirma con grep de strings). Validar antes de retirar. |
| sectors | `/api/v1/sectors` | `/api/v1/sectors` (mismo) | ❌ **No retirar**: `apps/admin` usa `/api/v1/sectors` directamente (`sectorAdminConfig.ts`). |

Retirados el 2026-06-10: **11 rutas** (830 → 819). Resto de doble superficie (dashboard, documents, products, auth…): pendiente de validar el origen exacto del montaje y el uso del frontend antes de tocar.

## Riesgo

> ⚠️ La versión bajo `/api/v1/tenant/...` lleva las dependencies de `build_api_router` (`with_access_claims` + `require_scope("tenant")` + `ensure_rls`). La versión "plana" `/api/v1/...` montada en `main.py` **puede no llevar las mismas guardas** → potencial diferencia de permisos. **Antes de retirarlas, verificar que ningún cliente las usa y que no exponen datos con menos control.**

## Plan de retirada (pendiente)

1. Por cada módulo de la tabla, confirmar (frontend + logs de acceso) que solo se usa el path `/api/v1/tenant/...`.
2. Eliminar el `include_router(...)` correspondiente en `app/main.py`.
3. Re-generar este inventario y confirmar que el recuento de rutas baja sin pérdida de funcionalidad usada.
4. Estado objetivo de `main.py`: middlewares + health + docs + `include_router(build_api_router(), prefix="/api/v1")`, sin montajes sueltos salvo excepciones documentadas.

## Cómo regenerar

```bash
python -c "import app.main as m; [print(sorted(meth+' '+r.path for r in m.app.routes for meth in (getattr(r,'methods',None) or []) ))]"
```
