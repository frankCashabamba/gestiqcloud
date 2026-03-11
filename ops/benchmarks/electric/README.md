# ElectricSQL Benchmarks

Benchmarks used to measure offline-first synchronization performance with ElectricSQL.

## P95 Targets

| Metric | Target | Description |
|---------|----------|-------------|
| Initial sync | < 5s | Full load of 10K records |
| Incremental sync | < 500ms | Incremental changes |
| Shape filter | < 200ms | Shape-based filtering |

## Requirements

```bash
pip install -r requirements.txt
```

Or from the project root:

```bash
pip install aiohttp websockets pytest-benchmark
```

## Execution

### 1. Generate test data (100MB dataset)

```bash
python setup.py
```

This creates:
- 10,000 products
- 5,000 clients
- 20,000 POS receipts

### 2. Run sync benchmarks

```bash
python benchmark_sync.py
```

Metrics:
- Initial sync time (full load)
- Incremental sync time
- Offline operations throughput

### 3. Run shape benchmarks

```bash
python benchmark_shapes.py
```

Metrics:
- Shape latency across different data sizes
- Filter performance by `tenant_id`
- Filter performance by date

## Environment Variables

```bash
# ElectricSQL server URL
ELECTRIC_URL=ws://localhost:5133

# Backend API URL (for shapes)
API_BASE_URL=http://localhost:8000

# Tenant ID used for tests
TEST_TENANT_ID=bench_tenant_001
```

## Result Structure

The benchmarks generate:
- `results/sync_benchmark.json` - sync benchmark results
- `results/shapes_benchmark.json` - shape benchmark results
- `results/summary.md` - human-readable summary

## Result Interpretation

### Initial Sync

```
PASS: < 5s for 10K records
WARN: 5-10s (review indexes)
FAIL: > 10s (needs optimization)
```

### Incremental Sync

```
✅ PASS: < 500ms
WARN: 500ms-1s (acceptable with network latency)
FAIL: > 1s (review batching)
```

### Shape Filter

```
✅ PASS: < 200ms
WARN: 200-500ms (review DB indexes)
FAIL: > 500ms (query optimization required)
```

## Troubleshooting

### "Connection refused"

Verify that ElectricSQL is running:
```bash
docker ps | grep electric
```

### "Initial sync timeout"

Increase the timeout or reduce the dataset:
```bash
SYNC_TIMEOUT=60 python benchmark_sync.py
```

### Corrupted test data

Regenerate:
```bash
python setup.py --clean
```
