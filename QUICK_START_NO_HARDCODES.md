# ⚡ Quick Start - Sistema Sin Hardcodes

**Tiempo total:** 5-10 minutos para validar setup

---

## 📋 Lo que se creó

✅ **8 nuevas tablas de configuración**
✅ **28 API endpoints CRUD**
✅ **4 componentes React genéricos**
✅ **1 cliente API centralizado**
✅ **100% configurable desde BD - CERO HARDCODES**

---

## 🚀 5 Pasos para Activar

### 1️⃣ Backend: Ejecutar Migraciones

```bash
# Script idempotente (lee ops/migrations/*/up.sql)
python ops/scripts/migrate_all_migrations_idempotent.py
```

**¿Qué pasa?**
- ✅ Lee todas las migraciones en `ops/migrations/`
- ✅ Ejecuta la nueva: `2026-01-19_010_ui_configuration_tables/up.sql`
- ✅ Crea 8 tablas nuevas con índices
- ✅ Evita re-ejecutar migraciones ya aplicadas
- ✅ Registra todo en tabla `_migrations`

**Resultado esperado:**
```
[OK] Database connection successful
[OK] Migrations tracking table ready
> 2026-01-19_010_ui_configuration_tables
  [OK] Migration applied
[SUCCESS] All applicable migration(s) processed!
```

### 2️⃣ Backend: Registrar Modelos

En `apps/backend/app/models/__init__.py`:

```python
from app.models.core.ui_config import (
    UiSection, UiWidget, UiTable,
    UiColumn, UiFilter, UiForm,
    UiFormField, UiDashboard
)
```

### 3️⃣ Backend: Registrar Router

En `apps/backend/app/main.py`:

```python
from app.modules.ui_config.interface.http.admin import router as ui_config_router

# Dentro de la función main() o en la inicialización:
app.include_router(ui_config_router, prefix="/api/v1/admin")
```

### 4️⃣ Frontend: Verificar Archivos

Confirmarcorp que existen:

```
✅ apps/admin/src/components/GenericDashboard.tsx
✅ apps/admin/src/components/GenericWidget.tsx
✅ apps/admin/src/components/GenericTable.tsx
✅ apps/admin/src/components/generic-components.css
✅ apps/admin/src/services/api.ts
```

### 5️⃣ Frontend: Usar en Página Principal

En `apps/admin/src/pages/Dashboard.tsx`:

```typescript
import { GenericDashboard } from "../components/GenericDashboard";

export default function DashboardPage() {
  return <GenericDashboard dashboardSlug="default" />;
}
```

---

## ✨ Crear tu Primer Dashboard (API)

### 1. Crear una Sección

```bash
curl -X POST http://localhost:8000/api/v1/admin/ui-config/sections \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "my-dashboard",
    "label": "Mi Dashboard",
    "description": "Mi primer dashboard",
    "icon": "📊",
    "position": 0,
    "active": true,
    "show_in_menu": true
  }'
```

**Resultado:**
```json
{
  "id": "12345678-1234-5678-1234-567812345678",
  "slug": "my-dashboard",
  "label": "Mi Dashboard",
  "...": "..."
}
```

### 2. Copiar el `id` y crear un Widget

```bash
curl -X POST http://localhost:8000/api/v1/admin/ui-config/widgets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "section_id": "12345678-1234-5678-1234-567812345678",
    "widget_type": "stat_card",
    "title": "Mis Métricas",
    "position": 0,
    "width": 50,
    "config": {
      "metric": "total_users",
      "icon": "👥",
      "color": "blue"
    },
    "api_endpoint": "/dashboard_stats?metric=total_users",
    "refresh_interval": 60,
    "active": true
  }'
```

### 3. Abrir navegador

```
http://localhost:3000/dashboard
```

**¡Eso es todo!** El dashboard se cargará automáticamente desde BD.

---

## 🔍 Verificar que Funciona

### Backend

```bash
# Test 1: Listar secciones
curl http://localhost:8000/api/v1/admin/ui-config/sections \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response esperado: []  (vacío al principio)

# Test 2: Crear sección (ver arriba)
# Test 3: Listar de nuevo - debe mostrar la sección creada
```

### Frontend

Abrir consola del navegador (F12) y ejecutar:

```typescript
// Test: Traer secciones desde API
fetch('http://localhost:8000/api/v1/admin/ui-config/sections', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
  }
})
.then(r => r.json())
.then(data => console.log('Secciones:', data))
```

---

