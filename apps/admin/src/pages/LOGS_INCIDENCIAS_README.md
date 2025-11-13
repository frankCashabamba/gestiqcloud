# 📋 Sistema de Logs e Incidencias Admin UI

## Componentes Implementados

### 1. LogsViewer (`/admin/logs`)
Visor centralizado de logs del sistema con las siguientes características:

**Características:**
- ✅ Filtros avanzados (tipo, tenant, usuario, fechas, acción)
- ✅ Stats cards (eventos hoy, logins fallidos, errores críticos)
- ✅ Tabla paginada (50 items por página)
- ✅ Auto-refresh cada 30s (opcional)
- ✅ Exportación a CSV
- ✅ Modal de detalles JSON
- ✅ Color coding por tipo de log

**Tipos de logs soportados:**
- `audit_log` - Eventos generales del sistema
- `auth_audit` - Eventos de autenticación
- `auditoria_importacion` - Cambios en importaciones

**Filtros disponibles:**
```typescript
{
  tipo_log: 'all' | 'audit_log' | 'auth_audit' | 'auditoria_importacion'
  tenant_id: string (UUID o ID)
  user_id: string (UUID)
  fecha_desde: string (YYYY-MM-DD)
  fecha_hasta: string (YYYY-MM-DD)
  accion: string (login, create, update...)
  page: number
  limit: number (default: 50)
}
```

---

### 2. IncidenciasPanel (`/admin/incidencias`)
Panel de gestión de incidencias con IA auto-resolución.

**Tabs:**
1. **Activas** - Incidencias abiertas o en progreso
2. **Resueltas** - Incidencias cerradas o auto-resueltas
3. **Stock Alerts** - Alertas de inventario bajo

**Características por tab:**

#### Tab Activas/Resueltas:
- ✅ Badge de severidad (critical, high, medium, low)
- ✅ Indicador "🤖 Auto-detect" para incidencias automáticas
- ✅ Indicador "✨ Auto-resuelto" si fue cerrada por IA
- ✅ Acciones rápidas:
  - 🔍 Ver detalle completo
  - 🤖 Analizar con IA
  - ✨ Auto-Resolver
  - 👤 Asignarme
  - ✅ Cerrar

#### Tab Stock Alerts:
- ✅ Producto, almacén, stock actual/mínimo
- ✅ Estados: active, notified, resolved
- ✅ Acciones:
  - 📧 Notificar ahora
  - ✅ Resolver alerta

---

### 3. IncidentDetailModal
Modal completo de detalle de incidencia con:

**Secciones:**
- 📊 Información general (ID, tipo, severidad, tenant, usuario, estado, fechas)
- 📝 Título y descripción
- 🔍 Stack trace (si existe)
- 📦 Metadata JSON
- 🤖 **Análisis IA** (si existe)
  - Análisis completo
  - 💡 Sugerencia de resolución
- 📄 Notas de resolución

**Acciones del footer:**
- 🤖 Analizar con IA
- ✨ Auto-Resolver
- 👤 Asignarme
- ✅ Cerrar
- Cancelar

---

## Servicios API

### `logs.ts`
```typescript
// Lista logs con filtros y paginación
listLogs(filters: LogFilters): Promise<LogsResponse>

// Exporta logs a CSV
exportLogs(filters: LogFilters): Promise<Blob>
```

### `incidents.ts`
```typescript
// CRUD Incidencias
listIncidents(filters: { estado?: string }): Promise<Incident[]>
getIncident(id: string): Promise<Incident>

// Acciones IA
analyzeIncident(id: string): Promise<void>
autoResolveIncident(id: string): Promise<void>

// Gestión
assignIncident(id: string, userId: string): Promise<void>
closeIncident(id: string): Promise<void>

// Stock Alerts
listStockAlerts(filters: { estado?: string }): Promise<StockAlert[]>
notifyStockAlert(id: string): Promise<void>
resolveStockAlert(id: string): Promise<void>
```

---

## Tipos TypeScript

