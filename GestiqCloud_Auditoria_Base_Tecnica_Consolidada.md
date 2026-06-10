# GestiqCloud — Auditoría consolidada y plan para dejar una base técnica sólida

Fecha: 2026-06-09  
Repositorio: `frankCashabamba/gestiqcloud`  
Commit observado en revisiones GitHub: `556018a1373f2b74ca828d44d17ff4617166f687`  
Alcance: backend, documentación general, despliegue, seguridad, multitenancy, workers, módulos críticos y plan de unificación.

---

## 0. Nota de honestidad

Este documento consolida:

1. Auditorías previas subidas por Frank.
2. Revisión directa de documentación del repositorio.
3. Revisión directa de ficheros críticos de backend.
4. Aclaración funcional de Frank: **VPS para backend + scripts SQL + IA local/OCR/Redis/Celery; Render para frontends; Cloudflare Worker como edge gateway**.

No se marca como “cerrado” nada que no esté validado por código o por decisión explícita. Donde falta comprobar ejecución real en producción, se indica como pendiente.

---

## 0.0 🔴 HALLAZGO CRÍTICO (2026-06-10) — RLS bypassed: la app se conecta como SUPERUSER

Al probar el aislamiento multi-tenant contra Postgres real se descubrió que **RLS no protege nada con la configuración actual**: la app se conecta como `postgres` (**superuser**), y Postgres ignora RLS para superusers **incluso con `FORCE ROW LEVEL SECURITY`**. El GUC `app.tenant_id` se setea correctamente y las políticas (`tenant_isolation_policy`, `admin_bypass`) existen, pero el superuser las salta todas.

**Evidencia (Postgres dev, 2026-06-10):**
- `tenant_session_scope(A)` veía **4356** productos (todos los tenants), incl. 553 del tenant B → **fuga cross-tenant total**.
- Con un rol **no-superuser** de prueba: `app.tenant_id=A` veía **exactamente 554** (solo A), **0 de B** → RLS aísla perfectamente.
- 100 tablas con RLS; **15 sin `FORCE`** (riesgo adicional para el owner).

**Implicación:** hoy el aislamiento multi-tenant depende **solo de los filtros `WHERE tenant_id` manuales** en el código, no de RLS. Los puntos 3/4/9 (sesión, bypass, workers) asumían RLS efectiva; **no lo es mientras la app use un superuser**.

**Acción (no aplicada aquí — requiere infra/DBA):**
1. Crear un rol de aplicación **NO-superuser** con los grants mínimos (`SELECT/INSERT/UPDATE/DELETE` en tablas de negocio, `USAGE` en el esquema).
2. Apuntar `DATABASE_URL` (backend + workers) a ese rol en **todos** los entornos.
3. Añadir `FORCE ROW LEVEL SECURITY` a las 15 tablas que faltan.
4. Mantener el bypass de sistema vía `app.bypass_rls` (`system_session`/`bot_session_scope`) — la política `admin_bypass` ya lo contempla.

Test invariante añadido: `test_app_db_connection_is_not_superuser` (pg_only) — falla si la conexión es superuser.

---

## 0.1 Estado de ejecución — primera tanda (2026-06-09)

Todos los hallazgos de este documento se verificaron contra código (16 de 17 confirmados; las imprecisiones eran nombres de ficheros que ya no existen, anotadas en cada sección). Primera tanda de bajo esfuerzo / alto valor **aplicada**:

| ID | Estado | Fichero(s) |
|---|---|---|
| C-03 importador por id sin tenant | ✅ Resuelto | `importador/tasks.py`, `importador/services/ai_analysis_agent.py` |
| C-05 CSRF no montado | ✅ Resuelto (montaje); tests pendientes | `main.py`, `middleware/require_csrf.py` |
| C-07 admin_logs sin guard superadmin | ✅ Resuelto | `routers/admin_logs.py` |
| M-02 export CSV/XLSX injection | ✅ Resuelto | `export/interface/http/tenant.py` |
| M-03 documents upload débil | ✅ Resuelto | `documents/interface/http/document_storage.py` |
| M-05 accounting seed sin permiso | ✅ Resuelto | `accounting/interface/http/tenant.py` |

### Base técnica (los 10 puntos del veredicto) — avance por punto

| # | Punto | Estado |
|---|---|---|
| 1 | Auth única | ✅ **Núcleo resuelto** (2026-06-09): una sola puerta `with_access_claims`; puertas paralelas eliminadas; contrato en `docs/security/auth-contract.md`; tests verdes. Falta: tests de login con BD. |
| 2 | Tenant context único | ✅ **Puerta resuelta** (2026-06-09): `core/tenant_context.py` (`TenantContext` + `get_tenant_context`); las ~8 funciones lectoras delegan; contrato en `docs/security/tenant-context-contract.md`; tests verdes. Falta: auditar tenant desde payload + reconciliar GUC en punto 3. |
| 3 | Session DB única (GUC/RLS) | ✅ **Resuelto** (2026-06-09): `db/session.py` es shim de `config/database.py`; nuevo `system_session()`. Tests estructurales verdes; RLS real pendiente CI-Postgres. |
| 4 | Bypass RLS inventariado y cerrado | ✅ **Resuelto** (2026-06-10): inventario en `bypass-rls-register.md`; importador filtra por tenant; C-04 Telegram migrado a `tenant_session_scope` (sin bypass) + `compare_digest`. Bypass restante (`system_session`, `bot_session_scope`) documentado y justificado. |
| 5 | CSRF | 🟡 Montado (bypass bajo pytest, flag `PYTEST_DISABLE_CSRF_BYPASS`); falta verificar en prod + tests. |
| 6 | Rate limit único | ✅ **Consolidado** (2026-06-10): `EndpointRateLimiter` con Redis+fallback (cierra evasión multi-proceso del login); decorador muerto eliminado; capas documentadas con responsabilidad clara en `docs/seguridad.md`. |
| 7 | Telemetry única + redacción PII | ✅ **Resuelto** (2026-06-10): `telemetry` es la única capa (eliminados `metrics/store.py` y `middleware/metrics.py`, código muerto). Nueva utilidad `core/redact.py` `redact_sensitive`. Tests verdes. |
| 8 | Router moderno fuente de verdad | 🟡 **Inventariado + retirada parcial** (2026-06-10): `docs/routes-inventory.md`. Retirados de `main.py` los montajes legacy de **notifications** y **profit** (11 rutas, 830→819) tras validar que el frontend usa solo `/tenant`. `hr` pendiente (frontend con rutas relativas), `sectors` no se retira (admin lo usa sin `/tenant`). |
| 9 | Workers con aislamiento probado | 🟠 Código migrado + tests cross-tenant implementados (`test_session_isolation.py`, pg_only). **PERO al probar contra Postgres real se halló que RLS está bypassed porque la app usa SUPERUSER (ver §0.0).** Aislamiento real bloqueado hasta usar rol no-superuser. RLS con rol correcto: probado OK (554 vs 0 fugas). |
| 10 | Documentación deploy real | ✅ **Resuelto** (2026-06-10): `docs/deploy.md` y `docs/entornos.md` alineados a VPS (backend+SQL+Redis+Celery+IA en VPS; Render solo frontends; Cloudflare edge). Corregido `app.current_tenant`→`app.tenant_id`. |

