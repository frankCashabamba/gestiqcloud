# Fase E - Scripts Batch Import

Automatización para **importar múltiples archivos en lote** desde carpetas locales. Ideal para:
- Migraciones en masa (100+, 1000+ archivos)
- Ambientes on-premise sin acceso web
- Carga automática de carpetas vigiladas
- Testing en bulk

## 1. Componentes

### `app/modules/imports/scripts/batch_import.py`

Script standalone + clase `BatchImporter` reutilizable.

**Características:**
- ✅ Recursión en subcarpetas
- ✅ Clasificación automática o manual
- ✅ Validación canónica
- ✅ Validación por país (opcional)
- ✅ Promoción a tablas destino (opcional)
- ✅ Reporte JSON detallado
- ✅ Dry-run (simular sin procesar)
- ✅ Skip-errors (continuar ante fallos)

### Integración en CLI

Comando nuevo en `cli.py`:
```bash
python -m app.modules.imports.cli batch-import [OPTIONS]
```

## 2. Uso

### Ejemplo básico - Validar sin procesar

```bash
python -m app.modules.imports.cli batch-import \
  --folder C:\datos\facturas \
  --doc-type invoice \
  --validate \
  --report results.json
```

### Ejemplo avanzado - Procesar, validar y promocionar

```bash
python -m app.modules.imports.cli batch-import \
  --folder /data/imports \
  --doc-type invoice \
  --country EC \
  --validate \
  --promote \
  --report report.json \
  --pattern "*.xlsx"
```

### Ejemplo de simulación

```bash
python -m app.modules.imports.cli batch-import \
  --folder /data/test \
  --doc-type product \
  --validate \
  --dry-run
```

### Usar parser específico

```bash
python -m app.modules.imports.cli batch-import \
  --folder /data/bank \
  --parser csv_bank \
  --validate
```

## 3. Opciones

| Opción | Tipo | Default | Descripción |
|--------|------|---------|-------------|
| `--folder` | str | **REQUIRED** | Carpeta a procesar |
| `--doc-type` | str | None | Tipo: invoice, product, expense, bank_tx |
| `--parser` | str | None | Parser específico (auto-detect si no se usa) |
| `--pattern` | str | `*.*` | Patrón glob: `*.csv`, `*.xlsx`, etc. |
| `--recursive / --no-recursive` | bool | True | Buscar en subcarpetas |
| `--validate / --no-validate` | bool | True | Validar esquema canónico |
| `--country` | str | None | Código país para validación: EC, ES, etc. |
| `--promote / --no-promote` | bool | False | Promocionar a tablas destino |
| `--dry-run` | bool | False | Simular sin procesar |
| `--skip-errors / --fail-fast` | bool | True | Continuar en errores |
| `--report` | str | batch_import_report.json | Archivo de salida |

## 4. Reporte JSON

Estructura del archivo generado:

```json
{
  "summary": {
    "total_files": 150,
    "processed": 145,
    "successful": 140,
    "skipped": 3,
    "failed": 5,
    "validation_errors": 4,
    "promotion_errors": 1,
    "total_items": 850,
    "total_time_ms": 45230.5,
    "started_at": "2025-11-11T10:30:00.123456",
    "completed_at": "2025-11-11T10:31:15.654321"
  },
  "results": [
    {
      "filename": "facturas_2025_01.csv",
      "filepath": "/data/facturas/2025/01/facturas_2025_01.csv",
      "status": "success",
      "doc_type": "invoice",
      "parser_id": "csv_invoices",
      "items_count": 45,
      "errors": [],
      "warnings": [],
      "promoted": true,
      "promotion_errors": [],
      "processing_time_ms": 125.5,
      "timestamp": "2025-11-11T10:30:15.123456"
    },
    {
      "filename": "gastos_invalidos.xlsx",
      "filepath": "/data/facturas/gastos_invalidos.xlsx",
      "status": "validation_error",
      "doc_type": "expense",
      "parser_id": "xlsx_expenses",
      "items_count": 10,
      "errors": [
        "Missing required field: amount",
        "Invalid date format in row 5"
      ],
      "warnings": [],
      "promoted": false,
      "promotion_errors": [],
      "processing_time_ms": 85.2,
      "timestamp": "2025-11-11T10:30:42.789012"
    }
  ]
}
```

## 5. Estados de Importación

| Estado | Descripción |
|--------|-------------|
| `success` | Archivo procesado, validado y (opcionalmente) promocionado |
| `validation_error` | Archivo parseado pero falló validación canónica |
| `parser_error` | Error al parsear el archivo |
| `promotion_error` | Parseado y validado pero promoción falló |
| `skipped` | No hay parser disponible para el archivo |
| `failed` | Error inesperado |

