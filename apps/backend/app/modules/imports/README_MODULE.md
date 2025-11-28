# Módulo: imports (resumen)

Propósito: pipeline de importación (OCR/AI), staging/validación y promoción de datos.

## Endpoints (prefix `/api/v1/imports`)
- Batches: create/list/get.
- Ingest: `/batches/{id}/ingest` (rows/files).
- Validate: `/batches/{id}/validate`.
- Promote: `/batches/{id}/promote`.
- Items: listar, corregir, descargar errors.csv.
- Fotos/OCR: adjuntar fotos a batch o item.
- Preview: `interface/http/preview.py` prefixes `/preview` y `/files` (requiere auth).

## Componentes clave
- `application/tasks/*`: OCR, classify, extract, import, publish.
- `application/job_runner.py`: arranque del runner si `IMPORTS_ENABLED=1` y tablas listas.
- `interface/http/*`: routers (tenant/public/preview).
- `domain/handlers_*`: lógica de parsers y transformaciones.
- Docs internas extensas en `INDICE_DOCUMENTACION_COMPLETA.md` y otros `.md`.

## Notas
- Env: `IMPORTS_ENABLED`, credenciales de OCR/AI/storage si aplica.
- Tablas requeridas: import_batches/items/mappings/lineage/corrections (ver Alembic).
- Tests: ejecutar en SQLite; revisar compatibilidad de tipos.
