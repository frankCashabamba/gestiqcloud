# OCR Worker Monitoring

Este documento describe el sistema de monitoreo para el worker de OCR de GestiqCloud.

## Endpoints

### GET /api/v1/imports/ocr/metrics

Retorna métricas globales del sistema OCR.

**Autenticación:** Requiere token con scope `tenant`.

**Ejemplo de respuesta:**

```json
{
  "timestamp": "2026-01-17T12:00:00.000Z",
  "queue": {
    "pending": 5,
    "running": 2,
    "done": 1250,
    "failed": 12,
    "total": 1269,
    "oldest_pending_age_seconds": 45.0,
    "avg_wait_time_seconds": 3.25
  },
  "processing_times": {
    "p50_ms": 850.5,
    "p95_ms": 2340.0,
    "p99_ms": 4500.0
  },
  "rates": {
    "success_rate": 0.9904,
    "error_rate": 0.0096,
    "jobs_per_minute": 8.5
  },
  "totals": {
    "total_processed": 15420,
    "total_failed": 148,
    "uptime_seconds": 86400
  },
  "health": {
    "queue_healthy": true,
    "error_rate_healthy": true,
    "backlog_age_healthy": true
  }
}
```

### GET /api/v1/imports/ocr/metrics/tenant

Retorna métricas específicas del tenant actual.

**Ejemplo de respuesta:**

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-17T12:00:00.000Z",
  "all_time": {
    "pending": 2,
    "running": 1,
    "done": 450,
    "failed": 3
  },
  "last_24h": {
    "pending": 2,
    "running": 1,
    "done": 85,
    "failed": 1
  }
}
```

## Métricas Disponibles

### Queue Metrics (Estado de la Cola)

| Métrica | Descripción |
|---------|-------------|
| `pending` | Jobs esperando ser procesados |
| `running` | Jobs actualmente en procesamiento |
| `done` | Jobs completados exitosamente |
| `failed` | Jobs que fallaron |
| `total` | Total de jobs en el sistema |
| `oldest_pending_age_seconds` | Edad del job pendiente más antiguo |
| `avg_wait_time_seconds` | Tiempo promedio de espera (últimas 24h) |

### Processing Times (Tiempos de Procesamiento)

| Métrica | Descripción |
|---------|-------------|
| `p50_ms` | Percentil 50 (mediana) del tiempo de procesamiento |
| `p95_ms` | Percentil 95 del tiempo de procesamiento |
| `p99_ms` | Percentil 99 del tiempo de procesamiento |

Los percentiles se calculan sobre una ventana deslizante de los últimos 1000 jobs o 1 hora.

### Rate Metrics (Tasas)

| Métrica | Descripción |
|---------|-------------|
| `success_rate` | Proporción de jobs exitosos (0.0-1.0) |
| `error_rate` | Proporción de jobs fallidos (0.0-1.0) |
| `jobs_per_minute` | Throughput actual |

### Total Metrics (Acumulados)

| Métrica | Descripción |
|---------|-------------|
| `total_processed` | Total de jobs procesados desde inicio del worker |
| `total_failed` | Total de jobs fallidos desde inicio del worker |
| `uptime_seconds` | Tiempo desde que se inició el collector |

### Health Indicators

| Indicador | Condición Saludable |
|-----------|---------------------|
| `queue_healthy` | `pending < 100` |
| `error_rate_healthy` | `error_rate < 0.1` (10%) |
| `backlog_age_healthy` | `oldest_pending_age < 300s` (5 min) |

## Interpretación de Datos

### Cola Saludable

- **pending < 10**: Excelente, procesamiento en tiempo real
- **pending 10-50**: Normal bajo carga moderada
- **pending 50-100**: Alta carga, considerar escalar workers
- **pending > 100**: Backlog crítico, escalar inmediatamente

### Tiempos de Procesamiento

- **p50 < 1s**: Excelente para documentos simples
- **p95 < 5s**: Aceptable para la mayoría de PDFs
- **p99 < 10s**: Documentos complejos o multipágina
- **p99 > 15s**: Posibles problemas de rendimiento

### Tasas de Error

- **< 1%**: Excelente
- **1-5%**: Aceptable, revisar logs de errores
- **5-10%**: Preocupante, investigar causas
- **> 10%**: Crítico, acción inmediata requerida

## Alertas Recomendadas

### Críticas (P1)

```yaml
- alert: OCRQueueBacklogCritical
  expr: ocr_queue_pending > 200
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "OCR queue backlog crítico"
    description: "Más de 200 jobs pendientes por más de 5 minutos"

