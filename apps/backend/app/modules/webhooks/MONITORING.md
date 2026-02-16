# Webhook Monitoring Guide

## Prometheus Metrics Overview

All webhook deliveries are automatically tracked via Prometheus metrics.

---

## 1. Metrics Collection

### Automatic Metrics

Metrics are recorded automatically in `apps/backend/app/modules/webhooks/tasks.py`:

1. **When delivery starts:** Status recorded in `webhook_deliveries_total`
2. **When delivery completes:** Duration recorded in `webhook_delivery_duration_seconds`
3. **When retrying:** Reason recorded in `webhook_retries_total`
4. **HTTP responses:** Status code recorded in `webhook_delivery_http_status`

### Example Metrics Output

```
# HELP webhook_deliveries_total Total webhook deliveries by event and status
# TYPE webhook_deliveries_total counter
webhook_deliveries_total{event="invoice.created",status="delivered",tenant_id="abc123"} 145
webhook_deliveries_total{event="invoice.created",status="failed",tenant_id="abc123"} 3
webhook_deliveries_total{event="payment.received",status="delivered",tenant_id="abc123"} 47

# HELP webhook_delivery_duration_seconds Webhook delivery duration in seconds
# TYPE webhook_delivery_duration_seconds histogram
webhook_delivery_duration_seconds_bucket{event="invoice.created",tenant_id="abc123",le="0.1"} 120
webhook_delivery_duration_seconds_bucket{event="invoice.created",tenant_id="abc123",le="0.5"} 140
webhook_delivery_duration_seconds_bucket{event="invoice.created",tenant_id="abc123",le="1.0"} 144
webhook_delivery_duration_seconds_sum{event="invoice.created",tenant_id="abc123"} 98.45
webhook_delivery_duration_seconds_count{event="invoice.created",tenant_id="abc123"} 145

# HELP webhook_retries_total Total webhook retry attempts
# TYPE webhook_retries_total counter
webhook_retries_total{event="invoice.created",reason="timeout",tenant_id="abc123"} 2
webhook_retries_total{event="invoice.created",reason="server_error",tenant_id="abc123"} 5
webhook_retries_total{event="payment.received",reason="connection_error",tenant_id="abc123"} 1

# HELP webhook_delivery_http_status HTTP status codes from webhook deliveries
# TYPE webhook_delivery_http_status counter
webhook_delivery_http_status{event="invoice.created",status_code="200"} 130
webhook_delivery_http_status{event="invoice.created",status_code="202"} 15
webhook_delivery_http_status{event="invoice.created",status_code="500"} 5
webhook_delivery_http_status{event="invoice.created",status_code="503"} 1
```

---

## 2. Key Queries

### Success Rate by Event

```promql
sum(rate(webhook_deliveries_total{status="delivered"}[5m])) by (event)
/
sum(rate(webhook_deliveries_total[5m])) by (event)
```

### Failure Rate by Event

```promql
sum(rate(webhook_deliveries_total{status="failed"}[5m])) by (event)
/
sum(rate(webhook_deliveries_total[5m])) by (event)
```

### Average Delivery Time by Event

```promql
histogram_quantile(0.95,
  sum(rate(webhook_delivery_duration_seconds_bucket[5m])) by (event, le)
)
```

### Retry Rate

```promql
sum(rate(webhook_retries_total[5m])) by (event, reason)
```

### P99 Delivery Time

```promql
histogram_quantile(0.99,
  sum(rate(webhook_delivery_duration_seconds_bucket[5m])) by (le)
)
```

### Failed Deliveries Last Hour

```promql
sum(increase(webhook_deliveries_total{status="failed"}[1h])) by (event)
```

### HTTP Status Distribution

```promql
sum(rate(webhook_delivery_http_status[5m])) by (status_code)
```

---

## 3. Grafana Dashboard

### Dashboard JSON

Create a new Grafana dashboard and add these panels:

```json
{
  "title": "Webhook Monitoring",
  "panels": [
    {
      "title": "Delivery Success Rate",
      "targets": [{
        "expr": "sum(rate(webhook_deliveries_total{status=\"delivered\"}[5m])) by (event) / sum(rate(webhook_deliveries_total[5m])) by (event)"
      }],
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1
        }
      }
    },
    {
      "title": "Deliveries by Status",
      "targets": [{
        "expr": "sum(rate(webhook_deliveries_total[5m])) by (status)"
      }],
      "type": "piechart"
    },
    {
      "title": "Delivery Duration (95th percentile)",
      "targets": [{
        "expr": "histogram_quantile(0.95, sum(rate(webhook_delivery_duration_seconds_bucket[5m])) by (event, le))"
      }],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        }
      }
    },
    {
      "title": "Retry Reasons",
      "targets": [{
        "expr": "sum(rate(webhook_retries_total[5m])) by (reason)"
      }],
      "type": "barchart"
    },
    {
      "title": "HTTP Status Codes",
      "targets": [{
        "expr": "sum(rate(webhook_delivery_http_status[5m])) by (status_code)"
      }],
      "type": "barchart"
    },
    {
      "title": "Failed Deliveries (24h)",
      "targets": [{
        "expr": "sum(increase(webhook_deliveries_total{status=\"failed\"}[24h])) by (event)"
      }],
      "type": "stat"
    }
  ]
}
```

---

## 4. Alert Rules

### High Failure Rate

