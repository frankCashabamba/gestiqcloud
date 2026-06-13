# Módulo Copilot

Estado: Beta
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Dashboard y métricas de IA.
- Chat global mediante widget compartido.
- Streaming, feedback y sugerencias contextuales cuando backend lo soporta.

## Parcial

- Requiere control de coste, rate limits, trazabilidad y minimización de datos.
- Los contextos por módulo deben validarse para no exponer PII innecesaria.

## Pendiente

- Tests de permisos y privacidad.
- Observabilidad de coste/error por tenant.

## Endpoints usados

- `/api/v1/tenant/ai/*`

## Permisos

- `copilot:read`

## Tests mínimos

- Abrir panel.
- Enviar consulta.
- Registrar feedback.
- Bloquear acceso sin permiso.
