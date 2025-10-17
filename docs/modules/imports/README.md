# Módulo de Importación Documental — GestiqCloud

**Versión**: 1.0  
**Última actualización**: 2025-01-17

## Resumen

El módulo de **importación documental** de GestiqCloud procesa documentos heterogéneos (facturas PDF/XML, recibos, extractos bancarios CSV/Excel) y los convierte en datos estructurados normalizados para contabilidad y finanzas.

### Características principales

- **Multi-tenant estricto** con Row-Level Security (RLS)
- **Pipeline completo**: ingest → preprocess → extract → validate → promote
- **OCR self-hosted** (Tesseract) con mejora de imagen
- **Validación fiscal** para Ecuador (SRI) y España (AEAT)
- **Deduplicación** por hash y linaje completo
- **Procesamiento asíncrono** con Celery y Redis
- **Seguridad**: antivirus, sandbox PDF, límites de tamaño
- **Observabilidad**: métricas Prometheus, logs estructurados, OpenTelemetry

## Arquitectura

Consulta [ARCHITECTURE.md](./ARCHITECTURE.md) para diagramas completos.

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                      API /api/v1/imports                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────────┐│
│  │ Batches  │  │  Items   │  │Corrections│  │  Mappings  ││
│  └──────────┘  └──────────┘  └───────────┘  └────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Workers (Celery)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │Preprocess│→ │ Extract  │→ │ Validate │→ │  Promote   │ │
│  │(AV+OCR)  │  │(Parsers) │  │ (Rules)  │  │(Publish)   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Storage & Data                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  MinIO   │  │PostgreSQL│  │  Redis   │                  │
│  │  (S3)    │  │  + RLS   │  │ (Queue)  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Inicio rápido

### 1. Configuración

```bash
# Variables de entorno necesarias
export DATABASE_URL="postgresql://user:pass@localhost/gestiqcloud"
export REDIS_URL="redis://localhost:6379/0"
export S3_ENDPOINT="http://localhost:9000"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin"
export S3_BUCKET="gestiqcloud-imports"

# Opcional para producción
export CLAMAV_HOST="localhost"
export CLAMAV_PORT="3310"
```

### 2. Migraciones

```bash
# Aplicar migraciones del módulo imports
psql $DATABASE_URL -f ops/migrations/imports/001_import_batches.sql
psql $DATABASE_URL -f ops/migrations/imports/002_import_items.sql
psql $DATABASE_URL -f ops/migrations/imports/003_import_lineage.sql
psql $DATABASE_URL -f ops/migrations/imports/004_rls_policies.sql
```

### 3. Iniciar workers

```bash
# Worker para imports (con cola dedicada)
celery -A apps.backend.celery_app worker \
  -Q imports \
  -n imports@%h \
  --concurrency=4 \
  --loglevel=info
```

### 4. API disponible

```bash
# Healthcheck
curl http://localhost:8000/api/v1/imports/health

# Crear batch
curl -X POST http://localhost:8000/api/v1/imports/batches \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "invoices", "description": "Facturas enero 2025"}'
```

## Uso básico

### Importar facturas desde API

```python
import requests

# 1. Crear batch
response = requests.post(
    "https://api.gestiqcloud.com/api/v1/imports/batches",
    headers={"Authorization": f"Bearer {token}"},
    json={"source_type": "invoices", "description": "Facturas proveedor A"},
)
batch_id = response.json()["id"]

# 2. Solicitar presigned URL para subir archivo
response = requests.post(
    f"https://api.gestiqcloud.com/api/v1/imports/batches/{batch_id}/upload-url",
    headers={"Authorization": f"Bearer {token}"},
    json={"filename": "factura_001.pdf", "content_type": "application/pdf"},
)
upload_url = response.json()["upload_url"]
file_key = response.json()["file_key"]

# 3. Subir archivo a S3
with open("factura_001.pdf", "rb") as f:
    requests.put(upload_url, data=f.read(), headers={"Content-Type": "application/pdf"})

# 4. Notificar ingesta
requests.post(
    f"https://api.gestiqcloud.com/api/v1/imports/batches/{batch_id}/ingest",
    headers={"Authorization": f"Bearer {token}"},
    json={"file_key": file_key, "filename": "factura_001.pdf"},
)

# 5. Monitorear progreso
response = requests.get(
    f"https://api.gestiqcloud.com/api/v1/imports/batches/{batch_id}",
    headers={"Authorization": f"Bearer {token}"},
)
status = response.json()["status"]
```

### Correcciones manuales

```python
# Obtener item con errores de validación
response = requests.get(
    f"https://api.gestiqcloud.com/api/v1/imports/items/{item_id}",
    headers={"Authorization": f"Bearer {token}"},
)
item = response.json()

# Aplicar corrección
requests.post(
    f"https://api.gestiqcloud.com/api/v1/imports/items/{item_id}/corrections",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "corrections": {
            "proveedor.tax_id": "1790016919001",  # Corregir RUC
            "totales.total": 112.00,               # Ajustar total
        },
        "reason": "RUC mal leído por OCR",
    },
)

# Revalidar
requests.post(
    f"https://api.gestiqcloud.com/api/v1/imports/items/{item_id}/revalidate",
    headers={"Authorization": f"Bearer {token}"},
)
```

