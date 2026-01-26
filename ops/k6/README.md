# K6 Load Testing Suite

Suite de pruebas de carga para GestiqCloud usando [k6](https://k6.io/).

## Requisitos

- [k6](https://k6.io/docs/getting-started/installation/) instalado

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

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `BASE_URL` | URL base del API | `http://localhost:8000` |
| `TEST_USER_EMAIL` | Email para tests de autenticación | - |
| `TEST_USER_PASSWORD` | Password para tests de autenticación | - |

## Escenarios Disponibles

### 1. Smoke Test (`scenarios/smoke.js`)
Test básico de salud del sistema.

```bash
k6 run scenarios/smoke.js
```

### 2. Auth Test (`scenarios/auth.js`)
Test de endpoints de autenticación.

```bash
k6 run scenarios/auth.js
```

### 3. API Load Test (`scenarios/api-load.js`)
Test de carga multi-endpoint (productos, ventas, clientes).

```bash
k6 run scenarios/api-load.js
```

## Uso

### Ejecución básica
```bash
cd ops/k6
k6 run scenarios/smoke.js
```

### Con variables de entorno
```bash
k6 run -e BASE_URL=https://api.gestiqcloud.com -e TEST_USER_EMAIL=test@example.com -e TEST_USER_PASSWORD=secret scenarios/auth.js
```

### Con más VUs y duración
```bash
k6 run --vus 50 --duration 5m scenarios/api-load.js
```

### Exportar resultados a JSON
```bash
k6 run --out json=results.json scenarios/smoke.js
```

### Exportar métricas a InfluxDB
```bash
k6 run --out influxdb=http://localhost:8086/k6 scenarios/api-load.js
```

## Thresholds

Los tests están configurados con los siguientes umbrales:

| Métrica | Umbral | Descripción |
|---------|--------|-------------|
| `http_req_duration` (p95) | < 500ms | 95% de requests bajo 500ms |
| `http_req_failed` | < 1% | Tasa de error menor al 1% |
| `http_reqs` | > 100/s | Throughput mínimo |

## Estructura

```
ops/k6/
├── README.md           # Este archivo
├── config.js           # Configuración base compartida
└── scenarios/
    ├── smoke.js        # Test de salud
    ├── auth.js         # Test de autenticación
    └── api-load.js     # Test de carga multi-endpoint
```
