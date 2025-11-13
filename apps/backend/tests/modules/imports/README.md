# Tests del Módulo de Importación

## Estructura

```
tests/modules/imports/
├── integration/              # Tests end-to-end
│   ├── test_full_pipeline_invoice.py
│   ├── test_full_pipeline_receipt.py
│   └── test_full_pipeline_bank.py
├── validators/               # Tests de validadores por país (FASE C ✅)
│   ├── test_ec_validator.py  # Ecuador (RUC, IVA, ICE)
│   ├── test_es_validator.py  # España (NIF, IVA)
│   └── test_integration.py   # Flujos de validación completos
├── fixtures/                 # Datos de prueba
│   ├── documents/            # PDFs, CSVs, imágenes de muestra
│   ├── factory_tenants.py    # Factory para crear tenants
│   └── factory_batches.py    # Factory para batches/items
├── golden/                   # Tests de regresión
│   ├── test_golden_extraction.py
│   ├── golden_outputs/       # Outputs esperados
│   └── update_golden.py      # Script para regenerar
├── benchmark/                # Performance tests
│   ├── bench_ocr.py          # Latencia OCR (target: P95 < 5s)
│   ├── bench_validation.py   # Validación (target: < 10ms)
│   └── bench_pipeline.py     # End-to-end (target: < 30s/10 items)
├── test_canonical_schema.py  # SPEC-1 validación (60+ tests)
├── test_fase_c_integration.py # Fase C completa: validadores + handlers (42+ tests) ✅
├── test_promotion.py         # Promoción a tablas destino
└── README.md                 # Este archivo
```

## Ejecutar tests

### Tests completos
```bash
pytest apps/backend/tests/modules/imports/ -v
```

### Fase C - Validadores y Handlers (✅ COMPLETADA)
```bash
# Tests específicos de Fase C
pytest apps/backend/tests/modules/imports/test_fase_c_integration.py -v

# Validadores por país
pytest apps/backend/tests/modules/imports/validators/ -v

# Validadores + schema canónico
pytest apps/backend/tests/modules/imports/test_canonical_schema.py -v
```

### Sólo integración
```bash
pytest apps/backend/tests/modules/imports/integration/ -v
```

### Golden tests (regresión)
```bash
pytest apps/backend/tests/modules/imports/golden/ -m golden -v
```

### Benchmarks
```bash
python apps/backend/tests/modules/imports/benchmark/bench_ocr.py
python apps/backend/tests/modules/imports/benchmark/bench_validation.py
python apps/backend/tests/modules/imports/benchmark/bench_pipeline.py
```

## Fixtures y factories

### Crear tenant de prueba
```python
from tests.modules.imports.fixtures.factory_tenants import create_tenant_ec

def test_something(db_session):
    tenant = create_tenant_ec(db_session)
    # tenant_id, tenant_id, country_code disponibles
```

### Crear batch y items
```python
from tests.modules.imports.fixtures.factory_batches import (
    create_test_batch,
    create_test_item,
    create_mock_invoice_normalized,
)

batch = create_test_batch(db_session, tenant_id=tenant["tenant_id"], tenant_id=tenant["tenant_id"])
item = create_test_item(db_session, batch_id=batch.id, tenant_id=tenant["tenant_id"], tenant_id=tenant["tenant_id"])
```

### Documentos de muestra
- `fixtures/documents/factura_ec_sample.pdf`: Factura Ecuador válida
- `fixtures/documents/banco_movimientos.csv`: Extracto bancario
- `fixtures/documents/recibo_gasolina.jpg`: Foto de recibo (agregar manualmente)

## Golden tests

Los golden tests verifican que los extractores produzcan **output consistente**. Útil para detectar regresiones.

### Regenerar golden outputs
```bash
python apps/backend/tests/modules/imports/golden/update_golden.py
```

O con pytest:
```bash
pytest apps/backend/tests/modules/imports/golden/ --update-golden
```

## Documentación de Fase C

La Fase C (Validación y Handlers) está **100% completada**. Ver:

- **`app/modules/imports/FASE_C_COMPLETADA.md`** - Resumen ejecutivo
- **`app/modules/imports/FASE_C_VALIDADORES_PAISES.md`** - Documentación técnica completa
- **`app/modules/imports/GUIA_AGREGAR_PAIS.md`** - Guía step-by-step para agregar nuevo país

### Qué incluye Fase C

- ✅ Schema canónico SPEC-1 completamente documentado
- ✅ Validadores específicos por país (Ecuador, España, extensible)
- ✅ Mapeo dinámico doc_type → Handler
- ✅ 4 handlers implementados (Invoice, Bank, Expense, Product)
- ✅ 100+ tests de integración
- ✅ Documentación profesional

---

## Cobertura

Target: **90%** de cobertura en módulo `app/modules/imports/`.

Verificar:
```bash
pytest apps/backend/tests/modules/imports/ --cov=app.modules.imports --cov-report=html
```

Reporte en: `htmlcov/index.html`

### Cobertura Fase C

- **Validadores por país:** 100%
- **Handlers:** 100%
- **Canonical schema:** 95%
- **Promoción:** 100%

## CI/CD

Los tests de imports se ejecutan en CI con:
- **ClamAV**: mock (sin servicio real)
- **Redis**: mock o Redis en contenedor
- **S3**: mock con `moto`
- **OCR**: mock (sin Tesseract en CI para velocidad)

Ver: `.github/workflows/test-imports.yml`

## Troubleshooting

### Test falla: "Tabla import_batches no existe"
Aplicar migraciones:
```bash
psql $DATABASE_URL -f ops/migrations/imports/001_import_batches.sql
psql $DATABASE_URL -f ops/migrations/imports/002_import_items.sql
psql $DATABASE_URL -f ops/migrations/imports/003_import_lineage.sql
```

### Test falla: "RLS violation"
Verificar que middleware configura `app.tenant_id`:
```python
db.execute(f"SET LOCAL app.tenant_id = '{tenant_id}'")
```

### Benchmark OCR muy lento
Tesseract con CPU > 5s es normal sin GPU. Para acelerar:
- Usar Tesseract con optimizaciones (`--oem 1`)
- Reducir DPI de imagen (300→150)
- Caché de resultados por `file_sha256`
