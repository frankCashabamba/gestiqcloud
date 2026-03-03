# Diseño profesional v2 — Importador 100% configurable (Backend + Frontend + IA + BD)
GestiqCloud · Importer module · 2026-02-27

## 0. Objetivo
No volver a tocar el módulo: **nuevos archivos/idiomas** se soportan con **templates en BD** desde UI. IA solo como apoyo, todo auditado.

## 1. Principios
- Extracción genérica -> IR estable -> Templates declarativos -> Validación/Promoción
- Persistir artefactos por etapa para reproceso
- Idempotencia end-to-end
- Multilenguaje por synonyms en templates
- DSL seguro (sin eval/exec)
- Golden files + CI

## 2. Arquitectura final
Etapas:
A Ingesta+sha -> ImportBatch
B Artifacts (OCRJob, tablas, texto)
C IR en ImportItem.raw (source_locator)
D Match template (reglas + IA)
E Apply template -> normalized/canonical_doc
F Validación + ImportResolution
G Promoción idempotente + lineage + PostingRegistry

## 3. BD (reusar tu esquema)
Sin migraciones obligatorias:
- `ImportBatch.parser_choice_confidence` guarda JSON de sha256, IA (model/prompt), scores.
- `ImportOCRJob.result` guarda meta + pages[].text (+ tokens opcional).
- `ImportAttachment.ocr_text` guarda texto final.
- `ImportItem.raw` guarda `source` (sheet/page/row) + `language`.

Opcional migración: `ImportBatch.file_sha256`, `ImportAttachment.page_no`.

## 4. IR estable (ImportItem.raw)
```json
{
  "source": {"file_sha256":"...", "origin":"excel|pdf_ocr", "sheet":"Hoja1", "page":2, "row":27},
  "language":"es",
  "artifacts_ref": {"ocr_job_id":"...","attachment_ids":["..."]},
  "tables":[{"headers_raw":["..."],"headers_norm":["..."],"rows":[{"...":"..."}]}],
  "text":"...",
  "kv":{"RUC":"..."}
}
```

## 5. Template schema v2 (ImportMapping.mappings)
```json
{
  "template_version": 2,
  "match": {"filename_regex":"PAN KUSI.*\\.xlsx$","language":["es","en"],"priority":50},
  "extract": {"mode":"excel_grid","all_sheets":true,"sheet_rules":[{"sheet_name_regex":"FORMATO.*","merged_cells":{"fill":true}}]},
  "header_normalization": {"strip_accents":true,"synonyms":{"es":{"producto":["nombre"]}}},
  "map": {"name":["producto","product"],"stock":["cantidad","qty"],"price":["precio","unit_price"]},
  "transforms": {"price":{"type":"number","fallback":0},"unit":{"expr":"coalesce(unit, unidad, 'unit')"}},
  "defaults": {"category":"SIN_CATEGORIA"},
  "dedupe_keys": ["name","price","stock"],
  "output": {"doc_type":"product"}
}
```

## 6. Backend (ejecutable por IA)
### Módulos propuestos
- `imports/application/template_engine/` (schema/matcher/header_norm/table_reader/interpreter/dsl/validator)
- `imports/application/ir_builder.py`
- `imports/application/reprocess_service.py`
- Rutas: `imports/routes/templates.py`, `imports/routes/reprocess.py`

### API mínima
- GET/POST/PUT `/api/v1/tenant/imports/mappings`
- POST `/api/v1/tenant/imports/batches/{id}/analyze`
- POST `/api/v1/tenant/imports/batches/{id}/apply-template`
- POST `/api/v1/tenant/imports/batches/{id}/reprocess`

### DSL seguro
Implementar con `ast` y whitelist de funciones (`coalesce`, `to_number`, `to_date`, `regex_extract`, etc.).

### Excel reader
- .xls -> xlrd o conversión
- multi-hoja, merged fill, header detect por hits contra `map`
- construir `headers_norm` con `header_normalization + synonyms`

### OCR estándar
- `image_to_data` para reconstruir líneas
- persistir meta+pages en `ImportOCRJob.result`

## 7. Frontend (ejecutable por IA)
- UI wizard para TemplateV2 + diccionario multilenguaje + simulación
- `TemplateManager.tsx` + `MappingSuggestModal.tsx` + `ConfirmParserModal.tsx`
- `importsApi.ts`: funciones list/create/update/apply/reprocess
- Tipos TS: `TemplateV2`

## 8. IA (prompts + validación + auditoría)
- Clasificación: JSON estricto con doc_type/mapping_id/confidence/reasons/language
- Mapping suggestion: JSON con map/synonyms/confidence
- Persistir en `ImportBatch.parser_choice_confidence` (model/prompt_version)

## 9. Golden files + CI + métricas
- Suite de archivos reales + snapshots por template
- métricas %EMPTY/%PARTIAL, OCR conf, headers desconocidos

## 10. Runbook
Deps: tesseract + idiomas, poppler/pymupdf, libreoffice/xlrd, libs python.
Env:
```bash
IMPORTS_OCR_LANG=spa+eng
IMPORTS_OCR_PSM=6
IMPORTS_OCR_DPI=300
IMPORTS_AI_PROVIDER=ollama ya implementado
OPENAI_API_KEY=...
```
