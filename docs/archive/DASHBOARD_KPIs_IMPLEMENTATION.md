# Dashboard KPIs - Implementación Profesional ✅

## Resumen Ejecutivo

Se ha implementado un **sistema profesional de KPIs en tiempo real** para todas las plantillas del tenant, reemplazando los placeholders `--` con datos reales del backend.

## Componentes Implementados

### 1. Backend API - `dashboard_stats.py` ✅

**Ubicación**: `apps/backend/app/routers/dashboard_stats.py`

**Endpoints creados**:
- `GET /api/v1/dashboard/kpis` - KPIs generales del tenant
- `GET /api/v1/dashboard/kpis/taller` - KPIs específicos de taller mecánico
- `GET /api/v1/dashboard/kpis/panaderia` - KPIs específicos de panadería

**Parámetros soportados**:
- `periodo`: `today`, `week`, `month`, `year`

**Datos devueltos**:
```json
{
  "periodo": "today",
  "fecha_inicio": "2025-01-27",
  "fecha_fin": "2025-01-27",
  "ventas": {
    "total": 15420.50,
    "count": 48,
    "mostrador": 8920.30,
    "promedio": 321.26
  },
  "gastos": {
    "total": 3240.80,
    "dia": 450.20
  },
  "inventario": {
    "stock_critico": 12,
    "productos_en_stock": 456,
    "mermas": 3
  },
  "facturacion": {
    "por_cobrar_total": 24560.00,
    "por_cobrar_count": 18,
    "vencidas": 5
  },
  "compras": {
    "pendientes": 7
  },
  "pedidos": {
    "pendientes": 15,
    "entregas_hoy": 8
  }
}
```

**Características**:
- ✅ Respeta RLS (Row-Level Security) con `tenant_id`
- ✅ Consultas optimizadas con agregaciones SQL
- ✅ Conversión automática Decimal → float para JSON
- ✅ Manejo de valores NULL con `func.coalesce()`
- ✅ Filtros dinámicos por período

### 2. Hook React - `useDashboardKPIs.ts` ✅

**Ubicación**: `apps/tenant/src/hooks/useDashboardKPIs.ts`

**Hooks exportados**:
1. `useDashboardKPIs({ periodo, autoRefresh, refreshInterval })` - KPIs generales
2. `useTallerKPIs()` - KPIs de taller
3. `usePanaderiaKPIs()` - KPIs de panadería

**Funciones helper**:
- `formatCurrency(value, currency)` - Formatea moneda (EUR/USD)
- `formatNumber(value)` - Formatea números con separadores de miles

**Ejemplo de uso**:
```tsx
const { data, loading, error, refetch } = useDashboardKPIs({ 
  periodo: 'today',
  autoRefresh: true,
  refreshInterval: 60000 // 1 minuto
})

if (loading) return <Skeleton />
if (error) return <ErrorAlert message={error} />

return <div>{formatCurrency(data.ventas.total)}</div>
```

**Características**:
- ✅ Auto-refresh opcional
- ✅ Estados de loading/error
- ✅ Refetch manual disponible
- ✅ TypeScript types completos
- ✅ Autenticación con JWT (`useAuth()`)

### 3. Plantillas Actualizadas (4/4) ✅

#### a) `default.tsx` - Panel General
**KPIs mostrados**:
- Ventas hoy → `formatCurrency(kpisData.ventas.mostrador)`
- Gastos del día → `formatCurrency(kpisData.gastos.dia)`
- Facturas por cobrar → `formatCurrency(kpisData.facturacion.por_cobrar_total)`

#### b) `panaderia.tsx` - Sector Panadería
**KPIs mostrados**:
- Ventas mostrador → `formatCurrency(kpisData.ventas_mostrador)`
- Stock crítico → `formatNumber(kpisData.stock_critico)`
- Mermas registradas → `formatNumber(kpisData.mermas_registradas)`

#### c) `taller.tsx` - Sector Taller Mecánico
**KPIs mostrados**:
- Órdenes activas → `formatNumber(kpisData.ordenes_trabajo_activas)`
- Servicios hoy → `formatNumber(kpisData.servicios_completados_hoy)`
- Repuestos pendientes → `formatNumber(kpisData.repuestos_pendientes)`

#### d) `todoa100.tsx` - Sector Retail
**KPIs mostrados**:
- Ventas del día → `formatCurrency(kpisData.ventas.total)`
- Ticket promedio → `formatCurrency(kpisData.ventas.promedio)`
- Productos en stock → `formatNumber(kpisData.inventario.productos_en_stock)`

### 4. Mejoras UX/UI Implementadas ✅

**Loading States**:
```tsx
{loading ? (
  <span className="inline-block w-20 h-8 bg-slate-200 animate-pulse rounded"></span>
) : (
  value
)}
```

