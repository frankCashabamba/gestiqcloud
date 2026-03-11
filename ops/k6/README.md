# K6 Load Testing Suite

Load testing suite for GestiqCloud using [k6](https://k6.io/).

## Requirements

- [k6](https://k6.io/docs/getting-started/installation/) installed

```bash
# Windows (chocolatey)
choco install k6

# macOS
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Base API URL | `http://localhost:8000` |
| `TEST_USER_EMAIL` | Email used by authentication tests | - |
| `TEST_USER_PASSWORD` | Password used by authentication tests | - |

## Available Scenarios

### 1. Smoke Test (`scenarios/smoke.js`)
Basic system health check.

```bash
k6 run scenarios/smoke.js
```

### 2. Auth Test (`scenarios/auth.js`)
Authentication endpoint test.

```bash
k6 run scenarios/auth.js
```

### 3. API Load Test (`scenarios/api-load.js`)
Multi-endpoint load test covering products, sales, and clients.

```bash
k6 run scenarios/api-load.js
```

## Usage

### Basic Execution
```bash
cd ops/k6
k6 run scenarios/smoke.js
```

### With Environment Variables
```bash
k6 run -e BASE_URL=https://api.gestiqcloud.com -e TEST_USER_EMAIL=test@example.com -e TEST_USER_PASSWORD=secret scenarios/auth.js
```

### With More VUs And Duration
```bash
k6 run --vus 50 --duration 5m scenarios/api-load.js
```

### Export Results To JSON
```bash
k6 run --out json=results.json scenarios/smoke.js
```

### Export Metrics To InfluxDB
```bash
k6 run --out influxdb=http://localhost:8086/k6 scenarios/api-load.js
```

## Thresholds

The tests are configured with the following thresholds:

| Metric | Threshold | Description |
|---------|--------|-------------|
| `http_req_duration` (p95) | < 500ms | 95% of requests under 500ms |
| `http_req_failed` | < 1% | Error rate below 1% |
| `http_reqs` | > 100/s | Minimum throughput |

## Structure

```
ops/k6/
├── README.md           # This file
├── config.js           # Shared base configuration
└── scenarios/
    ├── smoke.js        # Health check
    ├── auth.js         # Authentication test
    └── api-load.js     # Multi-endpoint load test
```