Ver registro de bypass RLS en `docs/security/bypass-rls-register.md` y contrato de auth en `docs/security/auth-contract.md`.

---

## 1. Veredicto ejecutivo realista

GestiqCloud **no está mal como base de producto**, pero ahora mismo tiene una deuda técnica peligrosa en el núcleo:

- Hay más de un sistema de autenticación.
- Hay más de una fuente de tenant.
- Hay más de una forma de abrir sesiones DB.
- Hay bypass RLS en varios flujos.
- Hay routers modernos y legacy conviviendo.
- Hay workers y módulos que pueden saltarse el patrón principal.
- La documentación mezcla estado real, histórico y objetivo.

La prioridad no debe ser seguir ampliando módulos. La prioridad es **cerrar la base técnica**.

La base técnica mínima antes de seguir creciendo debería ser:

1. Auth única.
2. Tenant context único.
3. Session DB única con GUC/RLS garantizado.
4. Bypass RLS inventariado, cerrado y justificado.
5. CSRF confirmado en app real.
6. Rate limit único.
7. Metrics/telemetry única con redacción de PII.
8. Router moderno como fuente de verdad, legacy aislado o eliminado.
9. Workers con aislamiento multi-tenant probado.
10. Documentación alineada con el despliegue real VPS + Render + Cloudflare.

---

## 2. Arquitectura real decidida

### 2.1 Estado real actual recomendado

```text
Usuarios
  ↓
Cloudflare Worker
  - /api/*
  - CORS
  - cookies
  - request-id
  - headers seguridad
  ↓
VPS
  - Backend FastAPI
  - scripts SQL/migraciones
  - Redis
  - Celery workers
  - IA local/OCR
  - logs runtime
  ↓
PostgreSQL

Render
  - Admin React static
  - Tenant React static
```

### 2.2 Qué significa esto para la documentación

La documentación debe dejar de decir cosas ambiguas como:

- “Backend en Render” si realmente el backend operativo está en VPS.
- “Render + Cloudflare” como si Render fuera todo.
- “VPS” sólo en una parte del README sin explicar qué vive allí.

Debe quedar así:

```md
## Deploy real

- Backend API: VPS.
- Scripts SQL/migraciones: VPS.
- Redis/Celery workers: VPS.
- IA local/OCR: VPS.
- Admin/Tenant React: Render static.
- Edge gateway: Cloudflare Worker.
- `render.yaml`: referencia activa para frontends y configuración histórica/alternativa para backend, no fuente principal del backend productivo si el backend real está en VPS.
```

### 2.3 Problema actual

Hay contradicción documental entre:

- README: menciona Render, pero también una tabla donde backend/Redis/Celery/IA están en VPS.
- `docs/deploy.md`: habla de backend en Render.
- `docs/entornos.md`: dice API Render `gestiqcloud-api`.
- `render.yaml`: define backend API en Render.
- Decisión real de Frank: VPS para backend + scripts SQL + IA local.

Esto no es sólo “documentación fea”. En producción, una documentación ambigua provoca:

- migraciones ejecutadas en el sitio equivocado;
- variables configuradas en Render pero no en VPS;
- workers duplicados;
- debugging lento;
- riesgo de tocar producción sin saber qué servicio está vivo.

---

## 3. Prioridad 0 — Unificación técnica obligatoria

Esta es la parte que debe ir al principio de cualquier plan técnico. No es opcional.

### 3.1 Auth única

#### Situación detectada

Las auditorías previas detectan duplicidad entre:

```text
core/access_guard.py
core/auth.py
core/auth_http.py
core/auth_middleware.py
core/refresh.py
modules/identity/*
```

> **Corrección (2026-06-09, verificado contra código):** `core/auth.py` y `core/auth_middleware.py` **ya no existen**. Los ficheros reales presentes son `core/access_guard.py`, `core/auth_http.py`, `core/refresh.py`, `core/authz.py`, más `core/auth_shared.py`, `core/auth_cookies.py` y `core/auth_dependencies.py`. La dispersión es menor que la descrita, pero `get_current_user` (en `auth_dependencies.py` / `middleware/tenant.py`) sigue conviviendo con el patrón `identity`. El plan de unificación sigue siendo válido; corregir la lista de ficheros antes de ejecutarlo.

Riesgo:

- Un endpoint puede validar claims con un sistema y otro endpoint con otro.
- Permisos inconsistentes.
- Refresh/logout pueden comportarse distinto según ruta.
- Admin y tenant pueden acabar compartiendo lógica accidentalmente.
- Difícil saber qué flujo es el canónico.

#### Decisión recomendada

Declarar como única fuente de verdad:

```text
modules/identity/*
core/access_guard.py
core/authz.py
```

Y todo lo demás:

```text
core/auth.py
core/auth_http.py
core/auth_middleware.py
core/refresh.py
```

debe quedar en uno de estos estados:

- eliminado;
- wrapper fino hacia identity;
- marcado legacy con fecha de retirada;
- no importable desde nuevos módulos.

#### Regla técnica

Todo endpoint debe usar uno de estos patrones:

```python
Depends(with_access_claims)
Depends(require_scope("tenant" | "admin"))
Depends(require_permission("..."))  # cuando aplique
```

