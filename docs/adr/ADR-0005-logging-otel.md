# ADR-0005: Logging y OpenTelemetry

- Estado: Aceptado
- Fecha: 2025-xx-xx
- Autor: (tu nombre)

## Contexto
- FastAPI + SQLAlchemy en Render con OTEL_ENABLED=1 (backend/worker/beat).
- Se requieren logs con request_id y métricas básicas (latencia/errores por endpoint) para operación.

## Decisión
- Logs a STDOUT con niveles INFO en prod, DEBUG solo en dev.
- Propagar `X-Request-Id` desde CF Worker (ADR-0001) y adjuntarlo en logs.
- Activar OpenTelemetry con exporter OTLP configurable por env (`OTEL_EXPORTER_OTLP_ENDPOINT`); `OTEL_SERVICE_NAME` por servicio (api, worker, beat).
- Métricas mínimas: `http.server.duration`, `http.server.errors`, auth 401/403, imports (batches failed/pending), pagos (intent/error por proveedor), einvoicing (fallos/latencia), health `/ready`.
- Trazas opcionales según necesidad; priorizar métricas y logs.

## Consecuencias
- Necesidad de configurar endpoint OTLP en cada entorno (secreto). Sin endpoint, OTEL se puede desactivar.
- Panel/dashboards deben consumir el exporter (Prometheus/OTel backend/Datadog, según elección futura).

## Referencias
- `docs/observabilidad.md` (métricas/alertas sugeridas).
- `render.yaml` (OTEL_ENABLED, OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT).
