# Celery Setup para Imports Pipeline

## Arquitectura

```mermaid
graph LR
    A[API: POST /batches/ingest] --> B[Ingest Items]
    B --> C[Enqueue Pipeline]
    C --> D[Queue: imports_pre]
    D --> E[Task: Preprocess]
    E --> F[Queue: imports_ocr]
    F --> G[Task: OCR]
    G --> H[Queue: imports_ml]
    H --> I[Task: Classify]
    I --> J[Queue: imports_etl]
    J --> K[Task: Extract]
    K --> L[Queue: imports_val]
    L --> M[Task: Validate]
    M --> N[Queue: imports_pub]
    N --> O[Task: Publish]
    O --> P[Destination Tables]
    
    E -->|Error| Q[DLQ]
    G -->|Error| Q
    I -->|Error| Q
    K -->|Error| Q
    M -->|Error| Q
    O -->|Error| Q
    Q --> R[API: POST /batches/retry]
```

## Colas

| Cola | Tarea | Timeout | Concurrency |
|------|-------|---------|-------------|
| imports_pre | Preprocess (antivirus, validación) | 30s | 4 |
| imports_ocr | OCR (photo_utils) | 180s | 2 |
| imports_ml | Classify (doc_type) | 30s | 4 |
| imports_etl | Extract (canónico) | 30s | 4 |
| imports_val | Validate (país) | 30s | 4 |
| imports_pub | Publish (destino) | 30s | 2 |

## Estados de Item

```
pending → preprocessing → preprocessed → ocr_processing → ocr_completed 
  → classifying → classified → extracting → extracted → validating 
  → validated → publishing → published

*_failed (cualquier etapa puede fallar, con retry)
```

## Comandos

### Development (inline mode, sin Celery)
```bash
export IMPORTS_RUNNER_MODE=inline
export IMPORTS_ENABLED=1
python -m uvicorn app.main:app --reload
```

### Production (con Celery + Redis)

**Arrancar Redis:**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Arrancar Worker:**
```bash
export REDIS_URL=redis://localhost:6379/0
export IMPORTS_RUNNER_MODE=celery
export DB_DSN=postgresql://user:pass@localhost:5432/gestiqcloud
cd apps/backend
python -m app.modules.imports.application.worker_main
```

**Arrancar Backend API:**
```bash
export REDIS_URL=redis://localhost:6379/0
export IMPORTS_RUNNER_MODE=celery
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Compose (todo en uno)
```bash
docker-compose up -d redis celery-worker backend
```

### Systemd (producción)
```bash
sudo cp ops/systemd/gestiq-worker-imports.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gestiq-worker-imports
sudo systemctl start gestiq-worker-imports
sudo journalctl -u gestiq-worker-imports -f
```

## Endpoints API

### Ingestar y procesar
```bash
POST /api/v1/imports/batches/{batch_id}/ingest
{
  "rows": [...],
  "mapping_id": "uuid",
  "transforms": {...},
  "defaults": {...}
}

Response:
{
  "batch_id": "uuid",
  "items_ingested": 10,
  "pipeline_enqueued": 10,
  "group_id": "celery-group-id"
}
```

### Consultar progreso
```bash
GET /api/v1/imports/batches/{batch_id}/status

Response:
{
  "batch_id": "uuid",
  "status": "processing",
  "total_items": 10,
  "completed": 7,
  "processing": 2,
  "failed": 1,
  "pending": 0,
  "progress": 70.0,
  "status_breakdown": {
    "published": 7,
    "extracting": 2,
    "ocr_failed": 1
  }
}
```

### Reintentar fallidos
```bash
POST /api/v1/imports/batches/{batch_id}/retry

Response:
{
  "retried": 3,
  "batch_id": "uuid"
}
```

## Monitoring con Flower (opcional)

```bash
pip install flower
celery -A app.modules.imports.application.celery_app flower --port=5555
```

Abrir http://localhost:5555

## Métricas Prometheus

Exponer en `/metrics` endpoint:

- `imports_items_processed_total{tenant_id, doc_type, status}`
- `imports_task_duration_seconds{task_name, tenant_id}`
- `imports_ocr_latency_seconds{tenant_id}`
- `imports_errors_total{task_name, tenant_id, error_type}`

## Tests

```bash
# Unit tests (con mocks)
export IMPORTS_RUNNER_MODE=inline
pytest apps/backend/app/modules/imports/application/tests/test_tasks.py -v

# Integration tests (con test redis)
docker run -d --name test-redis -p 6380:6379 redis:7-alpine
export REDIS_URL=redis://localhost:6380/0
pytest apps/backend/app/modules/imports/application/tests/test_pipeline_integration.py -v
docker stop test-redis && docker rm test-redis
```

## Troubleshooting

### Worker no procesa tareas
1. Verificar Redis: `redis-cli -h localhost ping` → `PONG`
2. Verificar worker logs: `journalctl -u gestiq-worker-imports -f`
3. Revisar colas: `celery -A app.modules.imports.application.celery_app inspect active`

### Items stuck en "processing"
1. Revisar timeout de tasks (default 90s soft, 120s hard)
2. Verificar que worker tiene acceso a DB con RLS: `SET LOCAL app.tenant_id`
3. Revisar logs por errores de permisos o conexión

### Re-encolar manualmente
```python
from app.modules.imports.domain.pipeline import enqueue_item_pipeline
from uuid import UUID

enqueue_item_pipeline(
    item_id=UUID("..."),
    tenant_id=UUID("..."),
    batch_id=UUID("...")
)
```

## Rollout Checklist

- [ ] Redis en producción (persistencia activada)
- [ ] Worker systemd service configurado
- [ ] Métricas exportadas a Prometheus
- [ ] Alertas configuradas (queue depth, error rate)
- [ ] Backfill de items legacy con estado "pending"
- [ ] Feature flag `IMPORTS_ENABLED=1` activado
- [ ] Smoke test: 1 batch end-to-end en staging
- [ ] Rate limits ajustados por tenant
- [ ] DLQ monitoreada con retention de 7 días

## DLQ Strategy

Items que fallan **3 veces** (max_retries) quedan en estado `*_failed`. Estrategias:

1. **Manual Review**: Admin revisa error en UI, corrige metadata, POST `/batches/{id}/retry`
2. **Auto-retry con backoff**: Configurar `task.retry_kwargs` con `countdown` exponencial
3. **Dead Letter Table**: Opcional, tabla `import_dlq` con payload completo para análisis forense

## Render.yaml Blueprint (añadir)

```yaml
- type: worker
  name: gestiq-imports-worker
  runtime: python
  buildCommand: "pip install -r requirements.txt"
  startCommand: "python -m app.modules.imports.application.worker_main"
  envVars:
    - key: REDIS_URL
      fromService:
        type: redis
        name: gestiq-redis
    - key: DB_DSN
      fromDatabase:
        name: gestiqcloud-db
    - key: IMPORTS_RUNNER_MODE
      value: celery
    - key: IMPORTS_ENABLED
      value: "1"
  scaling:
    minInstances: 1
    maxInstances: 4

- type: redis
  name: gestiq-redis
  plan: starter
  ipAllowList: []
```