No debería existir otro `get_current_user` paralelo salvo que sea wrapper explícito y testeado.

#### Tests obligatorios

- Login tenant genera claims esperados.
- Login admin genera claims esperados.
- Endpoint tenant rechaza token admin salvo permiso explícito.
- Endpoint admin rechaza token tenant.
- Refresh reutilizado revoca familia.
- Logout borra cookies y revoca refresh.
- Endpoint nuevo falla si no pasa por `with_access_claims`.

#### ESTADO (2026-06-09) — RESUELTO (núcleo); tests de login pendientes

Contrato unificado y documentado en `docs/security/auth-contract.md`. **Una sola puerta de validación de token: `with_access_claims`** (que decodifica vía el único `JwtService`). Cambios:

- `middleware/tenant.py`: era **copia byte-a-byte** de `core/auth_dependencies.py` → ahora shim re-exportador (sin lógica propia).
- `modules/identity/.../protected.py`: `get_current_user` ya no usa `OAuth2PasswordBearer` ni decodifica aparte; usa `with_access_claims` y mapea a `AuthenticatedUser`. Eliminados `decode_token` y `oauth2_scheme`.
- `core/security_cookies.py`: **eliminado** (sin usos; tenía además un bug: llamaba `decode_access_token`, inexistente). Su caller `sector_config.py` migrado a `with_access_claims`.
- **Hallazgo nuevo (no estaba en la auditoría):** `core/security.get_current_active_tenant_user` era un **stub placeholder que NO validaba token**, y `api/v1/einvoicing.py` (envío de facturas electrónicas) lo usaba en producción → endpoints sin auth real. Eliminado el stub y migrado einvoicing a `with_access_claims` + `require_scope("tenant")`.

Tests: `app/tests/security/test_auth_contract.py` (10, verdes) — mapeo de claims, `require_scope`/`require_permission`, wrapper dict, shim de `middleware/tenant`, y anti-regresión de los símbolos eliminados. Pendiente: tests de login real (claims tenant vs admin) con fixtures de BD.

> Nota: el patrón canónico `with_access_claims`+`require_scope` ya era dominante (77 endpoints); esta tanda eliminó las puertas paralelas de decodificación, no reescribió los 77.

---

### 3.2 Tenant context único

#### Situación detectada

Hay múltiples fuentes de tenant:

```text
request.state.access_claims
request.state.session
tenant_context.py
db/rls.py
config/database.py
middleware/tenant.py
middleware/tenant_middleware.py
```

> **Corrección (2026-06-09, verificado contra código):** `core/tenant_context.py` **no existe**; el resto sí (`db/rls.py`, `config/database.py`, `middleware/tenant.py`, `middleware/tenant_middleware.py`). **No** existe aún una función `get_tenant_context` ni un modelo `TenantContext` único, y hay ~37 accesos directos a `tenant_id` desde claims/session repartidos por el código. El problema descrito es real; este punto **sigue pendiente** (no abordado en la tanda del 2026-06-09).

Riesgo:

- Un endpoint puede usar `tenant_id` de claims.
- Otro endpoint puede usar session.
- Otro puede aceptar tenant desde payload o URL.
- Workers pueden usar tenant manual.
- RLS puede recibir un tenant diferente al usado por el endpoint.

#### Decisión recomendada

Crear una única función oficial:

```python
get_tenant_context(request) -> TenantContext
```

con salida tipada:

```python
class TenantContext(BaseModel):
    tenant_id: UUID | None
    user_id: UUID | None
    scope: Literal["tenant", "admin", "public"]
    is_superadmin: bool
    request_id: str | None
```

Y prohibir acceso directo a:

```python
request.state.access_claims["tenant_id"]
request.state.session["tenant_id"]
```

fuera de esa función.

#### Regla técnica

Para endpoints tenant:

```text
tenant_id siempre viene del token/contexto.
Nunca viene de payload.
Nunca viene de query param.
Nunca viene sólo de path.
```

Excepción permitida:

- endpoints públicos por slug o configuración pública;
- webhooks externos con firma fuerte;
- admin superuser con permiso explícito.

#### Tests obligatorios

- Payload con `tenant_id` distinto se ignora o rechaza.
- Tenant A no puede leer/editar recurso de Tenant B.
- Workers no procesan recurso si `doc_id` no pertenece al tenant del job.
- Cualquier endpoint tenant sin contexto falla.

#### ESTADO (2026-06-09) — RESUELTO (puerta única); migración de callsites progresiva

Verificado: había **~8 funciones** distintas para obtener el tenant (`get_tenant_uuid`, `get_tenant_id_from_token`, `get_current_tenant_id` ×2, `ensure_tenant`, `tenant_id_from_request`, `ensure_rls` ×2) con retornos inconsistentes (UUID/str/None), más 169 `claims.get("tenant_id")` directos.

Creado `core/tenant_context.py` con `TenantContext` (Pydantic) y **`get_tenant_context(request)` como única puerta de resolución** (deriva de `with_access_claims`; ver `docs/security/tenant-context-contract.md`). Las funciones lectoras (`get_tenant_uuid`, `get_tenant_id_from_token`, `get_current_tenant_id`, `tenant_id_from_request`) ahora **delegan** en ella — firmas y retornos intactos, ~470 callsites sin tocar.

Seguridad: el *fallback dev* (primer tenant de la BD) se sacó de la capa limpia y queda confinado a `get_current_tenant_id` con guard `ENVIRONMENT!=production`. La fuente `session` queda como fallback documentado, no para módulos nuevos.

Tests: `app/tests/security/test_tenant_context.py` (verdes). Smoke de login/empresa sin regresiones.

Pendiente: auditar endpoints que acepten `tenant_id` desde payload/body; reconciliar `ensure_tenant`/`ensure_rls` (GUC) en el **punto 3**.

---

### 3.3 Session DB única con RLS/GUC garantizado

#### Situación detectada

`app/config/database.py` tiene la sesión principal con GUCs:

```text
app.tenant_id
app.user_id
app.bypass_rls
```

y los aplica en `after_begin`. Esto es una buena dirección.

Pero `app/db/session.py` define otro engine, otro `SessionLocal`, otro `get_db` y otro `get_db_context` sin ese contexto. Eso es peligroso porque workers pueden entrar por ahí.

