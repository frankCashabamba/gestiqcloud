# Módulo Importador

Estado: Beta
Madurez: 3/5
Owner: Frontend/Backend
Riesgo: Alto

## Implementado

- Upload asincrónico, listado de documentos, detalle, revisión y confirmación.
- Routing de destino, guardado en destino y modal de confirmación.
- Soporte para documentos, productos, recetas y diarios según backend.

## Parcial

- `raw_ai_json` y snapshots deben quedar limitados a debug o vistas técnicas.
- Campos derivados por IA necesitan señal visual consistente.

## Pendiente

- E2E importador.
- Historial visible de cambios por documento.
- Política de datos sensibles y PII.

## Endpoints usados

- `/api/v1/tenant/imports/*`
- `/api/v1/tenant/importador/*` si aplica en rutas legacy.

## Permisos

- `importer:use`
- Pendiente granular: `imports:confirm`, `imports:route`, `imports:purge`.

## Tests mínimos

- Subir archivo.
- Abrir documento en revisión.
- Confirmar datos.
- Guardar en destino con confirmación.
- Bloquear raw/debug JSON fuera de modo debug.
