# Celery/Redis Implementation Summary

## Archivos Creados

### Core Infrastructure
1. **apps/backend/app/modules/imports/application/celery_app.py** - Configuración Celery con 6 colas
2. **apps/backend/app/modules/imports/application/worker_main.py** - Entry point del worker
3. **apps/backend/app/modules/imports/application/metrics.py** - Métricas Prometheus

### Tasks (6 etapas del pipeline)
4. **apps/backend/app/modules/imports/application/tasks/__init__.py**
5. **apps/backend/app/modules/imports/application/tasks/task_preprocess.py** - Antivirus + validación
6. **apps/backend/app/modules/imports/application/tasks/task_ocr.py** - OCR con photo_utils
7. **apps/backend/app/modules/imports/application/tasks/task_classify.py** - Clasificación doc_type
8. **apps/backend/app/modules/imports/application/tasks/task_extract.py** - Extracción canónica
9. **apps/backend/app/modules/imports/application/tasks/task_validate.py** - Validación por país
10. **apps/backend/app/modules/imports/application/tasks/task_publish.py** - Promoción a tablas destino

### Orchestration
11. **apps/backend/app/modules/imports/domain/pipeline.py** - Enqueue chains, retry, DLQ
12. **apps/backend/app/modules/imports/domain/handlers.py** - Función `publish_to_destination()`

### API Updates
13. **apps/backend/app/modules/imports/interface/http/tenant.py** - Actualizados 3 endpoints:
    - `POST /batches/{id}/ingest` → retorna dict con pipeline_enqueued
    - `GET /batches/{id}/status` → progreso (X/N items, breakdown)
    - `POST /batches/{id}/retry` → re-encolar fallidos

### Config & Deployment
14. **docker-compose.yml** - Añadidos servicios `redis` y `celery-worker`
15. **ops/systemd/gestiq-worker-imports.service** - Systemd unit file
16. **requirements-celery.txt** - Dependencies (celery, redis, kombu, flower)
17. **Makefile.imports** - Comandos para dev (redis-start, worker-start, test, etc.)

### Tests
18. **apps/backend/app/modules/imports/application/tests/__init__.py**
19. **apps/backend/app/modules/imports/application/tests/test_tasks.py** - Unit tests con mocks
20. **apps/backend/app/modules/imports/application/tests/test_pipeline_integration.py** - E2E test

### Documentation
21. **apps/backend/app/modules/imports/CELERY_SETUP.md** - Guía completa con diagrama, comandos, troubleshooting

---

## Diagrama de Flujo

```mermaid
sequenceDiagram
    participant API
    participant Redis
    participant Worker
    participant DB
    participant Destination

    API->>DB: POST /batches/ingest (insert items)
    API->>Redis: Enqueue batch pipeline
    
    loop Para cada item
        Redis->>Worker: preprocess task
        Worker->>DB: Update status=preprocessing
        Worker->>DB: Validate file, update status=preprocessed
        
        Worker->>Redis: Chain to ocr task
        Worker->>DB: Update status=ocr_processing
        Worker->>DB: OCR + save result, status=ocr_completed
        
        Worker->>Redis: Chain to classify task
        Worker->>DB: Classify doc_type, status=classified
        
        Worker->>Redis: Chain to extract task
        Worker->>DB: Extract canónico, status=extracted
        
        Worker->>Redis: Chain to validate task
        Worker->>DB: Validate país, status=validated
        
        Worker->>Redis: Chain to publish task
        Worker->>DB: Publish to destination
        Worker->>Destination: Insert into expenses/invoices/bank
        Worker->>DB: Update status=published
    end
    
    API->>DB: GET /batches/{id}/status
    DB-->>API: {completed: X, failed: Y, progress: Z%}
```

---

## Comandos Rápidos

### Development (Inline Mode - Sin Celery)
```bash
export IMPORTS_RUNNER_MODE=inline
export IMPORTS_ENABLED=1
cd apps/backend
uvicorn app.main:app --reload --port 8000
```

### Production (Con Celery + Redis)

**Terminal 1 - Redis:**
```bash
docker run -d --name gestiq-redis -p 6379:6379 redis:7-alpine
```

**Terminal 2 - Worker:**
```bash
export REDIS_URL=redis://localhost:6379/0
export IMPORTS_RUNNER_MODE=celery
export DB_DSN=postgresql://postgres:root@localhost:5432/gestiqclouddb_dev
cd apps/backend
python -m app.modules.imports.application.worker_main
```