#### Riesgo real

Si una tarea usa:

```python
from app.db.session import get_db_context
```

puede ejecutar SQL sin el mismo RLS/GUC que la sesión principal.

Ejemplo confirmado en worker IA:

```python
from app.db.session import get_db_context
```

y luego recorre tenants y ejecuta SQL manual con `tenant_id = :tid`.

Aunque las queries estén parametrizadas, el riesgo no desaparece. La seguridad depende de filtros manuales, no de una barrera central.

#### Decisión recomendada

Eliminar `app/db/session.py` como sesión alternativa o convertirlo en wrapper de `app/config/database.py`.

Estado objetivo:

```python
# app/db/session.py
from app.config.database import SessionLocal, get_db, session_scope, tenant_session_scope
```

Nada de engine propio.

#### Helper recomendado para workers

Crear algo así:

```python
@contextmanager
def tenant_worker_session(tenant_id: UUID, user_id: UUID | None = None, *, bypass_rls: bool = False):
    db = SessionLocal()
    db.info["tenant_id"] = str(tenant_id)
    db.info["user_id"] = str(user_id) if user_id else None
    db.info["bypass_rls"] = bool(bypass_rls)
    db.execute(text("SELECT 1"))
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

Y para jobs globales multi-tenant:

```python
with system_session() as db:
    tenant_ids = ...
for tenant_id in tenant_ids:
    with tenant_worker_session(tenant_id) as db:
        ...
```

No mezclar “listar tenants globalmente” con “procesar datos del tenant” en la misma sesión sin contexto.

#### Tests obligatorios

- Test que falle si alguien importa `app.db.session.SessionLocal`.
- Test worker tenant A con `doc_id` de tenant B.
- Test `current_setting('app.tenant_id')` dentro de sesión worker.
- Test rollback mantiene GUC tras nueva transacción.
- Test superadmin bypass sólo cuando se declara explícitamente.

#### ESTADO (2026-06-09) — RESUELTO (C-01 y C-02); tests RLS reales pendientes de CI-Postgres

- `app/db/session.py`: dejó de crear engine/`SessionLocal` propios → es **shim** de `app/config/database.py` (única fábrica con `after_begin`/GUCs). `get_db_context` ahora es `session_scope`.
- **C-02 workers migrados** a context managers canónicos:
  - `workers/ai_tasks.py` (`daily_executive_summary`) y `workers/expiry_tasks.py`: listan tenants con `session_scope()` (la tabla `tenants` no tiene RLS) y procesan **cada tenant** con `tenant_session_scope(tid)` (GUC `app.tenant_id`, RLS activa).
  - `workers/notifications.py`: `send_notification_task` (recibe tenant) → `tenant_session_scope`; `check_and_notify_low_stock` (barrido cross-tenant) → nuevo `system_session()` con `bypass_rls`, delegando el envío real a `send_notification_task` (que corre por tenant).
- Nuevo helper `system_session()` en `config/database.py`: activa `bypass_rls` vía `db.info` (reaplicado por `after_begin` tras cada commit). Inventariado en `docs/security/bypass-rls-register.md`.
- Tests: `app/tests/security/test_session_isolation.py` — estructurales verdes (shim, sin engine propio, workers usan scopes canónicos, ningún worker importa el shim legacy); los de comportamiento RLS (bypass activo, `app.tenant_id`, aislamiento cross-tenant A↔B) van marcados `pg_only`/skip y quedan **pendientes de CI con Postgres** (SQLite no soporta SET LOCAL/current_setting).

Pendiente: reconciliar `ensure_tenant`/`ensure_rls` (punto 2) con esta fábrica única; tests cross-tenant reales en CI-Postgres.

---

### 3.4 Bypass RLS inventariado

#### Situación detectada

Hay uso confirmado de:

```python
db.info["bypass_rls"] = True
```

en flujos como:

- Telegram bot webhook.
- Importador/Celery.
- Configuración especial.

#### Riesgo

`bypass_rls=True` puede ser necesario en tareas internas, pero sin inventario y tests es una puerta peligrosa.

#### Decisión recomendada

Crear un registro explícito:

```md
docs/security/bypass-rls-register.md
```

Con tabla:

| Código | Fichero | Motivo | Alcance | Tiene test | Fecha revisión |
|---|---|---|---|---|---|

Regla:

```text
Ningún bypass RLS puede existir sin:
- motivo documentado;
- permiso/condición clara;
- test cross-tenant;
- owner técnico;
- fecha de revisión.
```

---

### 3.5 CSRF confirmado en app real

#### Situación detectada

Las auditorías previas indican que CSRF parece definido pero posiblemente no montado.

#### Decisión recomendada

Confirmar en código real:

- dónde se genera token;
- dónde se valida;
- qué rutas están exentas;
- cómo interactúa con Cloudflare Worker;
- cómo se comportan cookies SameSite.

#### Tests obligatorios

- POST tenant sin CSRF falla.
- POST tenant con CSRF válido pasa.
- Login/refresh/logout se comportan según diseño.
- Worker no elimina headers CSRF.
- Frontend envía header correcto.

---

### 3.6 Rate limiting único

#### Situación detectada

Existen varias capas:

```text
middleware/rate_limit.py
middleware/endpoint_rate_limit.py
decorators rate_limit
identity SimpleRateLimiter
```

#### Riesgo

- Un login puede tener límite en una ruta y no en otra.
- IP se calcula distinto.
- Reglas duplicadas y difíciles de ajustar.
- Falsos positivos o huecos.

#### Decisión recomendada

Una capa oficial:

```text
EndpointRateLimiter + storage Redis
```

o una capa global + overrides declarativos.

Ejemplo:

```python
RATE_LIMIT_RULES = {
    "tenant.login": "10/min/ip",
    "admin.login": "10/min/ip",
    "password.reset": "5/5min/ip",
    "webhook.public": "60/min/signature_or_ip",
}
```

Eliminar decoradores antiguos salvo wrapper hacia la capa única.

#### ESTADO (2026-06-10) — RESUELTO (consolidación + storage Redis)

Las capas tienen propósitos distintos y se mantienen separadas pero con responsabilidad clara y storage unificado en Redis:

- **`EndpointRateLimiter`** (capa oficial por endpoint crítico): reescrito para usar **Redis** (fixed-window) con **fallback a memoria** local. Antes usaba solo memoria → con varios procesos el límite de login/password-reset era **evadible**; ahora es consistente entre procesos.
- **`RateLimitMiddleware`** (global por user/tenant/IP, ya Redis): se mantiene como límite global de tráfico.
- **`SimpleRateLimiter` / `core/login_rate_limit`** (Redis): lockout anti-fuerza-bruta por **fallos** de login. Propósito distinto (cuenta fallos, no requests) → se mantiene.
- **Eliminado** el decorador muerto `rate_limit()` (`middleware/endpoint_rate_limit.py`), que era una tercera vía en memoria sin uso real.

Tests: `app/tests/security/test_rate_limit.py`. Documentado en `docs/seguridad.md`.

---

### 3.7 Metrics/telemetry única

#### Situación detectada

Duplicidad entre:

```text
app.metrics.store
app.telemetry.metrics
```

y logs con tenant/user/entity/error metadata.

#### Riesgo

- Doble contabilización.
- Métricas no comparables.
- PII en logs/telemetría.
- Coste de observabilidad innecesario.
- Debugging confuso.

#### Decisión recomendada

Una capa:

```text
app.telemetry
```

y `app.metrics` debe ser wrapper o retirarse.

Añadir redacción centralizada:

```python
redact_sensitive(data)
```

que oculte:

- tokens;
- emails si no son necesarios;
- documentos OCR;
- raw_ai_json sensible;
- storage_uri;
- passwords;
- API keys;
- certificados;
- datos fiscales/personales.

---

### 3.8 Router moderno vs legacy

#### Situación detectada

`platform/http/router.py` monta muchos módulos modernos. Pero `app/main.py` también monta routers adicionales/legacy manualmente después.

Esto rompe la idea de “router principal único”.

#### Riesgo

- Mismo módulo montado dos veces.
- Rutas antiguas siguen vivas sin querer.
- Permisos diferentes entre ruta nueva y legacy.
- Difícil saber qué endpoint consume el frontend.

#### Decisión recomendada

Estado objetivo:

```text
app/main.py
  - middlewares
  - health
  - docs
  - include_router(build_api_router(), prefix="/api/v1")