```yaml
groups:
  - name: webhook_alerts
    interval: 1m
    rules:
      - alert: WebhookHighFailureRate
        expr: |
          (sum(rate(webhook_deliveries_total{status="failed"}[5m])) by (event)
           /
           sum(rate(webhook_deliveries_total[5m])) by (event))
          > 0.1
        for: 5m
        labels:
          severity: warning
          service: webhooks
        annotations:
          summary: "High webhook failure rate for {{ $labels.event }}"
          description: |
            {{ $labels.event }} has >10% failure rate
            Current rate: {{ $value | humanizePercentage }}
          runbook: "https://docs.example.com/webhooks/troubleshooting"
```

### High Retry Count

```yaml
- alert: WebhookHighRetryRate
  expr: |
    sum(rate(webhook_retries_total[5m])) by (event)
    > 5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High webhook retry rate for {{ $labels.event }}"
    description: |
      {{ $labels.event }} is being retried frequently
      Retries per minute: {{ $value | humanize }}
```

### Slow Deliveries

```yaml
- alert: WebhookSlowDeliveries
  expr: |
    histogram_quantile(0.99,
      sum(rate(webhook_delivery_duration_seconds_bucket[5m])) by (event, le)
    )
    > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Slow webhook deliveries for {{ $labels.event }}"
    description: |
      P99 delivery time: {{ $value | humanizeDuration }}
```

### No Deliveries in Period

```yaml
- alert: WebhookNoDeliveries
  expr: |
    increase(webhook_deliveries_total[1h]) == 0
    and on(event) (
      increase(webhook_deliveries_total[24h]) > 0
    )
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "No webhook deliveries for {{ $labels.event }} in last hour"
    description: |
      Expected deliveries but none were recorded
      Check webhook subscriptions and triggers
```

---

## 5. Troubleshooting Queries

### Find Failed Deliveries

```sql
SELECT id, event, target_url, status, last_error, created_at
FROM webhook_deliveries
WHERE status = 'FAILED'
ORDER BY created_at DESC
LIMIT 100;
```

### Find Slow Deliveries

```sql
SELECT id, event, target_url, attempts, created_at, updated_at,
  EXTRACT(EPOCH FROM (updated_at - created_at)) as duration_seconds
FROM webhook_deliveries
WHERE status = 'DELIVERED'
  AND (updated_at - created_at) > interval '5 seconds'
ORDER BY (updated_at - created_at) DESC
LIMIT 50;
```

### Find Hung Deliveries

```sql
SELECT id, event, target_url, status, attempts, created_at,
  NOW() - created_at as age
FROM webhook_deliveries
WHERE status = 'PENDING'
  AND attempts < 3
  AND NOW() - created_at > interval '1 hour'
ORDER BY created_at ASC;
```

### Event Count by Status

```sql
SELECT event, status, COUNT(*) as count
FROM webhook_deliveries
WHERE created_at > NOW() - interval '24 hours'
GROUP BY event, status
ORDER BY event, status;
```

### Delivery Rate by Event

```sql
SELECT 
  event,
  COUNT(*) as total_deliveries,
  SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) as delivered,
  SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
  ROUND(
    100.0 * SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) / COUNT(*),
    2
  ) as success_rate_percent
FROM webhook_deliveries
WHERE created_at > NOW() - interval '24 hours'
GROUP BY event
ORDER BY event;
```

---

## 6. Performance Benchmarks

### Target SLAs

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Success Rate | >99.5% | <99% | <95% |
| P95 Latency | <500ms | >1s | >5s |
| P99 Latency | <1s | >2s | >10s |
| Retry Rate | <1% | >5% | >10% |
| Failure Rate | <0.5% | >1% | >5% |

### Example Healthy State (24h)

```
invoice.created:
  - Total: 10,000
  - Delivered: 9,990 (99.9%)
  - Failed: 10 (0.1%)
  - P95 Latency: 280ms
  - Retries: 45 (0.45%)
  - Retry Reasons: [timeout: 25, server_error: 15, connection_error: 5]

payment.received:
  - Total: 5,000
  - Delivered: 4,995 (99.9%)
  - Failed: 5 (0.1%)
  - P95 Latency: 320ms
  - Retries: 20 (0.4%)
```

---

## 7. Webhook Testing

### Test Delivery Manually

```python
# In Python
import requests
import json
from datetime import datetime

webhook_url = "https://webhook.site/your-unique-id"
payload = {
    "event": "invoice.created",
    "resource_type": "invoice",
    "resource_id": "inv-123",
    "timestamp": datetime.utcnow().isoformat(),
    "data": {
        "invoice_id": "inv-123",
        "invoice_number": "INV-2024-001",
        "amount": "1500.00",
        "currency": "USD"
    },
    "metadata": {
        "tenant_id": "test-tenant",
        "source": "gestiqcloud"
    }
}

response = requests.post(
    webhook_url,
    json=payload,
    headers={
        "X-Event": "invoice.created",
        "Content-Type": "application/json",
        "User-Agent": "GestiqCloud-Webhooks/1.0"
    },
    timeout=10
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

### Load Test

```bash
# Using Apache Bench
ab -n 1000 -c 10 -p payload.json \
  -H "Content-Type: application/json" \
  https://your-webhook-endpoint

# Using wrk (more modern)
wrk -t4 -c100 -d60s \
  -s script.lua \
  https://your-webhook-endpoint
```

---

## 8. Celery Worker Monitoring

### Check Worker Status

```bash
# Using celery CLI
celery -A app.celery_app inspect active

# See queue sizes
celery -A app.celery_app inspect reserved

# Monitor in real-time
celery -A app.celery_app events
```

### Worker Health

```bash
# Check if workers are alive
celery -A app.celery_app inspect ping

# Get worker stats
celery -A app.celery_app inspect stats
```

---

**Last Updated:** 2024-02-14
**Version:** 1.0.0
