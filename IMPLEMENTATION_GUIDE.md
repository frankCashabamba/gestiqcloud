# 🚀 Guía de Implementación - Sistema Configurable Sin Hardcodes

**Fecha:** 19 Enero 2026
**Estado:** Listo para Implementar
**Estimación:** 5-7 días

---

## 📋 Qué se ha creado

### Backend (Python/FastAPI)

#### 1. Modelos de Base de Datos
- `apps/backend/app/models/core/ui_config.py`
  - `UiSection` - Secciones del dashboard
  - `UiWidget` - Widgets dinámicos
  - `UiTable` - Configuración de tablas
  - `UiColumn` - Columnas de tabla
  - `UiFilter` - Filtros de tabla
  - `UiForm` - Formularios dinámicos
  - `UiFormField` - Campos de formulario
  - `UiDashboard` - Dashboards personalizados

#### 2. Migración Alembic
- `apps/backend/alembic/versions/010_ui_configuration_tables.py`
  - Crea todas las tablas necesarias
  - Índices y constraints optimizados
  - Compatible con PostgreSQL y SQLite

#### 3. Schemas Pydantic
- `apps/backend/app/schemas/ui_config_schemas.py`
  - Validación de datos
  - Schemas para CRUD operations
  - Response models

#### 4. Repositories (Data Access)
- `apps/backend/app/modules/ui_config/infrastructure/repositories.py`
  - `UiSectionRepository`
  - `UiWidgetRepository`
  - `UiTableRepository`
  - `UiFormRepository`
  - `UiDashboardRepository`

#### 5. API Endpoints
- `apps/backend/app/modules/ui_config/interface/http/admin.py`
  - `/ui-config/sections` - CRUD de secciones
  - `/ui-config/widgets` - CRUD de widgets
  - `/ui-config/tables` - CRUD de tablas
  - `/ui-config/forms` - CRUD de formularios
  - `/ui-config/dashboards` - CRUD de dashboards

### Frontend (React/TypeScript)

#### 1. Componentes Genéricos
- `apps/admin/src/components/GenericDashboard.tsx`
  - Carga dinámicamente secciones
  - Renderiza widgets según configuración
  - Sin hardcodes

- `apps/admin/src/components/GenericWidget.tsx`
  - Renderiza widgets por tipo:
    - `stat_card` - Tarjetas de estadísticas
    - `chart` - Gráficos
    - `table` - Tablas
    - `form` - Formularios

- `apps/admin/src/components/GenericTable.tsx`
  - Tabla completamente configurable
  - Filtros dinámicos
  - Paginación
  - Búsqueda
  - Exportación
  - Acciones personalizables

#### 2. Servicios
- `apps/admin/src/services/api.ts`
  - Cliente API centralizado
  - Manejo de autenticación
  - Endpoints organizados por módulo
  - Métodos para todas las operaciones CRUD

#### 3. Estilos
- `apps/admin/src/components/generic-components.css`
  - Responsive design
  - Animaciones suaves
  - Temas personalizables
  - Mobile-first

---

## 🛠️ Pasos de Implementación

### PASO 1: Ejecutar Migraciones (Backend)

```bash
# Usar script idempotente (lee ops/migrations/*/up.sql)
python ops/scripts/migrate_all_migrations_idempotent.py
```

**¿Qué hace?**
- Lee archivo: `ops/migrations/2026-01-19_010_ui_configuration_tables/up.sql`
- Crea 8 tablas nuevas:
  - `ui_sections` - Secciones del dashboard
  - `ui_widgets` - Widgets dinámicos
  - `ui_tables` - Configuración de tablas
  - `ui_columns` - Columnas de tabla
  - `ui_filters` - Filtros de tabla
  - `ui_forms` - Formularios dinámicos
  - `ui_form_fields` - Campos de formulario
  - `ui_dashboards` - Dashboards personalizados
- Añade índices y constraints
- Registra ejecución en `_migrations`
- Idempotente: seguro re-ejecutar

**Resultado esperado:** `[SUCCESS] All applicable migration(s) processed!`

### PASO 2: Registrar Modelos (Backend)

En `apps/backend/app/models/__init__.py` o `imports.py`, agregar:

```python
from app.models.core.ui_config import (
    UiSection,
    UiWidget,
    UiTable,
    UiColumn,
    UiFilter,
    UiForm,
    UiFormField,
    UiDashboard,
)
```

### PASO 3: Registrar Router (Backend)