### `types/logs.ts`
```typescript
interface LogEntry {
  id: string
  tipo_log: 'audit_log' | 'auth_audit' | 'auditoria_importacion'
  tenant_id?: string
  user_id?: string
  accion?: string
  kind?: string
  evento?: string
  ip_address?: string
  metadata?: Record<string, any>
  created_at: string
}

interface LogStats {
  eventos_hoy: number
  logins_fallidos_24h: number
  errores_criticos: number
  total_registros: number
}
```

### `types/incidents.ts`
```typescript
interface Incident {
  id: string
  tenant_id?: string
  user_id?: string
  tipo: string
  severidad: 'low' | 'medium' | 'high' | 'critical'
  titulo: string
  descripcion: string
  estado: 'open' | 'in_progress' | 'resolved' | 'auto_resolved' | 'closed'
  auto_detected: boolean
  auto_resolved: boolean
  stack_trace?: string
  metadata?: Record<string, any>
  ia_analysis?: string | Record<string, any>
  ia_suggestion?: string
  assigned_to?: string
  resolution_notes?: string
  created_at: string
  updated_at: string
  resolved_at?: string
}

interface StockAlert {
  id: string
  tenant_id: string
  product_id: string
  product_name: string
  warehouse_id: string
  warehouse_name: string
  qty_on_hand: number
  min_qty: number
  estado: 'active' | 'notified' | 'resolved'
  detected_at: string
  notified_at?: string
  resolved_at?: string
}
```

---

## Endpoints Backend Necesarios

### Logs
```
GET  /api/v1/admin/logs
     ?tipo_log=audit_log
     &tenant_id=uuid
     &user_id=uuid
     &fecha_desde=2025-01-01
     &fecha_hasta=2025-01-31
     &accion=login
     &page=1
     &limit=50

GET  /api/v1/admin/logs/export
     (mismos params, retorna CSV)
```

**Response:**
```json
{
  "logs": [
    {
      "id": "uuid",
      "tipo_log": "auth_audit",
      "tenant_id": "uuid",
      "user_id": "uuid",
      "accion": "login",
      "ip_address": "127.0.0.1",
      "metadata": {},
      "created_at": "2025-01-27T10:00:00Z"
    }
  ],
  "stats": {
    "eventos_hoy": 150,
    "logins_fallidos_24h": 3,
    "errores_criticos": 0,
    "total_registros": 1542
  },
  "total": 1542
}
```

---

### Incidencias
```
GET  /api/v1/admin/incidents?estado=open,in_progress
GET  /api/v1/admin/incidents/:id
POST /api/v1/admin/incidents/:id/analyze
POST /api/v1/admin/incidents/:id/auto-resolve
POST /api/v1/admin/incidents/:id/assign
     Body: { "user_id": "uuid" }
POST /api/v1/admin/incidents/:id/close
```

**Response GET /incidents:**
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "user_id": "uuid",
    "tipo": "database_error",
    "severidad": "high",
    "titulo": "Error de conexión a base de datos",
    "descripcion": "No se pudo conectar al pool...",
    "estado": "open",
    "auto_detected": true,
    "auto_resolved": false,
    "stack_trace": "Traceback...",
    "metadata": {},
    "ia_analysis": "El error indica...",
    "ia_suggestion": "Verificar configuración de pool...",
    "assigned_to": null,
    "resolution_notes": null,
    "created_at": "2025-01-27T10:00:00Z",
    "updated_at": "2025-01-27T10:00:00Z",
    "resolved_at": null
  }
]
```

---

### Stock Alerts
```
GET  /api/v1/admin/stock-alerts?estado=active,notified
POST /api/v1/admin/stock-alerts/:id/notify
POST /api/v1/admin/stock-alerts/:id/resolve
```

**Response GET /stock-alerts:**
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "product_id": "uuid",
    "product_name": "Producto A",
    "warehouse_id": "uuid",
    "warehouse_name": "Almacén Principal",
    "qty_on_hand": 5,
    "min_qty": 10,
    "estado": "active",
    "detected_at": "2025-01-27T08:00:00Z",
    "notified_at": null,
    "resolved_at": null
  }
]
```

---

## Navegación Admin

Las nuevas rutas ya están integradas en:

**`App.tsx`:**
```tsx
<Route path="logs" element={<LogsViewer />} />
<Route path="incidencias" element={<IncidenciasPanel />} />
```

