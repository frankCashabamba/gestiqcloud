# P0 Integration Guide para HTTP Endpoints

## Resumen de Cambios

Los endpoints HTTP del módulo imports deben ser actualizados para:

1. Usar `robust_parser` para analizar archivos (en lugar de lógica dispersa)
2. Usar `universal_validator` para validar documentos
3. Retornar errores estructurados con contexto completo

## Endpoints a Actualizar

### 1. POST /imports/analyze

**Cambio:** Usar `robust_parser.analyze_file()` para header detection consistente.

**Antes:**
```python
# Lógica dispersa en smart_router + classifier
headers, sample_rows = extract_headers_somehow(file)
suggested_parser = classifier.classify(file)
```

**Después:**
```python
from app.modules.imports.parsers.robust_excel import robust_parser

# Análisis robusto unificado
analysis = robust_parser.analyze_file(file_path)
headers = analysis["headers"]
header_row = analysis["header_row"]

# Clasificación con headers correctos
smart_result = await smart_router.analyze_file(
    file_path=file_path,
    filename=original_filename,
)

# Sugerir mapeo de campos
field_mapping = universal_validator.find_field_mapping(headers, smart_result.suggested_doc_type)
```

**Response mejorado:**
```json
{
  "suggested_parser": "xlsx_invoices",
  "suggested_doc_type": "sales_invoice",
  "headers": ["Factura", "Fecha", "Cliente", "Total"],
  "header_row": 2,
  "sample_rows": [{...}, {...}],
  "field_mapping_suggestion": {
    "Factura": "invoice_number",
    "Fecha": "invoice_date",
    "Cliente": "customer_name",
    "Total": "amount_total"
  },
  "confidence": 0.95
}
```

### 2. POST /imports/batches/{batch_id}/ingest

**Cambio:** Integrar validación con errores estructurados.

**Antes:**
```python
# Parsear + validar con errores genéricos
rows = parse_rows(file)
for row in rows:
    try:
        # validar
    except Exception as e:
        item.errors = [{"error": str(e)}]
```

**Después:**
```python
from app.modules.imports.parsers.robust_excel import robust_parser
from app.modules.imports.domain import universal_validator

# Parse robusto
parse_result = robust_parser.parse_file(file_path)
if not parse_result["success"]:
    return {"status": "PARSE_ERROR", "errors": parse_result["errors"]}

# Validar cada fila
for row_idx, row_data in enumerate(parse_result["rows"], start=parse_result["header_row"]+1):
    # Determinar doc_type del batch
    doc_type = batch.source_type  # "sales_invoice", "expense", etc.

    is_valid, errors = universal_validator.validate_document_complete(
        data=row_data,
        doc_type=doc_type,
        row_number=row_idx,
        item_id=item.id,
        batch_id=batch.id,
    )

    item.status = "VALID" if is_valid else "VALIDATION_FAILED"
    item.errors = errors.to_list()  # Errores estructurados
```

**Response mejorado:**
```json
{
  "batch_id": "...",
  "status": "INGESTED",
  "items_total": 10,
  "items_valid": 8,
  "items_with_errors": 2,
  "errors": [
    {
      "row_number": 3,
      "field_name": "amount",
      "canonical_field": "amount_total",
      "category": "validation",
      "severity": "error",
      "rule_name": "is_positive",
      "message": "Amount must be positive",
      "suggestion": "Ensure value > 0",
      "raw_value": "-100.00",
      "item_id": "item-123"
    },
    {
      "row_number": 5,
      "field_name": "invoice_date",
      "canonical_field": "invoice_date",
      "category": "missing_field",
      "severity": "error",
      "message": "Required field 'invoice_date' is missing",
      "suggestion": "Please provide a value for 'invoice_date'",
      "item_id": "item-124"
    }
  ]
}
```

### 3. PATCH /imports/batches/{batch_id}/items/{item_id}

**Cambio:** Validar corrección contra schema.

**Antes:**
```python
item.normalized[field] = new_value
# Sin validación adicional
```

**Después:**
```python
from app.modules.imports.domain import universal_validator

# Actualizar valor
normalized_data = item.normalized or {}
normalized_data[field] = new_value
item.normalized = normalized_data

# Re-validar documento
is_valid, errors = universal_validator.validate_document_complete(
    data=normalized_data,
    doc_type=batch.source_type,
    row_number=item.row_number,
    item_id=item.id,
)

item.status = "VALID" if is_valid else "VALIDATION_FAILED"
item.errors = errors.to_list()

if is_valid:
    # Registrar corrección
    correction = ImportItemCorrection(
        item_id=item.id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        user_id=request.user.id,
    )
    db.add(correction)
```