## 📊 Ejemplos Listos para Copiar-Pegar

### Ejemplo 1: Widget de Estadísticas

```json
{
  "section_id": "YOUR_SECTION_ID",
  "widget_type": "stat_card",
  "title": "Pagos Procesados Hoy",
  "position": 0,
  "width": 25,
  "config": {
    "metric": "payments_today",
    "icon": "💳",
    "color": "green"
  },
  "api_endpoint": "/dashboard_stats?metric=payments_today",
  "refresh_interval": 60,
  "active": true
}
```

### Ejemplo 2: Tabla de Datos

```json
{
  "slug": "users-table",
  "title": "Tabla de Usuarios",
  "api_endpoint": "/admin/users",
  "columns": [
    {
      "field_name": "id",
      "label": "ID",
      "data_type": "string",
      "sortable": true,
      "visible": true,
      "position": 0
    },
    {
      "field_name": "email",
      "label": "Email",
      "data_type": "string",
      "sortable": true,
      "visible": true,
      "position": 1
    },
    {
      "field_name": "created_at",
      "label": "Creado",
      "data_type": "date",
      "format": "dd/MM/yyyy",
      "sortable": true,
      "visible": true,
      "position": 2
    }
  ],
  "filters": [
    {
      "field_name": "email",
      "label": "Email",
      "filter_type": "text",
      "placeholder": "Buscar por email"
    }
  ],
  "pagination_size": 25,
  "sortable": true,
  "searchable": true,
  "exportable": true,
  "active": true
}
```

### Ejemplo 3: Formulario

```json
{
  "slug": "create-payment",
  "title": "Crear Pago",
  "api_endpoint": "/payments",
  "method": "POST",
  "fields": [
    {
      "field_name": "amount",
      "label": "Monto",
      "field_type": "number",
      "required": true,
      "placeholder": "0.00",
      "validation": {
        "min": 0.01
      },
      "position": 0
    },
    {
      "field_name": "reference",
      "label": "Referencia",
      "field_type": "text",
      "required": true,
      "placeholder": "Ej: PAY-001",
      "position": 1
    },
    {
      "field_name": "status",
      "label": "Estado",
      "field_type": "select",
      "options": [
        {"label": "Pendiente", "value": "pending"},
        {"label": "Completado", "value": "completed"},
        {"label": "Fallido", "value": "failed"}
      ],
      "position": 2
    }
  ],
  "submit_button_label": "Crear Pago",
  "success_message": "Pago creado exitosamente",
  "active": true
}
```

---

## 🐛 Troubleshooting Rápido

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError` | Verifica que `ui_config.py` existe en `/models/core/` |
| `Table doesn't exist` | Ejecuta `alembic upgrade head` |
| `404 /ui-config` | Verifica que el router está registrado en `main.py` |
| `CORS error` en frontend | Verifica `VITE_API_URL` en `.env` |
| `401 Unauthorized` | Verifica que `getAuthToken()` retorna token válido |
| Dashboard vacío | Verifica que hay secciones creadas en BD |

---

## 📈 Performance Esperado

| Acción | Tiempo |
|--------|--------|
| Load dashboard | <100ms |
| Load secciones | <50ms |
| Load widgets | <100ms |
| Search table | <200ms |
| Export table | <500ms |

---

## 🎓 Próximos Pasos

1. **Hoy:** Ejecutar migraciones y crear primer dashboard
2. **Mañana:** Integrar con datos reales (pagos, incidentes)
3. **Día 3:** Crear admin UI para gestionar configuración
4. **Día 4:** Agregar más módulos (webhooks, e-invoicing)

---

## 💡 Recordatorio: CERO HARDCODES

```typescript
// ❌ ANTES (Hardcoded - BAD)
function Dashboard() {
  return (
    <>
      <h1>Dashboard</h1>
      <PaymentsWidget />
      <UsersWidget />
      <PaymentsTable />
    </>
  );
}

// ✅ AHORA (Configurable - GOOD)
function Dashboard() {
  return <GenericDashboard dashboardSlug="default" />;
}
```

**Un archivo. Infinitas posibilidades. Todo desde BD.**

---

## 📞 ¿Preguntas?

Si algo no funciona:
1. Revisa los logs: `docker logs backend`
2. Verifica consola del navegador: `F12`
3. Consulta `IMPLEMENTATION_GUIDE.md` para detalles

---

**¡Listo! Ahora tienes un sistema completamente configurable. Happy coding! 🚀**