```

Todo lo demás debería ir a:

```text
app/platform/http/router.py
```

o estar marcado como legacy con fecha de retirada.

#### Acción concreta

Crear un fichero:

```md
docs/routes-inventory.md
```

con:

| Ruta | Router | Estado | Front la usa | Retirar |
|---|---|---|---|---|

---

## 4. Hallazgos críticos consolidados

### C-01 — Sesión alternativa sin RLS/GUC

#### Evidencia

`app/config/database.py` define la sesión principal con GUCs y `after_begin`.

`app/db/session.py` define otro engine y otro `SessionLocal` sin esa lógica.

#### Impacto

Alto. Cualquier worker o módulo que use `app.db.session` puede saltarse el aislamiento central.

#### Acción

- Convertir `app/db/session.py` en wrapper o eliminarlo.
- Migrar imports de workers.
- Añadir test anti-import.

#### ESTADO (2026-06-09) — RESUELTO

`app/db/session.py` es ahora un shim de `app/config/database.py` (sin engine propio). Test anti-engine: `test_db_session_does_not_build_its_own_engine`. Ver §3.3.

---

### C-02 — Workers multi-tenant sin aislamiento demostrado

#### Evidencia

`workers/ai_tasks.py` usa `get_db_context` desde `app.db.session` y recorre tenants activos. Luego ejecuta SQL manual con `tenant_id = :tid`.

#### Impacto

Alto. Aunque filtra por tenant en SQL, no hay RLS/GUC central en esa sesión.

#### Acción

- Separar sesión global de listado de tenants y sesión tenant.
- Usar `tenant_worker_session`.
- Añadir tests cross-tenant.

#### ESTADO (2026-06-09) — RESUELTO (código); tests cross-tenant en CI-Postgres

`workers/ai_tasks.py`, `expiry_tasks.py` y `notifications.py` separan listado (`session_scope`) de procesamiento por tenant (`tenant_session_scope`); el barrido global de stock usa `system_session()` (bypass). El rol de `tenant_worker_session` lo cumple `tenant_session_scope` (ya existía). Ver §3.3.

---

### C-03 — Importador con bypass RLS y carga por id sin tenant

#### Evidencia previa

Auditoría de módulos detecta:

- `SessionLocal`.
- `db.info["bypass_rls"] = True`.
- carga de documento por `doc_id` sin validar `tenant_id`.

#### Impacto

Grave. Un job mal formado puede procesar documento de otro tenant.

#### Acción

Cambiar toda query crítica a:

```python
.where(ImpDocumento.id == doc_id, ImpDocumento.tenant_id == tenant_id)
```

No basta con pasar tenant al proceso; debe estar en la query.

#### ESTADO (2026-06-09) — RESUELTO

Las tres rutas con `bypass_rls=True` que cargaban documento por id ya filtran por tenant:

- `modules/importador/tasks.py` `_run_processing`: `filter(ImpDocumento.id == doc_id, ImpDocumento.tenant_id == tenant_id)`.
- `modules/importador/tasks.py` (recuperación de payload perdido): mismo filtro con `UUID(str(tenant_id))`.
- `modules/importador/services/ai_analysis_agent.py` `analyze_document_with_ai`: nuevo parámetro `tenant_id` y validación `doc.tenant_id == tenant_id` tras `db.get(...)`; los dos callers (batch y tarea Celery `analyze_document_ai`) lo pasan.

Pendiente: tests cross-tenant automatizados (un `doc_id` de tenant B con job de tenant A debe devolver "no encontrado").

---

### C-04 — Telegram bot con bypass RLS

#### Evidencia previa

Webhook de Telegram carga config por `tenant_id` de URL y abre sesión con bypass.

#### Impacto

Grave si el tenant_id de URL no está blindado con secret fuerte y validaciones.

#### Acción

- Mantener `webhook_secret` obligatorio.
- No usar bypass para leer datos de tenant.
- Usar tenant session con GUC.
- Test con tenant_id ajeno y secret inválido.

#### ESTADO (2026-06-10) — RESUELTO

`modules/telegram_bot/.../webhook.py`: eliminado `_get_bot_db` (que activaba `bypass_rls`). La carga de config y de stock usa ahora `tenant_session_scope(tenant_id)` (GUC `app.tenant_id`, RLS activa, sin bypass). El `webhook_secret` se compara con `secrets.compare_digest` (timing-safe) y sigue siendo obligatorio (403 si falta o no coincide). Tests: `app/tests/security/test_telegram_webhook.py` (secret ausente/ inválido → 403, válido → 200, y no-bypass estructural).

---

### C-05 — CSRF posiblemente no montado

#### Evidencia previa

Auditoría global lo marca como crítico pendiente.

#### Impacto

Alto si usas cookies HttpOnly para auth y endpoints mutables sin CSRF.

#### Acción

- Confirmar middleware/dependency real.
- Añadir tests de integración.
- Documentar rutas exentas.

#### ESTADO (2026-06-09) — RESUELTO (montaje); tests pendientes

La infraestructura CSRF ya existía completa y end-to-end, solo **no estaba montado** el middleware:

- `core/csrf.py` `issue_csrf_token` guarda el token en `session["csrf"]`.
- `GET /api/v1/tenant/auth/csrf` y `GET /api/v1/admin/auth/csrf` emiten cookie `csrf_token` (`httponly=False`, `samesite=lax`, `secure` en prod).
- Los clientes HTTP de `apps/tenant` y `apps/admin` ya leen la cookie y reenvían `X-CSRF-Token`/`X-CSRF`.

Cambio aplicado en `app/main.py`: se monta `RequireCSRFMiddleware` **antes** de `SessionMiddleware` (queda más interno y ve `request.state.session`), bajo flag `CSRF_ENABLED` (default on). Valida double-submit (header == cookie) o (header == sesión).

Rutas exentas (en `middleware/require_csrf.py`):
- Métodos seguros (GET/HEAD/OPTIONS).
- Sufijos `/auth/login`, `/auth/refresh`, `/auth/logout`.
- Webhooks entrantes externos por segmento `/webhook/` (Telegram, Stripe `/tenant/billing/webhook/stripe`, pasarelas `/reconciliation/webhook/{provider}`). **No** se eximen los `/webhooks/` plural (gestión del tenant), que sí exigen CSRF.

Pendiente: tests de integración (POST sin CSRF → 403, con CSRF válido → 200, webhook externo exento) y validar en producción tras Cloudflare Worker que el header no se elimina.

---

### C-06 — Auth y tenant duplicados

#### Evidencia

Auditorías previas listan múltiples sistemas de auth y tenant context.

#### Impacto

Alto. Es la raíz de bugs de seguridad difíciles.

#### Acción

Unificación por contrato técnico y eliminación de rutas antiguas.

---

### C-07 — Admin logs / endpoints internos con validación superadmin pendiente

#### Evidencia previa

`admin_logs.py` fue marcado pendiente porque el comentario dice “todos los tenants superadmin”, pero se observó sólo `Depends(get_current_user)`.

#### Impacto

Crítico si un admin tenant puede ver logs globales.

#### Acción

Verificar y exigir:

```python
Depends(require_scope("admin"))
Depends(require_permission("superadmin.logs.read"))
```

o guard equivalente.

#### ESTADO (2026-06-09) — RESUELTO

Confirmado en `routers/admin_logs.py`: los endpoints `GET /audit` y `GET /audit/stats` (que listan auditoría de **todos** los tenants) usaban solo `Depends(get_current_user)`. Se cambiaron a `Depends(require_scope("admin"))`.

`require_scope("admin")` es el guard correcto aquí (no `require_permission`): un admin de empresa con `is_company_admin=True` haría bypass de `require_permission`, pero su token es `kind="tenant"`, por lo que `require_scope("admin")` lo rechaza. Los endpoints `/` y `/stats` ya filtraban por el tenant del usuario, así que no se tocaron.

---

## 5. Hallazgos medios consolidados

### M-01 — Webhooks devuelven `str(e)`

Impacto:

- filtra errores internos;
- puede exponer URLs, SQL o proveedor.

Acción:

- devolver errores genéricos;
- log interno con request_id.

---

### M-02 — Export CSV/XLSX sin neutralizar fórmulas

Impacto:

- CSV/Excel injection si usuarios guardan productos/clientes con valores tipo `=...`.

Acción:

- escapar valores que empiecen por `=`, `+`, `-`, `@`, tab, CR.

**ESTADO (2026-06-09) — RESUELTO.** En `modules/export/interface/http/tenant.py` se añadió `_sanitize_cell()` (antepone `'` a strings que empiezan por `= + - @ \t \r`) y se aplica en `_csv()` (todas las celdas) y en el export XLSX (campos de texto: almacén, código, producto). Los campos numéricos se serializan como `float`, no como texto.