**Hover Effects**:
```tsx
className="... hover:shadow-md transition-shadow"
```

**Skeleton Animation**:
- Pulse en gris mientras carga
- Transición suave al mostrar datos

## Arquitectura de Datos

```mermaid
graph TB
    subgraph Frontend
        A[Plantillas TSX] --> B[useDashboardKPIs]
        B --> C[fetch + Auth]
    end
    
    subgraph Backend
        C --> D[/api/v1/dashboard/kpis]
        D --> E[RLS Middleware]
        E --> F[SQL Queries]
    end
    
    subgraph Database
        F --> G[(Invoices)]
        F --> H[(Stock Items)]
        F --> I[(Expenses)]
        F --> J[(Sales Orders)]
    end
    
    style B fill:#4A90E2
    style D fill:#50C878
    style F fill:#FF6B6B
```

## Tablas Consultadas

| Tabla | Uso |
|-------|-----|
| `invoices` | Ventas totales, facturas por cobrar |
| `expenses` | Gastos del día/período |
| `stock_items` | Stock crítico, productos en inventario |
| `stock_moves` | Mermas (kind='adjustment', qty<0) |
| `sales_orders` | Pedidos pendientes, órdenes de trabajo |
| `purchase_orders` | Compras pendientes, repuestos |
| `deliveries` | Entregas programadas |

## Testing

### 1. Prueba Backend
```bash
# Levantar backend
cd apps/backend
uvicorn app.main:app --reload

# Test endpoint (reemplazar JWT)
curl -X GET "http://localhost:8000/api/v1/dashboard/kpis?periodo=today" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Respuesta esperada**: JSON con todos los KPIs

### 2. Prueba Frontend
```bash
# Levantar frontend
cd apps/tenant
npm run dev

# Abrir navegador
open http://localhost:3000

# Inspeccionar Network tab
# Buscar: /api/v1/dashboard/kpis
```

**Resultado esperado**: 
- Números reales en lugar de `--`
- Skeleton animado durante carga
- Moneda formateada correctamente (€ 1.234,56)

## Instalación y Activación

### 1. Backend
```bash
# El router ya está montado en main.py línea 247
# Solo necesitas reiniciar el backend
docker compose restart backend

# O si usas uvicorn directamente
pkill uvicorn && uvicorn app.main:app --reload
```

### 2. Frontend
```bash
# El hook ya está creado, solo necesitas rebuild
cd apps/tenant
npm run build

# O en desarrollo
npm run dev
```

### 3. Verificación
```bash
# Verificar que el router está montado
curl http://localhost:8000/api/v1/dashboard/kpis | jq
```

## Próximas Mejoras (Opcional)

### 1. Caché Redis
```python
@router.get("/kpis")
@cache(expire=60)  # 1 minuto
def get_dashboard_kpis(...):
    ...
```

### 2. WebSocket Real-time
```python
@router.websocket("/ws/kpis")
async def websocket_kpis(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await get_kpis_async()
        await websocket.send_json(data)
        await asyncio.sleep(5)
```

### 3. Filtros Avanzados
```python
@router.get("/kpis")
def get_dashboard_kpis(
    periodo: str = "today",
    store_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ...
):
```

### 4. Gráficos Históricos
```tsx
import { LineChart } from 'recharts'

const { data } = useDashboardKPIs({ periodo: 'month' })
<LineChart data={data.ventas.historico} />
```

## Seguridad

✅ **RLS Middleware** - Aislamiento por tenant  
✅ **JWT Authentication** - Solo usuarios autenticados  
✅ **SQL Injection Protection** - SQLAlchemy ORM  
✅ **CORS Configurado** - Solo dominios permitidos  

## Performance

- **Queries optimizadas**: Solo 1 query por módulo
- **Agregaciones SQL**: Cálculos en base de datos
- **Índices recomendados**:
  ```sql
  CREATE INDEX idx_invoices_tenant_fecha ON invoices(tenant_id, fecha);
  CREATE INDEX idx_expenses_tenant_fecha ON expenses(tenant_id, fecha);
  CREATE INDEX idx_stock_items_tenant_qty ON stock_items(tenant_id, qty_on_hand);
  ```

## Changelog

### [1.0.0] - 2025-01-27
- ✅ Endpoint `/api/v1/dashboard/kpis` creado
- ✅ Endpoints específicos `/kpis/taller` y `/kpis/panaderia`
- ✅ Hook `useDashboardKPIs` con auto-refresh
- ✅ 4 plantillas actualizadas (default, panaderia, taller, todoa100)
- ✅ Formateo profesional de moneda y números
- ✅ Loading states con skeleton animation
- ✅ Router montado en `main.py`

---

**Implementado por**: Amp AI Agent  
**Fecha**: 27 de enero de 2025  
**Estado**: ✅ Completado y listo para producción
