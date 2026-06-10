# Contrato de tenant context (tenant único)

> Estado: **vigente desde 2026-06-09**. Verificado contra código.
> Complementa `auth-contract.md` (auth única).

## Principio

**Hay una sola función para resolver a qué tenant pertenece una request:
`get_tenant_context(request) -> TenantContext`** (`app/core/tenant_context.py`).
Parte de los claims de `with_access_claims` (la única puerta de validación de
token). Las funciones que antes extraían `tenant_id` por su cuenta delegan aquí.

## TenantContext

```python
class TenantContext(BaseModel):
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    scope: Literal["tenant", "admin", "public"] = "public"
    is_superadmin: bool = False
    request_id: str | None = None
```

- `scope == "admin"` si el token es `kind="admin"`; `"tenant"` si hay `tenant_id`; `"public"` si no hay identidad.
- `get_tenant_context` **no lanza excepción**: si no hay identidad devuelve `scope="public"`. Los dependencies que exijan tenant validan `ctx.tenant_id is not None`.
- La puerta limpia **nunca inventa tenant** (no tiene fallback de "primer tenant de la BD").

## Funciones lectoras (ahora wrappers de la puerta)

| Función | Fichero | Devuelve | Notas |
|---|---|---|---|
| `get_tenant_uuid` | `core/dependencies.py` | `UUID` | 401 si falta. Sin fallback session. |
| `get_tenant_id_from_token` | `core/dependencies.py` | `UUID` | Valida token (`with_access_claims`) + tenant. |
| `get_current_tenant_id` | `core/dependencies.py` | `UUID` | Conserva **fallback dev** (primer tenant de BD) solo si `ENVIRONMENT!=production`. |
| `tenant_id_from_request` | `db/rls.py` | `str \| None` | Usado por `ensure_rls`. |

## Reglas

1. Nuevo código que necesite el tenant usa `get_tenant_context(request)` (o `get_tenant_uuid` si solo quiere el UUID y exige presencia).
2. **`tenant_id` siempre del token/contexto, nunca del payload/query/path.** Excepciones permitidas: endpoints públicos por slug, webhooks externos con firma, y endpoints **admin** de plataforma que gestionan un tenant concreto por path (p.ej. `company/.../{tenant_id}`), que ya van con `require_scope("admin")`.
3. La fuente `request.state.session` (admin UI legacy) es **fallback** dentro de `get_tenant_context`; no usarla directamente en módulos nuevos.

## Cambios aplicados el 2026-06-09

- Creado `core/tenant_context.py` (`TenantContext` + `get_tenant_context`).
- `core/dependencies.py`: `get_tenant_uuid`, `get_tenant_id_from_token`, `get_current_tenant_id` delegan en la puerta. El *fallback dev* dejó de estar disperso; vive solo en `get_current_tenant_id`, fuera de la puerta limpia.
- `db/rls.py`: `tenant_id_from_request` delega en la puerta (con ello `ensure_rls` también).
- Tests: `app/tests/security/test_tenant_context.py` (verdes).

## Pendiente

- Auditar endpoints que aún acepten `tenant_id` desde payload/body (regla 2) y cerrarlos.
- Reconciliar `ensure_tenant` / `ensure_rls` (que setean el GUC) con la sesión DB única — **punto 3** del plan.
- Migración progresiva de los `claims.get("tenant_id")` directos hacia `get_tenant_context` donde aporte (no urgente: leer del claims canónico es válido).