**`AdminPanel.tsx`:**
```tsx
{ 
  nombre: 'Logs del Sistema', 
  descripcion: 'Auditoría y monitoreo centralizado', 
  icono: '/icons/logs.png', 
  url_completa: 'logs' 
},
{ 
  nombre: 'Incidencias', 
  descripcion: '🤖 Con IA auto-resolución', 
  icono: '/icons/incidents.png', 
  url_completa: 'incidencias' 
}
```

---

## Testing Manual

### 1. LogsViewer
```bash
# Navegar
http://localhost:5173/admin/logs

# Probar filtros:
- Seleccionar tipo: "auth_audit"
- Ingresar tenant_id
- Seleccionar rango de fechas
- Activar auto-refresh
- Exportar CSV
- Click en "Ver JSON" de cualquier log
```

### 2. IncidenciasPanel
```bash
# Navegar
http://localhost:5173/admin/incidencias

# Tab Activas:
- Ver lista de incidencias abiertas
- Click 🔍 para ver detalle completo
- Click 🤖 para analizar con IA
- Click ✨ para auto-resolver
- Click 👤 para asignarse
- Click ✅ para cerrar

# Tab Resueltas:
- Ver incidencias cerradas
- Verificar badge "🤖 Auto-resuelto"

# Tab Stock Alerts:
- Ver alertas de inventario
- Click "📧 Notificar"
- Click "✅ Resolver"
```

---

## Diseño UI

**Colores por severidad:**
- 🔴 Critical: bg-red-100 text-red-800
- 🟠 High: bg-orange-100 text-orange-800
- 🟡 Medium: bg-yellow-100 text-yellow-800
- 🔵 Low: bg-blue-100 text-blue-800

**Estados de incidencia:**
- Open: bg-gray-100 text-gray-800
- In Progress: bg-blue-100 text-blue-800
- Resolved: bg-green-100 text-green-800
- Auto-resolved: bg-green-100 text-green-800 + 🤖
- Closed: bg-gray-100 text-gray-800

**Responsive:**
- Grid adaptativo (1-4 columnas según pantalla)
- Tabla con scroll horizontal
- Modal full-width en móvil

---

## Próximos Pasos

### Backend (Falta implementar):
1. **Endpoints de logs** (`/api/v1/admin/logs`)
   - Consulta multi-tabla (audit_log + auth_audit + auditoria_importacion)
   - Filtrado y paginación
   - Stats agregadas
   - Export CSV

2. **Endpoints de incidencias** (`/api/v1/admin/incidents`)
   - CRUD completo
   - Trigger análisis IA (Celery task)
   - Auto-resolución (GPT-4 + tool calling)
   - Asignación y cierre

3. **Endpoints de stock alerts** (`/api/v1/admin/stock-alerts`)
   - Consulta con JOIN a products/warehouses
   - Notificación por email (Celery)
   - Actualización de estado

### IA Features (Fase 2):
1. **Análisis automático de incidencias:**
   - GPT-4 analiza stack trace + metadata
   - Genera sugerencias de resolución
   - Clasifica severidad

2. **Auto-resolución:**
   - Patrones conocidos → resolución automática
   - Script SQL/Python sugerido
   - Validación y ejecución

3. **Detección proactiva:**
   - Monitoreo de logs en tiempo real
   - Creación automática de incidencias
   - Alertas predictivas

---

## Archivos Creados

```
apps/admin/src/
├── pages/
│   ├── LogsViewer.tsx ✅ (350 líneas)
│   ├── IncidenciasPanel.tsx ✅ (400 líneas)
│   └── LOGS_INCIDENCIAS_README.md ✅ (este archivo)
├── components/
│   └── IncidentDetailModal.tsx ✅ (250 líneas)
├── services/
│   ├── logs.ts ✅ (100 líneas)
│   └── incidents.ts ✅ (150 líneas)
└── types/
    ├── logs.ts ✅ (30 líneas)
    └── incidents.ts ✅ (50 líneas)

Total: ~1,330 líneas de código profesional ✅
```

**Estado:** Frontend 100% completo. Backend pendiente.
