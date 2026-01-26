# ElectricSQL Benchmarks - Documentación

Esta documentación describe cómo ejecutar, interpretar y optimizar los benchmarks de ElectricSQL para la sincronización offline-first.

## Ubicación

```
ops/benchmarks/electric/
├── README.md           # Instrucciones rápidas
├── setup.py            # Generador de datos de prueba
├── benchmark_sync.py   # Benchmarks de sincronización
├── benchmark_shapes.py # Benchmarks de shapes/filtros
├── requirements.txt    # Dependencias
├── test_data/          # Datos generados (ignorar en git)
└── results/            # Resultados de benchmarks
```

## Objetivos P95

| Métrica | Objetivo | Justificación |
|---------|----------|---------------|
| **Sync inicial** | < 5s | UX aceptable para carga inicial de 10K registros |
| **Sync incremental** | < 500ms | Latencia imperceptible para el usuario |
| **Shape filter** | < 200ms | Respuesta instantánea para filtros |

## Ejecución de Benchmarks

### 1. Preparación

```bash
cd ops/benchmarks/electric

# Instalar dependencias
pip install -r requirements.txt

# Generar dataset de prueba (~100MB)
python setup.py
```

### 2. Ejecutar Benchmarks

```bash
# Benchmarks de sincronización
python benchmark_sync.py

# Benchmarks de shapes
python benchmark_shapes.py
```

### 3. Variables de Entorno

```bash
# URL del servidor ElectricSQL (producción/staging)
export ELECTRIC_URL=ws://electric.internal:3000

# URL del backend API
export API_BASE_URL=http://localhost:8000

# Tenant para pruebas
export TEST_TENANT_ID=bench_tenant_001

# Timeout de sync (segundos)
export SYNC_TIMEOUT=60
```

## Interpretación de Resultados

### Sync Inicial

```
✅ PASS: P95 < 5s
   El sistema sincroniza 10K registros dentro del objetivo.
   
⚠️  WARN: 5s < P95 < 10s
   Revisar:
   - Índices de base de datos
   - Tamaño de batch de sync
   - Latencia de red
   
❌ FAIL: P95 > 10s
   Requiere optimización urgente:
   - Reducir tamaño de payload inicial
   - Implementar paginación
   - Usar sync parcial por shapes
```

### Sync Incremental

```
✅ PASS: P95 < 500ms
   Cambios se sincronizan de forma imperceptible.
   
⚠️  WARN: 500ms < P95 < 1s
   Aceptable con latencia de red alta.
   Considerar batching de cambios.
   
❌ FAIL: P95 > 1s
   Revisar:
   - Debouncing de operaciones
   - Tamaño de changeset
   - Conexión WebSocket
```

### Shape Filter

```
✅ PASS: P95 < 200ms
   Filtros responden instantáneamente.
   
⚠️  WARN: 200ms < P95 < 500ms
   Revisar índices en columnas filtradas:
   - tenant_id
   - created_at
   - category
   
❌ FAIL: P95 > 500ms
   Requiere:
   - Índices compuestos
   - Particionamiento de datos
   - Reducir tamaño de shape
```

## Recomendaciones de Optimización

### 1. Sync Inicial Lento

```sql
-- Crear índices para shapes
CREATE INDEX idx_products_tenant ON products(tenant_id);
CREATE INDEX idx_receipts_tenant_date ON pos_receipts(tenant_id, created_at);
```

```typescript
// Reducir datos iniciales con shapes
const shapes = {
  products: { 
    where: `tenant_id = '${tenantId}' AND is_active = true`,
    limit: 1000  // Cargar solo activos
  }
};
```

### 2. Sync Incremental Lento

```typescript
// Implementar debouncing
const syncQueue: Change[] = [];
let syncTimeout: number;

function queueSync(change: Change) {
  syncQueue.push(change);
  clearTimeout(syncTimeout);
  syncTimeout = setTimeout(() => {
    electric.sync(syncQueue);
    syncQueue.length = 0;
  }, 100);  // Batch cada 100ms
}
```

### 3. Shapes Lentos

```typescript
// Usar shapes más específicos
const receiptShape = {
  table: 'pos_receipts',
  where: `
    tenant_id = '${tenantId}' 
    AND created_at > NOW() - INTERVAL '30 days'
    AND status = 'completed'
  `,
  columns: ['id', 'receipt_number', 'total', 'created_at']  // Solo columnas necesarias
};
```

### 4. Optimización de Red

```typescript
// Habilitar compresión
const electric = await electrify(db, ELECTRIC_URL, {
  compression: true,
  batchSize: 100,
  reconnectDelay: 1000,
});
```

## Arquitectura de Shapes

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  ElectricSQL    │────▶│   PostgreSQL    │
│   (PGlite)      │◀────│   Server        │◀────│   (Backend)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │   Shape Subscribe     │   CDC Stream          │
        │   ───────────────▶    │   ◀───────────────    │
        │                       │                       │
        │   Filtered Data       │   Changes             │
        │   ◀───────────────    │   ───────────────▶    │
        │                       │                       │
```

### Flujo de Datos

1. **Initial Sync**: Frontend solicita shape → Electric filtra → Envía datos
2. **Incremental Sync**: Backend modifica → CDC captura → Electric notifica → Frontend actualiza
3. **Offline Write**: Frontend escribe local → Cuando online → Sync al backend

## Métricas de Producción

### Dashboards Recomendados

```yaml
# Prometheus/Grafana queries
electric_sync_duration_seconds:
  - quantile: 0.95
  - labels: [tenant_id, sync_type]

electric_shape_latency_ms:
  - quantile: 0.95
  - labels: [shape_name, filter_type]

electric_offline_operations_total:
  - rate: 1m
  - labels: [operation_type]
```

### Alertas

```yaml
alerts:
  - name: ElectricSyncSlow
    condition: electric_sync_duration_p95 > 10s
    severity: warning
    
  - name: ElectricShapeSlow
    condition: electric_shape_latency_p95 > 500ms
    severity: warning
    
  - name: ElectricOfflineQueueHigh
    condition: electric_offline_queue_size > 1000
    severity: critical
```

## CI/CD Integration

### GitHub Actions

```yaml
name: ElectricSQL Benchmarks

on:
  schedule:
    - cron: '0 2 * * 1'  # Lunes 2am

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install deps
        run: pip install -r ops/benchmarks/electric/requirements.txt
        
      - name: Generate test data
        run: python ops/benchmarks/electric/setup.py
        
      - name: Run sync benchmarks
        run: python ops/benchmarks/electric/benchmark_sync.py
        
      - name: Run shape benchmarks
        run: python ops/benchmarks/electric/benchmark_shapes.py
        
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: ops/benchmarks/electric/results/
```

## Troubleshooting

### "Connection refused" a ElectricSQL

```bash
# Verificar que Electric está corriendo
docker ps | grep electric

# Verificar puerto
netstat -an | grep 5133

# Logs de Electric
docker logs electric-sql
```

### Resultados inconsistentes

```bash
# Limpiar y regenerar datos
python setup.py --clean

# Aumentar iteraciones para mayor precisión
NUM_ITERATIONS=50 python benchmark_sync.py
```

### Out of Memory en dataset grande

```bash
# Reducir dataset
NUM_PRODUCTS=5000 NUM_RECEIPTS=10000 python setup.py
```

## Referencias

- [ElectricSQL Documentation](https://electric-sql.com/docs)
- [PGlite Performance](https://pglite.dev/docs/performance)
- [Shapes Best Practices](https://electric-sql.com/docs/guides/shapes)