**Terminal 3 - API:**
```bash
export REDIS_URL=redis://localhost:6379/0
export IMPORTS_RUNNER_MODE=celery
cd apps/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Compose (Todo en uno)
```bash
docker-compose up -d redis celery-worker backend
docker-compose logs -f celery-worker
```

### Makefile Shortcuts
```bash
make -f Makefile.imports redis-start
make -f Makefile.imports worker-start
make -f Makefile.imports api-start
make -f Makefile.imports flower  # UI monitoring en http://localhost:5555
```

---

## Variables de Entorno Clave

| Variable | Valor Dev | Valor Prod | Descripción |
|----------|-----------|------------|-------------|
| `IMPORTS_RUNNER_MODE` | `inline` | `celery` | Modo de ejecución (inline=sync, celery=async) |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://prod:6379/0` | Broker Celery |
| `IMPORTS_ENABLED` | `1` | `1` | Feature flag global |
| `DB_DSN` | `postgresql://...` | `postgresql://...` | Connection string |
| `IMPORTS_MAX_ITEMS_PER_BATCH` | `5000` | `5000` | Límite de items por batch |
| `IMPORTS_MAX_INGESTS_PER_MIN` | `30` | `100` | Rate limit por tenant |

---

## Testing

### Unit Tests (con mocks)
```bash
export IMPORTS_RUNNER_MODE=inline
cd apps/backend
pytest app/modules/imports/application/tests/test_tasks.py -v
```

### Integration Tests (con test redis)
```bash
make -f Makefile.imports test-integration
```

---

## Monitoring

### Flower UI (Celery tasks dashboard)
```bash
pip install flower
celery -A app.modules.imports.application.celery_app flower --port=5555
# Abrir http://localhost:5555
```

### Métricas Prometheus
Expuestas en endpoint `/metrics`:
- `imports_items_processed_total{tenant_id, doc_type, status}`
- `imports_task_duration_seconds{task_name, tenant_id}`
- `imports_ocr_latency_seconds{tenant_id}`
- `imports_errors_total{task_name, tenant_id, error_type}`

### Inspeccionar colas manualmente
```bash
celery -A app.modules.imports.application.celery_app inspect active
celery -A app.modules.imports.application.celery_app inspect stats
celery -A app.modules.imports.application.celery_app purge  # Vaciar todas las colas (CUIDADO)
```

---

## Rollout Checklist

- [ ] Instalar dependencies: `pip install -r requirements-celery.txt`
- [ ] Redis en producción con persistencia (AOF o RDB)
- [ ] Systemd service configurado y enabled
- [ ] Worker logs monitoreados (journalctl)
- [ ] Alertas configuradas (Prometheus/Grafana):
  - Queue depth > 1000
  - Error rate > 5%
  - Task latency p95 > 60s
- [ ] Rate limits ajustados por tenant
- [ ] Feature flag `IMPORTS_ENABLED=1` activado
- [ ] Smoke test con 1 batch end-to-end en staging
- [ ] Backfill de items legacy con estado "pending"

---

## DLQ & Retry Strategy

Items que fallan **3 veces** (max_retries) quedan en estado `*_failed`:

1. **Manual Review**: Admin consulta error en `GET /batches/{id}/status`, corrige metadata del item, `POST /batches/{id}/retry`
2. **Auto-retry con backoff**: Backoff exponencial hasta 600s (10min)
3. **Dead Letter Monitoring**: Alertas cuando `failed` > 10% del batch

---

## Limitaciones & TODOs

- [ ] Tenant context middleware: Verificar que `SET LOCAL app.tenant_id` se aplica en worker session
- [ ] Idempotencia: Actualmente tasks permiten re-run (item status check), pero ideal agregar `task_id` a metadata
- [ ] DLQ Table: Opcional `import_dlq` para análisis forense de payloads fallidos
- [ ] Rate limiting por tenant: Implementar `redis_rate_limit` con sliding window
- [ ] Publish handlers: Reemplazar skeletons por inserts reales a domain models (Invoice, BankTransaction, etc.)
- [ ] Scaling: Considerar workers especializados (1 worker para OCR, otro para classify/extract)

---

## Render.yaml Blueprint (añadir)

```yaml
services:
  - type: redis
    name: gestiq-redis
    plan: starter
    ipAllowList: []
    
  - type: worker
    name: gestiq-imports-worker
    runtime: python
    buildCommand: "pip install -r requirements.txt -r requirements-celery.txt"
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
      targetMemoryPercent: 80
      targetCPUPercent: 70
```

---

## Troubleshooting

### Worker no inicia
- Verificar logs: `journalctl -u gestiq-worker-imports -f`
- Revisar imports: `python -c "from app.modules.imports.application.celery_app import celery_app; print(celery_app)"`

### Tasks no se ejecutan
- Ping Redis: `redis-cli -h localhost ping` → `PONG`
- Revisar colas: `celery -A app.modules.imports.application.celery_app inspect active_queues`
- Verificar routing: Task name debe match con `task_routes` en celery_app.py

### Items stuck en processing
- Revisar timeouts (default soft=90s, hard=120s; OCR=180s)
- Worker tiene permisos DB?: `SELECT current_setting('app.tenant_id', true)`
- Logs por OOM o network errors

### Performance degradation
- Escalar workers: `minInstances: 2` en Render
- Aumentar `worker_prefetch_multiplier` (default=1) si tasks son rápidas
- Separar colas: worker dedicado para `imports_ocr` con concurrency=2

---

**Fin del resumen. Ver CELERY_SETUP.md para detalles completos.**
