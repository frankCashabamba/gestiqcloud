# Módulo: ai_agent / copilot

Propósito: endpoints/servicios de asistencia AI (si se despliegan).

## Endpoints
- Copilot: `copilot/interface/http/tenant.py` prefix `/ai`.
- Imports AI: `imports/ai/http_endpoints.py` prefix `/imports/ai` (ver módulo imports).

## Componentes clave
- `services.py`/`provider` según implementación.
- Integración con `imports/ai` si se reusa providers.

## Notas
- Revisar claves de proveedor AI en env antes de habilitar.