En `apps/backend/app/main.py`, agregar el router:

```python
from app.modules.ui_config.interface.http.admin import router as ui_config_router

# En la sección de routers
app.include_router(ui_config_router, prefix="/api/v1/admin")
```

**URL resultante:** `GET /api/v1/admin/ui-config/sections`

### PASO 4: Copiar Componentes (Frontend)

Los archivos ya están creados, solo asegúrate de que existan:

```
apps/admin/src/
├── components/
│   ├── GenericDashboard.tsx
│   ├── GenericWidget.tsx
│   ├── GenericTable.tsx
│   └── generic-components.css
└── services/
    └── api.ts
```

### PASO 5: Crear Seed Data (Backend)

Crear `apps/backend/app/seeds/ui_config_seeds.py`:

```python
"""Initial seed data for UI configuration."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core.ui_config import (
    UiSection, UiWidget, UiDashboard
)

async def seed_ui_config(db: AsyncSession, tenant_id: uuid.UUID):
    """Create initial UI configuration for a new tenant."""

    # Create Dashboard section
    dashboard_section = UiSection(
        tenant_id=tenant_id,
        slug="dashboard",
        label="Dashboard",
        description="Main dashboard with KPIs",
        icon="📊",
        position=0,
        active=True,
        show_in_menu=True,
    )
    db.add(dashboard_section)
    await db.flush()

    # Create stat widgets
    widget_total = UiWidget(
        tenant_id=tenant_id,
        section_id=dashboard_section.id,
        widget_type="stat_card",
        title="Total Pagos",
        position=0,
        width=25,
        config={"metric": "total_payments", "icon": "💰", "color": "green"},
        api_endpoint="/dashboard_stats?metric=total_payments",
        refresh_interval=60,
    )
    db.add(widget_total)

    widget_pending = UiWidget(
        tenant_id=tenant_id,
        section_id=dashboard_section.id,
        widget_type="stat_card",
        title="Pendientes",
        position=1,
        width=25,
        config={"metric": "pending_count", "icon": "⏳", "color": "orange"},
        api_endpoint="/dashboard_stats?metric=pending_count",
        refresh_interval=60,
    )
    db.add(widget_pending)

    # Create dashboard
    dashboard = UiDashboard(
        tenant_id=tenant_id,
        name="Default Dashboard",
        slug="default",
        sections=[str(dashboard_section.id)],
        is_default=True,
    )
    db.add(dashboard)

    await db.commit()
```

### PASO 6: Actualizar Auth Helper (Frontend)

En `apps/admin/src/auth/useAuth.ts`, agregar función para obtener token:

```typescript
export function getAuthToken(): string | null {
  return localStorage.getItem("auth_token");
}
```

### PASO 7: Integrar Dashboard Principal (Frontend)

En `apps/admin/src/pages/Dashboard.tsx` o equivalente:

```typescript
import { GenericDashboard } from "../components/GenericDashboard";

export function DashboardPage() {
  return <GenericDashboard dashboardSlug="default" />;
}
```

### PASO 8: Configurar Variables de Entorno (Frontend)

En `apps/admin/.env`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 📊 Ejemplo Completo: Crear Dashboard de Pagos

### 1. Crear Sección via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/ui-config/sections \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "payments",
    "label": "Pagos",
    "description": "Gestión de pagos",
    "icon": "💳",
    "position": 1,
    "active": true,
    "show_in_menu": true
  }'
```

### 2. Crear Widget de Estadísticas

```bash
curl -X POST http://localhost:8000/api/v1/admin/ui-config/widgets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "section_id": "SECTION_ID_FROM_STEP_1",
    "widget_type": "stat_card",
    "title": "Total Pagos Hoy",
    "position": 0,
    "width": 25,
    "config": {
      "metric": "total_today",
      "icon": "💰",
      "color": "green"
    },
    "api_endpoint": "/dashboard_stats?metric=total_today",
    "refresh_interval": 60
  }'