---

### M-03 — Documents upload con validación débil

Impacto:

- MIME spoofing;
- nombres raros/path traversal lógico;
- almacenamiento de ficheros no deseados;
- trazabilidad incorrecta si `created_by=tenant_id`.

Acción:

- validar tamaño;
- detectar MIME real;
- normalizar nombre;
- `created_by=user_id`.

**ESTADO (2026-06-09) — RESUELTO.** En `modules/documents/interface/http/document_storage.py`:
- `created_by=user_id` (nuevo helper `_user_id_from_request`, fallback a `tenant_id` solo si el token no trae user_id).
- `MAX_UPLOAD_BYTES = 25 MB` → `413` si se excede.
- `_safe_filename()` descarta componentes de ruta (`os.path.basename`) y caracteres de control, trunca a 255.
- `_sniff_mime()` detecta el MIME real por magic bytes (PDF, PNG, JPEG, ZIP/OOXML, GIF) en vez de confiar en el `content_type` declarado por el cliente. Sin dependencias nuevas.

---

### M-04 — Users permite `is_company_admin` y roles/módulos desde payload

Impacto:

- escalada interna si se concede permiso de gestión de usuarios a perfiles no suficientemente restringidos.

Acción:

- separar permisos:
  - crear usuario normal;
  - asignar roles;
  - promover admin;
  - reset password.