- alert: OCRErrorRateCritical
  expr: ocr_error_rate > 0.15
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Tasa de error OCR crítica"
    description: "Error rate > 15% sostenido"
```

### Altas (P2)

```yaml
- alert: OCRQueueBacklogHigh
  expr: ocr_queue_pending > 100
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "OCR queue backlog alto"

- alert: OCRProcessingTimeSlow
  expr: ocr_p95_ms > 10000
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Tiempos de procesamiento OCR elevados"

- alert: OCROldestJobStale
  expr: ocr_oldest_pending_age_seconds > 600
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Job OCR pendiente por más de 10 minutos"
```

### Medias (P3)

```yaml
- alert: OCRErrorRateElevated
  expr: ocr_error_rate > 0.05
  for: 30m
  labels:
    severity: info
  annotations:
    summary: "Tasa de error OCR elevada"

- alert: OCRThroughputLow
  expr: ocr_jobs_per_minute < 1 AND ocr_queue_pending > 10
  for: 15m
  labels:
    severity: info
  annotations:
    summary: "Throughput OCR bajo con cola pendiente"
```

## Integración con Prometheus

Para exponer métricas en formato Prometheus, puedes crear un endpoint adicional:

```python
from prometheus_client import Counter, Gauge, Histogram

ocr_jobs_total = Counter('ocr_jobs_total', 'Total OCR jobs', ['status'])
ocr_queue_size = Gauge('ocr_queue_size', 'Current queue size', ['status'])
ocr_processing_duration = Histogram('ocr_processing_seconds', 'OCR processing time')
```

## Integración con Grafana

Ejemplo de queries para dashboard:

```promql
# Cola pendiente
ocr_queue_size{status="pending"}

# Tasa de éxito (últimos 5 min)
rate(ocr_jobs_total{status="done"}[5m]) /
rate(ocr_jobs_total[5m])

# P95 de tiempo de procesamiento
histogram_quantile(0.95, rate(ocr_processing_seconds_bucket[5m]))
```

## Logs Relacionados

Los logs del worker OCR usan el logger `imports.ocr_jobs`:

```bash
# Ver logs en tiempo real
tail -f /var/log/gestiq/worker.log | grep ocr_jobs

# Filtrar errores
grep -i "failed.*ocr" /var/log/gestiq/worker.log
```

## Troubleshooting

### Cola crece sin procesar

1. Verificar que el worker está corriendo:
   ```bash
   systemctl status gestiq-worker-imports
   ```

2. Verificar conexión a Redis:
   ```bash
   redis-cli ping
   ```

3. Revisar logs por errores de conexión a DB

### Alta tasa de errores

1. Revisar tipos de documentos que fallan:
   ```sql
   SELECT filename, error, COUNT(*)
   FROM import_ocr_jobs
   WHERE status = 'failed'
     AND created_at > NOW() - INTERVAL '1 hour'
   GROUP BY filename, error;
   ```

2. Verificar memoria disponible (EasyOCR consume mucha RAM)

3. Revisar timeout de procesamiento

### Tiempos de procesamiento altos

1. Verificar tamaño de documentos
2. Revisar configuración de `IMPORTS_OCR_WORKERS`
3. Considerar escalar horizontalmente