```

### 3. Crear Tabla de Pagos

```bash
curl -X POST http://localhost:8000/api/v1/admin/ui-config/tables \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "payments-list",
    "title": "Tabla de Pagos",
    "api_endpoint": "/payments",
    "columns": [
      {
        "field_name": "id",
        "label": "ID",
        "data_type": "string",
        "sortable": true,
        "visible": true
      },
      {
        "field_name": "amount",
        "label": "Monto",
        "data_type": "number",
        "format": "currency",
        "sortable": true,
        "visible": true
      },
      {
        "field_name": "status",
        "label": "Estado",
        "data_type": "string",
        "format": "badge",
        "filterable": true,
        "visible": true
      },
      {
        "field_name": "created_at",
        "label": "Fecha",
        "data_type": "date",
        "format": "dd/MM/yyyy",
        "sortable": true,
        "visible": true
      }
    ],
    "filters": [
      {
        "field_name": "status",
        "label": "Estado",
        "filter_type": "select",
        "options": [
          {"label": "Pendiente", "value": "pending"},
          {"label": "Completado", "value": "completed"},
          {"label": "Fallido", "value": "failed"}
        ]
      }
    ],
    "actions": [
      {
        "type": "view",
        "label": "Ver"
      },
      {
        "type": "edit",
        "label": "Editar"
      },
      {
        "type": "delete",
        "label": "Eliminar",
        "confirmation": true
      }
    ],
    "pagination_size": 25,
    "sortable": true,
    "searchable": true,
    "exportable": true
  }'
```

### 4. Frontend Carga Automáticamente

El componente `GenericDashboard` cargará automáticamente:
- Todas las secciones creadas
- Todos los widgets
- Las tablas configuradas
- Sin necesidad de código adicional

---

## 🔄 Flujo de Datos

```
Usuario accede a /admin
    ↓
GenericDashboard.tsx cargado
    ↓
GET /api/v1/admin/ui-config/sections
    ↓
Backend retorna secciones desde BD
    ↓
Frontend renderiza tabs de secciones
    ↓
Usuario hace clic en sección
    ↓
GET /api/v1/admin/ui-config/sections/{id}/widgets
    ↓
Backend retorna widgets configurados
    ↓
GenericWidget renderiza cada widget
    ↓
Cada widget hace GET a su api_endpoint
    ↓
Datos se muestran dinámicamente
```

---

## ✅ Checklist de Validación

- [ ] Migraciones ejecutadas correctamente
- [ ] Modelos importados en `__init__.py`
- [ ] Router registrado en `main.py`
- [ ] Componentes copiados al frontend
- [ ] API client creado
- [ ] Variables de entorno configuradas
- [ ] Seed data creada
- [ ] Token auth helper funcionando
- [ ] GenericDashboard integrado en página principal
- [ ] Prueba: Cargar dashboard en navegador
- [ ] Prueba: API devuelve secciones
- [ ] Prueba: Componentes se renderizan sin errores

---

## 🐛 Troubleshooting

### Error: "Tablas no existen"
```bash
# Reiniciar migraciones
cd apps/backend
python -m alembic downgrade -1
python -m alembic upgrade head
```

### Error: "Module not found"
```python
# Asegurar que los archivos están en la ruta correcta:
# apps/backend/app/models/core/ui_config.py
# apps/backend/app/modules/ui_config/...
# apps/backend/app/schemas/ui_config_schemas.py
```

### Error: "CORS error" (Frontend)
```typescript
// En GenericDashboard.tsx, verificar:
const apiUrl = `${import.meta.env.VITE_API_URL}${endpoint}`;
// Debe ser: http://localhost:8000/api/v1/ui-config/...
```

### Error: "401 Unauthorized"
```typescript
// En api.ts, verificar token:
const token = getAuthToken();
if (!token) console.error("No token found");
```

---

## 📈 Próximos Pasos

### Fase 1: Core Features (Ya hecho)
- ✅ Modelos de base de datos
- ✅ API endpoints
- ✅ Componentes genéricos

### Fase 2: Funcionalidades Específicas (3 días)
- [ ] Dashboard de pagos
- [ ] Tabla de incidentes
- [ ] Gestión de webhooks
- [ ] Formulario dinámico para crear webhooks

### Fase 3: Admin UI (4-5 días)
- [ ] CRUD visual para secciones
- [ ] CRUD visual para widgets
- [ ] CRUD visual para tablas
- [ ] Dashboard builder drag-and-drop

### Fase 4: Reportes (2 días)
- [ ] Exportación a Excel
- [ ] Exportación a PDF
- [ ] Reportes personalizados

---

## 📞 Soporte

Si algo no funciona:

1. Revisar los logs del backend: `docker logs backend`
2. Revisar la consola del navegador (F12)
3. Verificar que la BD tiene las tablas: `SELECT * FROM ui_sections;`
4. Verificar que el token es válido

---

**¿Necesitas ayuda con algo específico?** Avísame y te guío paso a paso.