### 4. GET /imports/batches/{batch_id}/items/{item_id}

**Response mejorado:**
```json
{
  "id": "item-123",
  "idx": 5,
  "status": "VALIDATION_FAILED",
  "raw": {...},
  "normalized": {...},
  "errors": [
    {
      "row_number": 5,
      "field_name": "invoice_date",
      "canonical_field": "invoice_date",
      "category": "validation",
      "rule_name": "is_date",
      "message": "Date format not recognized (try YYYY-MM-DD)",
      "suggestion": "Use format YYYY-MM-DD or DD/MM/YYYY for 'invoice_date'",
      "raw_value": "2024/1/15"
    }
  ]
}
```

## Ejemplos de Código

### Ejemplo 1: Integrar robust_parser en analyze

```python
@router.post("/imports/analyze")
async def analyze_import_file(file: UploadFile, request: Request):
    from app.modules.imports.parsers.robust_excel import robust_parser
    from app.modules.imports.services.smart_router import smart_router

    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")

    # Guardar archivo temporalmente
    file_path = save_upload(file, tenant_id)

    try:
        # Análisis robusto
        analysis = robust_parser.analyze_file(file_path)

        if not analysis["success"]:
            return {
                "status": "PARSE_ERROR",
                "error": analysis.get("error"),
            }

        # Smart routing
        smart_result = await smart_router.analyze_file(
            file_path=file_path,
            filename=file.filename,
            tenant_id=tenant_id,
        )

        # Field mapping
        field_mapping = universal_validator.find_field_mapping(
            analysis["headers"],
            smart_result.suggested_doc_type,
        )

        return {
            "suggested_parser": smart_result.suggested_parser,
            "suggested_doc_type": smart_result.suggested_doc_type,
            "confidence": smart_result.confidence,
            "headers": analysis["headers"],
            "header_row": analysis["header_row"],
            "sample_rows": analysis["sample_rows"],
            "field_mapping_suggestion": field_mapping,
        }
    finally:
        cleanup_file(file_path)
```

### Ejemplo 2: Integrar validación en ingest

```python
@router.post("/imports/batches/{batch_id}/ingest")
async def ingest_batch(batch_id: UUID, dto: IngestRows, request: Request, db: Session = Depends(get_db)):
    from app.modules.imports.parsers.robust_excel import robust_parser
    from app.modules.imports.domain import universal_validator

    # ... validación de permisos ...

    batch = db.query(ImportBatch).filter(...).first()

    # Parse robusto
    parse_result = robust_parser.parse_file(file_path)

    if not parse_result["success"]:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "PARSE_ERROR",
                "errors": parse_result["errors"],
            },
        )

    total_items = 0
    valid_items = 0
    error_items = 0
    all_errors = []

    for row_idx, row_data in enumerate(parse_result["rows"], start=parse_result["header_row"]+1):
        total_items += 1

        # Validar contra schema
        is_valid, errors = universal_validator.validate_document_complete(
            data=row_data,
            doc_type=batch.source_type,
            row_number=row_idx,
            batch_id=batch.id,
        )

        if is_valid:
            valid_items += 1
            status = "VALID"
            error_list = []
        else:
            error_items += 1
            status = "VALIDATION_FAILED"
            error_list = errors.to_list()
            all_errors.extend(error_list)

        # Crear item en BD
        item = ImportItem(
            batch_id=batch.id,
            idx=row_idx,
            raw=row_data,
            normalized=row_data,  # A refinar luego
            status=status,
            errors=error_list,
        )
        db.add(item)

    db.commit()

    return {
        "batch_id": batch.id,
        "status": "INGESTED",
        "items_total": total_items,
        "items_valid": valid_items,
        "items_with_errors": error_items,
        "errors": all_errors[:100],  # Limit to first 100 for response size
    }
```

## Migration Path

1. **Phase 1 (esta semana):** Crear clases P0 (schemas, validators, errors) - ✅ DONE
2. **Phase 2 (próxima semana):** Integrar en endpoints HTTP
3. **Phase 3:** Suite de tests completa con archivos reales
4. **Phase 4:** Dashboard de telemetría

## Backward Compatibility

Los cambios son aditivos. No breaking changes:

- Los campos antiguos siguen funcionando
- Los nuevos campos coexisten
- Los endpoints retornan errores más ricos pero en formato compatible JSON

## Testing P0

```bash
# Ejecutar suite de regresión
pytest apps/backend/app/tests/test_imports_p0_canonical.py -v

# Ejecutar ejemplos
python apps/backend/app/modules/imports/examples_p0.py
```
