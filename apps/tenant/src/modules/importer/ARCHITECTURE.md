Importador (frontend) – Arquitectura y lineamientos
==================================================

Propósito
---------
Módulo universal de importación (Excel/CSV/PDF/imagen) con soporte multi-tenant, mapeo de columnas y colas locales. Entrada única preferida: `ImportadorExcelWithQueue` en `/imports`.

Rutas y entrypoints
-------------------
- `Routes.tsx`: monta `/imports` con `ImportQueueProvider`.
  - `/imports` → `ImportadorExcelWithQueue` (principal).
  - `/imports/wizard` → `Wizard` (flujo alterno guiado).
  - `/imports/preview` → `PreviewPage` (lote concreto).
  - `/imports/batches` → `BatchesList` / `BatchDetail`.
- `manifest.ts`: registra el módulo en el menú y usa `Panel.tsx` (que renderiza `ImportadorExcelWithQueue`).

Estado y servicios
------------------
- Estado: `context/ImportQueueContext.tsx` gestiona la cola local, persistencia en localStorage y reintentos OCR. Estados: pending, processing, ready, saving, saved, duplicate, error.
- Servicios:
  - `services/importsApi.ts`: cliente oficial `/api/v1/imports/*` (batches, items, mappings, chunked upload, OCR jobs, promote, OCR enqueue/poll).
  - `services/parseExcelFile.ts`: parseo XLSX en cliente; usa `VITE_IMPORTS_CHUNK_THRESHOLD_MB` para decidir chunked upload.

Componentes clave
-----------------
- `ImportadorExcelWithQueue`: dropzone, lista de cola, enlaces a pendientes/historial.
- `ImportQueueContext`: procesa archivos (CSV/Excel/Doc), selecciona mapping por patrón, sube por chunks si excede umbral, ejecuta OCR para PDF/imagen y llama a `createBatch` + `ingestBatch`.
- `imports/BatchesList` + `BatchDetail`: vista de lotes y acciones (validate/promote/download errors).
- `components/ColumnMapper` y `utils/aliasCampos`, `detectarTipoDocumento`: ayudan al auto-mapeo y detección de tipo.

Flujos soportados
-----------------
1) **Excel/CSV pequeño**: lee en cliente → detecta tipo → `createBatch` → `ingestBatch`.
2) **Excel grande**: chunked upload local (`/imports/uploads/chunk/*`) → `createBatchFromUpload` → `start-excel-import`.
3) **PDF/Imagen**: `procesarDocumento` encola OCR → `pollOcrJob` → `ingestBatch` con filas OCR.
4) **Preview/validación**: `/imports/preview?batch_id=` consume `listItems` y permite parches vía `patchItem`.

Configuración y env
-------------------
- `VITE_IMPORTS_CHUNK_THRESHOLD_MB`: umbral para usar chunked upload.
- `VITE_IMPORTS_JOB_RECHECK_INTERVAL`, `VITE_IMPORTS_JOB_POLL_INTERVAL`, `VITE_IMPORTS_JOB_POLL_ATTEMPTS`: intervalos/reintentos OCR.
- Tipos y aliases en `config/entityTypes.ts` (carga dinámica con `/field-config/fields` y sector template_config).

Deudas y duplicados
-------------------
- Alinear `source_type` usados en cliente con los aceptados por backend (`products`, `invoices`, `bank`, `expenses`).

Testing sugerido
----------------
- Unit: parsers de CSV/Excel, detección de tipo, auto-mapeo de columnas.
- Integration (mock API): cola procesa CSV/Excel, caída a chunked upload, reintentos OCR, flujos de validación/promoción en `BatchDetail`.

Extensión
---------
- Nuevos tipos: agregar en `config/entityTypes.ts` y exponer aliases; validar que backend acepte el `source_type`.
- Nuevos endpoints: envolver en `services/importsApi.ts` y usarlos desde contexto/flows en vez de servicios legacy.