## 6. Uso programático

### Desde Python

```python
import asyncio
from pathlib import Path
from app.modules.imports.scripts.batch_import import BatchImporter

async def import_documents():
    importer = BatchImporter(
        folder=Path("/data/facturas"),
        doc_type="invoice",
        country="EC",
        validate=True,
        promote=True,
    )
    report = await importer.run()
    
    print(f"✓ Successful: {report.successful}")
    print(f"✗ Failed: {report.failed}")
    print(f"Items: {report.total_items}")
    
    return report

report = asyncio.run(import_documents())
```

### Configuración avanzada

```python
importer = BatchImporter(
    folder=Path("/data"),
    doc_type="invoice",
    parser_id="csv_invoices",  # Forzar parser específico
    recursive=True,             # Buscar en subdirectorios
    pattern="2025_*.csv",       # Solo archivos de 2025
    validate=True,
    promote=True,
    country="ES",               # Validación España
    dry_run=False,              # Procesar en serio
    skip_errors=True,           # Continuar en errores
)
```

## 7. Casos de uso

### 7.1 Migración de legacy system

```bash
python -m app.modules.imports.cli batch-import \
  --folder /legacy_backup/facturas \
  --doc-type invoice \
  --country EC \
  --validate \
  --promote \
  --report migration_report.json
```

Analizar reporte:
```bash
cat migration_report.json | jq '.summary'
cat migration_report.json | jq '.results[] | select(.status=="validation_error")'
```

### 7.2 Validación masiva (sin procesar)

```bash
python -m app.modules.imports.cli batch-import \
  --folder /uploads/pending \
  --country EC \
  --validate \
  --no-promote \
  --dry-run \
  --report validation_only.json
```

### 7.3 Cargar carpeta vigilada periódicamente (cron/scheduler)

```bash
#!/bin/bash
# /scripts/import_daily.sh

FOLDER="/var/imports/incoming"
REPORT="/var/imports/logs/$(date +%Y%m%d_%H%M%S).json"

python -m app.modules.imports.cli batch-import \
  --folder "$FOLDER" \
  --doc-type invoice \
  --country EC \
  --validate \
  --promote \
  --report "$REPORT" \
  --skip-errors

# Enviar reporte
if grep -q '"failed": 0' "$REPORT"; then
  echo "✓ Import exitoso" | mail -s "Import Report" admin@company.com
else
  cat "$REPORT" | mail -s "⚠️ Import con errores" admin@company.com
fi

# Limpiar archivos procesados exitosamente
# (opcional: backup antes de borrar)
```

### 7.4 Testing - validar estructura

```bash
python -m app.modules.imports.cli batch-import \
  --folder tests/fixtures/invoices \
  --doc-type invoice \
  --validate \
  --report test_validation.json \
  --skip-errors
```

## 8. Mejoras futuras

- [ ] **Webhook notifications**: Notificar cuando se completan batches
- [ ] **Database logging**: Persistir en BD en lugar de solo JSON
- [ ] **Parallelization**: Procesar múltiples archivos en paralelo
- [ ] **Retry policy**: Reintentos automáticos para errores transitorios
- [ ] **S3/Cloud storage**: Leer desde buckets S3, Azure Blob, etc.
- [ ] **Watch folder**: Daemon que vigile carpeta e importe automáticamente
- [ ] **Audit trail**: Historial completo en BD

## 9. Troubleshooting

### "No files found"

```bash
# Verificar patrón
python -m app.modules.imports.cli batch-import \
  --folder /data \
  --pattern "*.csv"  # Asegurar coincidencias
```

### "No suitable parser found"

```bash
# Listar parsers disponibles
python -m app.modules.imports.cli list-parsers

# Especificar parser explícitamente
python -m app.modules.imports.cli batch-import \
  --folder /data \
  --parser csv_invoices
```

### "Validation errors"

```bash
# Ver errores en el reporte
jq '.results[] | select(.status=="validation_error") | .errors' report.json
```

### "Promotion failed"

```bash
# Ver errores de promoción
jq '.results[] | .promotion_errors' report.json
```

## 10. Referencias

- `IMPORTADOR_PLAN.md` - Plan general
- `FASE_B_NUEVOS_PARSERS.md` - Parsers disponibles
- `FASE_C_VALIDADORES_PAISES.md` - Validadores por país
- `FASE_D_IA_CONFIGURABLE.md` - Clasificación IA
- `PARSER_REGISTRY.md` - Registro de parsers