### Promover batch completo

```python
# Promover todos los items validados a tablas destino
response = requests.post(
    f"https://api.gestiqcloud.com/api/v1/imports/batches/{batch_id}/promote",
    headers={"Authorization": f"Bearer {token}"},
)

# Verificar lineage
response = requests.get(
    f"https://api.gestiqcloud.com/api/v1/imports/batches/{batch_id}/lineage",
    headers={"Authorization": f"Bearer {token}"},
)
lineage = response.json()["items"]
```

## Tipos de documentos soportados

### 1. Facturas (invoices)

**Formatos**: PDF, XML (Facturae, SRI), imágenes JPG/PNG  
**Destino**: `expenses` (facturas de compra)  
**Validadores**: Ecuador (RUC, clave de acceso), España (NIF, CIF)

**Campos extraídos**:
- Proveedor (tax_id, nombre, dirección)
- Cliente (tax_id, nombre)
- Totales (subtotal, IVA, retenciones, total)
- Líneas (descripción, cantidad, precio, subtotal)
- Fecha emisión, número de factura

### 2. Recibos (expenses)

**Formatos**: JPG, PNG, PDF  
**Destino**: `expenses`  
**OCR**: Tesseract con mejora de imagen

**Campos extraídos**:
- Establecimiento
- Fecha
- Total
- Concepto (texto libre)

### 3. Movimientos bancarios (bank)

**Formatos**: CSV, Excel, CAMT.053, MT940  
**Destino**: `bank_movements`  
**Validadores**: IBAN, saldos

**Campos extraídos**:
- IBAN/cuenta
- Fecha valor
- Concepto
- Debe/Haber
- Saldo
- Referencia

## Estados del pipeline

```
draft → preprocessing → extracted → validated → promoted
                    ↓           ↓           ↓
              rejected_duplicate  validation_failed  promotion_failed
```

- **draft**: Batch creado, sin items
- **preprocessing**: Antivirus + OCR en progreso
- **extracted**: Datos normalizados disponibles
- **validated**: Pasó todas las reglas
- **promoted**: Publicado a tabla destino
- **validation_failed**: Errores de validación (requiere corrección)
- **rejected_duplicate**: Hash duplicado

## Seguridad

### Row-Level Security (RLS)

Todas las tablas de imports tienen **RLS habilitado**:

```sql
-- Política por tenant
CREATE POLICY tenant_isolation ON import_batches
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

Middleware de API configura `SET LOCAL app.tenant_id` en cada request.

### Antivirus

ClamAV escanea todos los archivos antes de procesarlos:

```python
# Configuración en settings
CLAMAV_ENABLED = True
CLAMAV_HOST = "localhost"
CLAMAV_PORT = 3310
```

### Sandbox PDF

PDFs se procesan en contenedor aislado con límites:
- Max 50 páginas
- Max 20 MB
- Timeout 30s

## Observabilidad

### Métricas Prometheus

```
# Contadores
imports_batches_created_total
imports_items_processed_total{status="validated|failed"}
imports_promotions_total{destination="expenses|bank_movements"}

# Histogramas (latencias)
imports_ocr_duration_seconds
imports_validation_duration_seconds
imports_promotion_duration_seconds

# Gauges
imports_queue_size{queue="imports"}
imports_batches_pending
```

### Logs estructurados

```json
{
  "timestamp": "2025-01-17T10:30:00Z",
  "level": "info",
  "module": "imports",
  "action": "item_validated",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "batch_id": "660e8400-e29b-41d4-a716-446655440000",
  "item_id": "770e8400-e29b-41d4-a716-446655440000",
  "duration_ms": 45,
  "validation_errors": 0
}
```

### Traces (OpenTelemetry)

Instrumentación automática de:
- HTTP requests (FastAPI)
- DB queries (SQLAlchemy)
- Celery tasks
- Redis operations

## Performance

### Targets (SLA)

- **OCR**: P95 < 5s por página (2 CPU cores)
- **Validación**: < 10ms por item
- **Promoción**: < 100ms por item
- **Pipeline completo**: < 30s para batch de 10 items (sin OCR)

### Optimizaciones

1. **Caché de OCR**: resultados por file_sha256
2. **Bulk inserts**: promoción en batch
3. **Índices**: `(tenant_id, batch_id)`, `(file_sha256)`, `(promoted_id)`
4. **Pool de DB**: 20 conexiones por worker

## Troubleshooting

Consulta [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) para problemas comunes.

## API completa

Consulta [API.md](./API.md) para referencia completa de endpoints.

## Deployment

Consulta [DEPLOYMENT.md](./DEPLOYMENT.md) para guías de despliegue.

## Testing

```bash
# Tests unitarios
pytest apps/backend/tests/modules/imports/

# Tests de integración
pytest apps/backend/tests/modules/imports/integration/

# Golden tests
pytest apps/backend/tests/modules/imports/golden/

# Benchmarks
python apps/backend/tests/modules/imports/benchmark/bench_ocr.py
python apps/backend/tests/modules/imports/benchmark/bench_validation.py
python apps/backend/tests/modules/imports/benchmark/bench_pipeline.py
```

## Licencia

Propietario — GestiqCloud © 2025