---

### M-05 — Accounting seed sin permiso granular

Impacto:

- usuario con scope tenant podría ejecutar seed/force si no tiene permiso específico.

Acción:

- exigir `PERM_ACCOUNTING_ACCOUNT_MANAGE`.

**ESTADO (2026-06-09) — RESUELTO.** En `modules/accounting/interface/http/tenant.py`, el endpoint `POST /chart-of-accounts/seed` ahora declara `dependencies=[Depends(require_permission(PERM_ACCOUNTING_ACCOUNT_MANAGE))]`, igual que `create_cuenta`.

---

### M-06 — Router grande y mezcla HTTP + SQL + negocio

Impacto:

- mantenimiento difícil;
- bugs al tocar endpoints;
- tests más complejos.

Acción:

- routers finos;
- services/use cases;
- repositorios;
- tests unitarios fuera de FastAPI.

---

## 6. Documentación: qué hay que rehacer

### 6.1 Documentos que deben quedar como fuente de verdad

```text
README.md
docs/README.md
docs/arquitectura.md
docs/deploy.md
docs/entornos.md
docs/seguridad.md
docs/backend.md
docs/modules-index.md
docs/routes-inventory.md
docs/security-risk-register.md
docs/security/bypass-rls-register.md
docs/audits/
```

### 6.2 Problemas documentales actuales

1. `README.md` mezcla Render y VPS.
2. `docs/deploy.md` habla de backend Render, pero Frank confirma VPS.
3. `docs/entornos.md` dice API en Render.
4. `render.yaml` puede ser histórico/alternativo, pero parece fuente real.
5. Auditorías están en ficheros sueltos, no integradas en `docs/audits/`.
6. Falta un risk register vivo.
7. Falta inventario de rutas.
8. Falta inventario de bypass RLS.
9. Falta matriz de entornos real.
10. Falta checklist de “base técnica cerrada”.

### 6.3 Nueva estructura recomendada

```text
docs/
├── README.md
├── arquitectura.md
├── backend.md
├── deploy.md
├── entornos.md
├── seguridad.md
├── routes-inventory.md
├── security-risk-register.md
├── modules-index.md
├── audits/
│   ├── 2026-06-09-auditoria-global.md
│   ├── 2026-06-09-auditoria-modules.md
│   └── 2026-06-09-plan-base-tecnica.md
├── security/
│   ├── bypass-rls-register.md
│   ├── csrf.md
│   ├── auth-contract.md
│   └── tenant-context-contract.md
├── deploy/
│   ├── vps-backend.md
│   ├── render-frontends.md
│   ├── cloudflare-worker.md
│   └── migrations-sql.md
└── runbooks/
    ├── deploy-vps.md
    ├── rollback.md
    ├── migrations.md
    ├── redis-celery.md
    └── incident-response.md
```

---

## 7. Plan de acción por fases

### Fase 0 — Congelar arquitectura base

Objetivo: no seguir ampliando deuda.

Acciones:

- Definir deploy real.
- Definir auth canónica.
- Definir tenant context canónico.
- Definir session DB canónica.
- Crear risk register.
- Crear bypass RLS register.

Salida esperada:

```text
docs/security-risk-register.md
docs/security/auth-contract.md
docs/security/tenant-context-contract.md
docs/security/bypass-rls-register.md
docs/deploy/vps-backend.md
```

---

### Fase 1 — Cerrar críticos de seguridad base

#### 1. Session DB

- `app/db/session.py` deja de crear engine propio.
- Workers migrados a sesión oficial.
- Test anti-import.

#### 2. RLS/GUC

- Todos los endpoints tenant prueban `app.tenant_id`.
- Workers usan `tenant_worker_session`.
- `bypass_rls` sólo en helpers auditados.

#### 3. CSRF

- Confirmar middleware.
- Tests reales.

#### 4. Endpoints internos

- `ai_health`, `email_health`, metrics, admin logs, ops/migrations protegidos por superadmin/internal token.

Salida esperada:

```text
pytest app/tests/security/test_session_rls.py
pytest app/tests/security/test_csrf.py
pytest app/tests/security/test_internal_endpoints.py
```

---

### Fase 2 — Unificación

Acciones:

- Unificar auth.
- Unificar tenant context.
- Unificar rate limit.
- Unificar metrics/telemetry.
- Reducir router legacy.

Salida esperada:

```text
core/auth_legacy.py eliminado o wrapper
middleware/tenant_middleware.py eliminado o desactivado
rate limit único
telemetry única
routes-inventory actualizado
```

---

### Fase 3 — Workers y colas

Acciones:

- Revisar `workers/*`.
- Revisar `modules/importador/tasks.py`.
- Añadir idempotencia.
- Añadir dead-letter o tabla de fallos.
- Añadir tests cross-tenant.

Salida esperada:

```text
worker_session.py
event_outbox con retry/backoff
tests multi-tenant workers
```

---

### Fase 4 — Módulos críticos

Orden:

1. identity
2. users
3. company
4. importador
5. documents
6. export
7. webhooks
8. accounting
9. pos/sales
10. invoicing/einvoicing
11. payments/reconciliation
12. inventory

Para cada módulo:

- endpoints;
- permisos;
- tenant_id;
- queries por id;
- payload tenant;
- errores expuestos;
- tests.

---

### Fase 5 — Limpieza de documentación y DX

Acciones:

- Actualizar README.
- Actualizar docs/deploy.
- Actualizar docs/entornos.
- Mover auditorías a `docs/audits`.
- Añadir checklist técnico.
- Añadir scripts de verificación.

---

## 8. Checklist “base técnica cerrada”

No considerar la base cerrada hasta que esto esté en verde:

### Auth

- [ ] Un único flujo login tenant.
- [ ] Un único flujo login admin.
- [ ] Refresh centralizado.
- [ ] Logout centralizado.
- [ ] No hay `get_current_user` alternativo sin wrapper.
- [ ] No hay endpoints admin con sólo auth genérica.

### Tenant

- [ ] Un único `TenantContext`.
- [ ] Ningún endpoint tenant acepta `tenant_id` desde payload.
- [ ] Test cross-tenant por cada módulo crítico.
- [ ] Tenant A no lee tenant B.

### DB/RLS

