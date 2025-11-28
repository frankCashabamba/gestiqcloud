# Observabilidad y alertas

## Logs
- Loggers clave: `app.startup`, `app.router`, `app.health`, `app.cors`, `app.docs`, `app.imports`, `app.payments`, `app.einvoicing`.
- Nivel recomendado: INFO en prod, DEBUG solo en dev.
- Propagar `X-Request-Id` (worker CF lo añade) y guardarlo en logs.

## Métricas (OTel)
- HTTP: `http.server.duration`, `http.server.errors` con labels `route`, `status`.
- Auth: tasa de 401/403 en `/auth/login` (admin/tenant), ratio de refresh fallidos.
- Imports: batches por estado (pending/failed), duración de `validate`/`promote`, colas/tareas `imports.*`.
- Pagos: intentos vs éxitos por proveedor, errores por tipo, latencia de confirmación/webhooks.
- E-invoicing: emisiones fallidas, latencia de proveedor, colas pendientes.
- DB/Redis: conexiones activas, errores, tiempo de consulta; ping en `/ready`.
- Infra: 5xx globales, uso CPU/RAM del servicio backend.

## Alertas sugeridas
- Auth: >5% 401/403 en login en 5 min; spike de rate-limit en login.
- Imports: batches `failed` > N o tareas encoladas > X min; tiempo de `validate`/`promote` fuera de SLA.
- Pagos: ratio de fallos > Y% por proveedor; webhooks 4xx/5xx.
- E-invoicing: emisiones fallidas consecutivas > N; latencia proveedor > umbral.
- Health: `/ready` 503 o sin respuesta.

## Dashboards mínimos
- Tráfico y errores por endpoint.
- Auth success/fail y rate-limit hits.
- Imports: estados, duración, colas.
- Pagos: intentos, éxito, error por proveedor; webhooks.
- E-invoicing: emisiones por estado, latencia.
- Infra: recursos y DB/Redis.

## Cómo ver/consultar
- Logs: usar visor de Render/collector OTel; filtrar por `request_id`.
- Métricas: configurar exporter OTLP/HTTP en `app/telemetry/otel.py` (añadir endpoint en env) y consumir en Prometheus/OTel backend.
