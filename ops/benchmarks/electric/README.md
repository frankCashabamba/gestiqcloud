# ElectricSQL Benchmarks

Benchmarks para medir rendimiento de sincronización offline-first con ElectricSQL.

## Objetivos P95

| Métrica | Objetivo | Descripción |
|---------|----------|-------------|
| Sync inicial | < 5s | Full load de 10K registros |
| Sync incremental | < 500ms | Cambios incrementales |
| Shape filter | < 200ms | Filtrado por shapes |

## Requisitos

```bash
pip install -r requirements.txt
```

O desde el directorio raíz del proyecto:

```bash
pip install aiohttp websockets pytest-benchmark
```

## Ejecución

### 1. Generar datos de prueba (100MB dataset)

```bash
python setup.py
```

Esto crea:
- 10,000 productos
- 5,000 clientes
- 20,000 recibos POS

### 2. Ejecutar benchmarks de sincronización

```bash
python benchmark_sync.py
```

Métricas:
- Tiempo de sync inicial (full load)
- Tiempo de sync incremental
- Throughput de operaciones offline

### 3. Ejecutar benchmarks de shapes

```bash
python benchmark_shapes.py
```

Métricas:
- Latencia de shapes con diferentes tamaños de datos
- Rendimiento de filtros por tenant_id
- Rendimiento de filtros por fecha

## Variables de Entorno

```bash
# URL del servidor ElectricSQL
ELECTRIC_URL=ws://localhost:5133

# URL del backend API (para shapes)
API_BASE_URL=http://localhost:8000

# Tenant ID para pruebas
TEST_TENANT_ID=bench_tenant_001
```

## Estructura de Resultados

Los benchmarks generan:
- `results/sync_benchmark.json` - Resultados de sync
- `results/shapes_benchmark.json` - Resultados de shapes
- `results/summary.md` - Resumen legible

## Interpretación de Resultados

### Sync Inicial

```
✅ PASS: < 5s para 10K registros
⚠️  WARN: 5-10s (revisar índices)
❌ FAIL: > 10s (requiere optimización)
```

### Sync Incremental

```
✅ PASS: < 500ms
⚠️  WARN: 500ms-1s (aceptable con latencia de red)
❌ FAIL: > 1s (revisar batching)
```

### Shape Filter

```
✅ PASS: < 200ms
⚠️  WARN: 200-500ms (revisar índices de DB)
❌ FAIL: > 500ms (requiere optimización de queries)
```

## Troubleshooting

### "Connection refused"

Verificar que ElectricSQL está corriendo:
```bash
docker ps | grep electric
```

### "Timeout en sync inicial"

Aumentar timeout o reducir dataset:
```bash
SYNC_TIMEOUT=60 python benchmark_sync.py
```

### Datos de prueba corruptos

Regenerar:
```bash
python setup.py --clean
```
