# Contrato de autenticación (auth única)

> Estado: **vigente desde 2026-06-09**. Verificado contra código.
> Este documento es la fuente de verdad de cómo se autentica y autoriza en el backend.

## Principio

**Hay una sola puerta de validación de token: `with_access_claims`.**
Ningún módulo decodifica o valida el JWT por su cuenta. Todo lo que necesite la
identidad del usuario parte de los claims que devuelve esa función.

## Capas

| Capa | Símbolo | Fichero | Qué hace |
|---|---|---|---|
| Decodificación JWT | `JwtService` (vía adapter `PyJWTTokenService`) | `modules/identity/infrastructure/jwt_service.py` | Único servicio que firma/verifica (HS256, `JWT_SECRET_KEY`/`SECRET_KEY`). |
| **Validación / identidad** | `with_access_claims(request)` | `core/access_guard.py` | **Única puerta.** Extrae token (Bearer → cookie `access_token` → sesión), valida vía `JwtService`, setea `request.state.access_claims`, devuelve el dict de claims. |
| Autorización | `require_scope`, `require_permission`, `require_roles` | `core/authz.py` | Guards declarativos. Consumen `with_access_claims`. |
| Tenant + GUC | `ensure_tenant` | `core/auth_dependencies.py` | Valida tenant_id (UUID) y setea `app.tenant_id` (RLS). |

## Wrappers permitidos (adaptadores finos, NO re-decodifican)

Devuelven formatos distintos para comodidad de ciertos routers, pero **siempre
construyen su resultado a partir de `with_access_claims`**:

- `core/auth_dependencies.py` → `get_current_user` devuelve `dict {id, user_id, tenant_id, roles}`.
- `modules/identity/interface/http/protected.py` → `get_current_user` devuelve `AuthenticatedUser` (Pydantic). Usado por `roles.py`, `home.py`, `users/permissions.py`.
- `middleware/tenant.py` es un **shim** que re-exporta de `auth_dependencies` (era una copia byte-a-byte; ya no tiene lógica propia).

## Shape de claims

```python
{
    "user_id": "<uuid>",      # también puede venir en "sub"
    "tenant_id": "<uuid|None>",
    "kind": "admin" | "tenant",
    "scope"/"scopes": ...,
    "is_superadmin": bool,
    "is_company_admin": bool,
    "permisos"/"permissions": { ... },
    "roles": [ ... ],
    "empresa_slug", "plantilla", "nombre": ...,
}
```

## Reglas

1. **Prohibido** definir nuevas funciones que decodifiquen el token (`jwt.decode`, `JwtService().decode`, `oauth2_scheme`) fuera de `access_guard`/`JwtService`.
2. **Prohibido** un `get_current_user` nuevo que no sea wrapper de `with_access_claims`.
3. Para endpoints de plataforma usar `require_scope("admin")` (un company-admin `kind="tenant"` no debe pasar). Para tenant, `require_scope("tenant")`.
4. `tenant_id` siempre del token/contexto, nunca del payload/query/path (ver futuro `tenant-context-contract.md`, punto 2 del plan).

## Cambios aplicados el 2026-06-09 (unificación)

- `middleware/tenant.py`: era copia byte-a-byte de `auth_dependencies.py` → convertido en shim re-exportador.
- `modules/identity/.../protected.py`: `get_current_user` ya no usa `OAuth2PasswordBearer` ni decodifica aparte; usa `with_access_claims` y mapea a `AuthenticatedUser`. Eliminados `decode_token` y `oauth2_scheme` (sin usos).
- `core/security_cookies.py`: **eliminado** (sin usos; además tenía un bug — llamaba `decode_access_token`, método inexistente en `PyJWTTokenService`). Su único caller (`sector_config.py`) migrado a `with_access_claims`.
- `core/security.get_current_active_tenant_user`: **eliminado** (era un stub placeholder que NO validaba token). Su caller real `api/v1/einvoicing.py` (envío de facturas electrónicas) estaba en producción sin auth real → migrado a `with_access_claims` + `require_scope("tenant")`.

## Pendiente

- Auditoría completa de que los ~77 endpoints usan `with_access_claims`/`require_scope` (de-facto ya es así).
- Tests de login real (claims tenant vs admin) cuando haya fixtures de BD en CI.