- [ ] Sólo existe un `SessionLocal` real.
- [ ] Workers usan helper oficial.
- [ ] GUCs aplicados en request y worker.
- [ ] `bypass_rls` inventariado.
- [ ] Test rollback mantiene GUC.

### CSRF

- [ ] Middleware/dependency confirmado.
- [ ] POST sin CSRF falla.
- [ ] POST con CSRF pasa.
- [ ] Login/refresh exenciones documentadas.

### Rate limit

- [ ] Una capa.
- [ ] Redis o storage central si hay varios procesos.
- [ ] Login tenant/admin cubiertos.
- [ ] Password reset cubierto.

### Observabilidad

- [ ] Una capa de metrics.
- [ ] Redacción PII.
- [ ] Request ID en logs.
- [ ] AI/OCR logs sin datos sensibles.

### Routers

- [ ] `app/main.py` no monta routers legacy sueltos salvo excepciones documentadas.
- [ ] `platform/http/router.py` es la fuente de verdad.
- [ ] `routes-inventory.md` existe.

### Deploy

- [ ] README dice VPS backend.
- [ ] docs/deploy dice VPS backend.
- [ ] docs/entornos dice VPS backend.
- [ ] Render documentado sólo para frontends o como legacy.
- [ ] Cloudflare Worker documentado.
- [ ] scripts SQL/migraciones documentados para VPS.

---

## 9. Propuesta de cambios documentales concretos

### 9.1 README.md

Cambiar sección Deploy por:

```md
## Deploy real

GestiqCloud usa despliegue híbrido:

| Componente | Dónde | Motivo |
|---|---|---|
| Backend API FastAPI | VPS | Control de runtime, IA local, OCR, Redis/Celery y scripts SQL |
| Redis | VPS | Broker Celery y caché |
| Celery workers | VPS | Importador, OCR/IA, tareas asíncronas |
| Scripts SQL/migraciones | VPS | Control operativo sobre PostgreSQL |
| Tenant React | Render static | Frontend estático |
| Admin React | Render static | Frontend estático |
| Cloudflare Worker | Cloudflare | CORS, cookies, request-id, proxy `/api/*` |

`render.yaml` se mantiene para frontends y referencia histórica/alternativa del backend, pero el backend productivo actual está en VPS.
```

### 9.2 docs/deploy.md

Renombrar a:

```text
docs/deploy/index.md
docs/deploy/vps-backend.md
docs/deploy/render-frontends.md
docs/deploy/cloudflare-worker.md
```

### 9.3 docs/seguridad.md

Añadir al principio:

```md
## Prioridad 0

Antes de ampliar módulos, cerrar:
- auth única;
- tenant context único;
- session DB única;
- RLS/GUC;
- CSRF real;
- rate limit único;
- telemetry con redacción.
```

### 9.4 docs/backend.md

Actualizar:

- `app/db/session.py` no puede figurar como sesión equivalente.
- Debe decir que `app/config/database.py` es la fuente canónica.
- Workers deben usar helper oficial.

---

## 10. Qué NO haría ahora

No haría ahora:

- más módulos nuevos;
- más pantallas;
- más proveedores de pago;
- más IA/copilot;
- más automatizaciones de negocio;
- más refactor masivo sin tests;
- activar RLS a ciegas en todas las tablas;
- borrar legacy sin inventario de rutas.

Primero se cierra la base.

---

## 11. Orden de trabajo recomendado para Frank

### Semana/Sprint 1

1. Documento de arquitectura real VPS/Render/Cloudflare.
2. Wrapper/eliminación de `app/db/session.py`.
3. Test anti sesión insegura.
4. Confirmar CSRF.
5. Cerrar endpoints internos.

### Semana/Sprint 2

1. TenantContext único.
2. Auth contract.
3. Migrar endpoints más críticos.
4. Rate limit único.
5. Risk register.

### Semana/Sprint 3

1. Workers.
2. Importador.
3. Telegram bot.
4. Documents.
5. Export.

### Semana/Sprint 4

1. Users/roles.
2. Accounting.
3. POS/Sales.
4. Invoicing/payments.

---

## 12. Definición de “base buena”

GestiqCloud tendrá una base buena cuando se pueda decir:

> Si mañana añado un módulo nuevo, no tengo que pensar cómo autenticar, cómo sacar tenant, cómo abrir sesión, cómo aplicar RLS, cómo rate-limitar, cómo loggear ni cómo exponer rutas. Todo eso ya está resuelto por contrato técnico y tests.

Ese es el objetivo.

---

## 13. Archivos críticos a revisar/modificar primero

```text
apps/backend/app/config/database.py
apps/backend/app/db/session.py
apps/backend/app/core/access_guard.py
apps/backend/app/core/authz.py
apps/backend/app/core/auth.py
apps/backend/app/core/auth_http.py
apps/backend/app/core/auth_middleware.py
apps/backend/app/core/refresh.py
apps/backend/app/middleware/tenant.py
apps/backend/app/middleware/tenant_middleware.py
apps/backend/app/middleware/rate_limit.py
apps/backend/app/middleware/endpoint_rate_limit.py
apps/backend/app/platform/http/router.py
apps/backend/app/main.py
apps/backend/app/workers/ai_tasks.py
apps/backend/app/workers/notifications.py
apps/backend/app/workers/expiry_tasks.py
apps/backend/app/modules/importador/tasks.py
apps/backend/app/modules/telegram_bot/interface/http/webhook.py
apps/backend/app/modules/documents/interface/http/document_storage.py
apps/backend/app/modules/export/interface/http/tenant.py
apps/backend/app/modules/users/application/services.py
apps/backend/app/modules/webhooks/interface/http/tenant.py
```

---

## 14. Conclusión

El proyecto tiene bastante trabajo hecho y una ambición real, pero el riesgo no está en “si tiene muchos módulos”. El riesgo está en que el núcleo técnico todavía no tiene una sola verdad.

La mejora más rentable no es añadir más funcionalidad. Es cerrar:

```text
auth + tenant + session + RLS + CSRF + workers + router + documentación real
```

Una vez eso esté cerrado, GestiqCloud tendrá mucha mejor base para crecer sin romperse y sin que cada módulo nuevo arrastre decisiones antiguas.
