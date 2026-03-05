Imports module — batch staging, validation and promotion

## Parsers

Soporte para múltiples formatos de archivo mediante parsers registrados:

### Disponibles
- **Excel**: generic, products_excel
- **CSV**: csv_invoices, csv_bank, csv_products (NUEVO)
- **XML**: xml_invoice, xml_camt053_bank, xml_products (NUEVO)
- **Excel Gastos**: xlsx_expenses (NUEVO)
- **PDF QR**: pdf_qr (NUEVO)

Ver `PARSER_REGISTRY.md` para detalles.

## Documentacion
- Canonica: `README.md`, `README_MODULE.md`, `PARSER_REGISTRY.md`, `PARSER_REGISTRY_GUIDE.md`, `spec_1_importador_documental_gestiq_cloud.md`.
- Historial/planes anteriores: `_legacy_docs/`.

## Endpoints (prefix: /api/v1/imports)
- POST `/batches` → create batch { source_type, origin, file_key?, mapping_id? }
- GET `/batches` → list batches (status= optional)
- GET `/batches/{id}` → get batch
- POST `/batches/{id}/ingest` → { rows[], mapping_id?, transforms?, defaults? }
- GET `/batches/{id}/items` → list items (status=, q=, with=lineage)
- PATCH `/batches/{id}/items/{itemId}` → { field, value } (records correction + revalidate)
- POST `/batches/{id}/validate` → revalidate all items
- POST `/batches/{id}/promote` → promote OK items (idempotent)
- GET `/batches/{id}/errors.csv` → idx,campo,error,valor

Mappings
- CRUD under `/mappings` (create/list/get/update/clone/delete)
- `ImportMapping` has: mappings, transforms, defaults, dedupe_keys
- If `mapping_id` present at batch or ingest, `apply_mapping` is used.

Feature flag
- Set `IMPORTS_ENABLED=1` to mount the imports router.

Persistence models (SQLAlchemy)
- ImportBatch, ImportItem, ImportMapping, ImportItemCorrection, ImportLineage
- ImportItem has: raw, normalized, status, errors, idempotency_key, dedupe_hash, promoted_to/id/at

Validation
- Basic validators for invoices/bank/expenses in `validators.py`.
- Dates: ISO or dd/mm/yyyy recognized where applicable.

Deduplication
- `dedupe_hash` computed per type in ingest. Promotion skips items whose hash was already promoted for the tenant.

Lineage & corrections
- PATCH records `ImportItemCorrection` and revalidates item.
- Promotion records `ImportLineage` with promoted_to and promoted_ref.

Migrations (Alembic)
Create migrations for the following tables/columns if not present:
- Table `import_batches`: id (UUID), tenant_id, source_type, origin, file_key, mapping_id (UUID, nullable), status, created_by (String), created_at (timestamp)
- Table `import_items`: id (UUID), batch_id (FK), idx, raw (JSON), normalized (JSON), status, errors (JSON), dedupe_hash, idempotency_key (unique), promoted_to, promoted_id (UUID, nullable), promoted_at
- Table `import_mappings`: id (UUID), tenant_id, name, source_type, version, mappings (JSON), transforms (JSON), defaults (JSON), dedupe_keys (JSON), created_at
- Table `import_item_corrections`: id (UUID), tenant_id, item_id (FK), user_id (UUID), field, old_value (JSON), new_value (JSON), created_at
- Table `import_lineage`: id (UUID), tenant_id, item_id (FK), promoted_to, promoted_ref, created_at
- Columns in `auditoria_importacion`: batch_id (UUID, nullable), item_id (UUID, nullable)

Notes for tests
- Tests run on SQLite; UUID columns are backed by PG types at runtime. Keep `created_by` as String for portability.
- Router mounts only when `IMPORTS_ENABLED=1`.

Photos (OCR/attachments)
- POST `/batches/{batch_id}/photos` - multipart form-data with `file`: creates an item from a photo (OCR optional)
- POST `/batches/{batch_id}/items/{item_id}/photos` - attach photo to an existing item and re-OCR/merge suggestions

Examples
```bash
# Create batch
curl -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"source_type":"receipts","origin":"ocr"}' \
     http://localhost:8000/api/v1/imports/batches

# Upload a photo to batch
curl -H "Authorization: Bearer $TOKEN" \
     -F file=@/path/to/receipt.jpg \
     http://localhost:8000/api/v1/imports/batches/$BATCH_ID/photos

# Attach a photo to an existing item
curl -H "Authorization: Bearer $TOKEN" \
     -F file=@/path/to/extra.jpg \
     http://localhost:8000/api/v1/imports/batches/$BATCH_ID/items/$ITEM_ID/photos
```
