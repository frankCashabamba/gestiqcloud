# Modulo: webhooks

Proposito: gestionar suscripciones de webhooks por tenant y despachar eventos salientes con firma opcional. No cubre webhooks entrantes de terceros.

## Auth y tenancy
- Rutas bajo router tenant `interface/http/tenant.py` (prefix `/webhooks`), requieren auth de tenant y `ensure_rls`.
- Headers tipicos de auth (Bearer) y `X-Tenant-Id` si el middleware lo exige.

## Endpoints
- POST `/webhooks/subscriptions`
  - Request: `{ "event": "string", "url": "https://...", "secret": "opcional" }`
  - Respuesta 201: `{ "id": "<uuid>", "event": "...", "url": "...", "secret": null|"***", "active": true }`
  - Validaciones: URL https, event no vacio, secret opcional. 400 si payload invalido, 409 si duplicado (mismo event+url activo).
- GET `/webhooks/subscriptions`
  - Lista suscripciones activas. Respuesta 200: `[ {id,event,url,active,created_at} ]`
  - Filtros: `?event=...` (opcional).
- POST `/webhooks/deliveries`
  - Encola entregas para todas las suscripciones activas de `event`.
  - Request: `{ "event": "string", "payload": { ...json... } }`
  - Respuesta 202: `{ "queued": true, "count": <n> }`
  - Errores: 400 si falta event/payload; 404 si no hay suscripciones activas para ese event.

## Modelos/DB
- `webhook_subscriptions`: id (uuid), tenant_id (uuid, RLS), event (text, index), url (text), secret (text null), active (bool default true), created_at.
- `webhook_deliveries`: id (uuid), tenant_id, event, payload (jsonb), target_url (text), status (enum/text), attempts (int default 0), last_error (text null), created_at, updated_at.
- Indices recomendados: (tenant_id,event) en subscriptions; (tenant_id,status) en deliveries.

## Flujo de entrega
- POST `/deliveries` crea registros en `webhook_deliveries` y dispara Celery `apps.backend.app.modules.webhooks.tasks.deliver` (si Celery habilitado) o envio directo async.
- Firma HMAC SHA-256 si la suscripcion tiene `secret`:
  - Header `X-Signature: sha256=<hex_digest>` calculado sobre el body JSON crudo.
  - Header `X-Event: <event>`.
- Timeout: 10s por request.
- Estados `status`: `PENDING` -> `SENDING` -> `DELIVERED` | `FAILED`.
- Reintentos: la tarea reintenta N veces (configurable) o se puede re-disparar manualmente seleccionando deliveries con `status=FAILED`.
- Exito si el receptor responde 2xx; otros codigos marcan `FAILED` con `last_error`.

## Configuracion
- Env vars: `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (si se usa Celery), `WEBHOOK_TIMEOUT_SECONDS` (10 por defecto), `WEBHOOK_MAX_RETRIES` (ej. 3), `WEBHOOK_ALLOWED_SCHEMES` (https), `WEBHOOK_USER_AGENT` (opcional).
- Seguridad: validar que URL sea https; opcional allowlist/denylist de dominios.
- Logging: registrar target_url, status, attempts, duracion; no loggear secrets ni payloads sensibles completos.

## Pruebas rapidas
- Crear suscripcion:
  ```
  curl -X POST -H "Authorization: Bearer <token>" \
    -d '{"event":"order.created","url":"https://webhook.site/xxx","secret":"s"}' \
    https://<host>/api/v1/tenant/webhooks/subscriptions
  ```
- Encolar entrega:
  ```
  curl -X POST -H "Authorization: Bearer <token>" \
    -d '{"event":"order.created","payload":{"id":1}}' \
    https://<host>/api/v1/tenant/webhooks/deliveries
  ```
- Verificar que el receptor reciba headers `X-Event` y `X-Signature` y que el status pase a `DELIVERED` en la DB.
