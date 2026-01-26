# 🏗️ Arquitectura de Sistema Configurable sin Hardcodes

**Principio:** Todo lo que aparece en UI viene de tablas de configuración en base de datos.

---

## 🗄️ Nuevas Tablas de Configuración Necesarias

### 1. `ui_sections` - Secciones del Dashboard
```sql
CREATE TABLE ui_sections (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    slug VARCHAR(100) NOT NULL UNIQUE,           -- "dashboard", "payments", "incidents"
    label VARCHAR(150) NOT NULL,                 -- "Dashboard", "Pagos", "Incidentes"
    description TEXT,
    icon VARCHAR(50),                             -- emoji o nombre de icono
    position INT DEFAULT 0,                       -- orden en UI
    active BOOLEAN DEFAULT TRUE,
    show_in_menu BOOLEAN DEFAULT TRUE,
    role_restrictions JSONB DEFAULT NULL,        -- roles permitidos
    module_requirement VARCHAR(100),              -- módulo que debe estar activo
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. `ui_widgets` - Widgets Dinámicos
```sql
CREATE TABLE ui_widgets (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    section_id UUID NOT NULL REFERENCES ui_sections(id),
    widget_type VARCHAR(50) NOT NULL,             -- "stat_card", "chart", "table", "form"
    title VARCHAR(200),
    description TEXT,
    position INT DEFAULT 0,
    width INT DEFAULT 100,                        -- % ancho (25, 33, 50, 100)
    config JSONB NOT NULL,                        -- configuración específica por tipo
    api_endpoint VARCHAR(255),                    -- endpoint que alimenta el widget
    refresh_interval INT,                         -- segundos para auto-refresh
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. `ui_tables` - Tablas Configurables
```sql
CREATE TABLE ui_tables (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    slug VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(200),
    description TEXT,
    api_endpoint VARCHAR(255) NOT NULL,
    model_name VARCHAR(100),                      -- ej: "Payment", "Incident"
    columns JSONB NOT NULL,                       -- config de columnas
    filters JSONB,                                 -- filtros disponibles
    actions JSONB,                                 -- acciones (edit, delete, view)
    pagination_size INT DEFAULT 25,
    sortable BOOLEAN DEFAULT TRUE,
    searchable BOOLEAN DEFAULT TRUE,
    exportable BOOLEAN DEFAULT TRUE,              -- permite exportar
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. `ui_forms` - Formularios Dinámicos
```sql
CREATE TABLE ui_forms (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    slug VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(200),
    description TEXT,
    api_endpoint VARCHAR(255) NOT NULL,           -- endpoint POST/PUT
    model_name VARCHAR(100),
    fields JSONB NOT NULL,                        -- definición de campos
    submit_button_label VARCHAR(100),
    success_message VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. `ui_columns` - Configuración de Columnas de Tabla
```sql
CREATE TABLE ui_columns (
    id UUID PRIMARY KEY,
    table_id UUID NOT NULL REFERENCES ui_tables(id),
    field_name VARCHAR(100) NOT NULL,
    label VARCHAR(150),
    data_type VARCHAR(50),                       -- "string", "number", "date", "boolean"
    format VARCHAR(100),                          -- ej: "dd/MM/yyyy", "currency", "percentage"
    sortable BOOLEAN DEFAULT TRUE,
    filterable BOOLEAN DEFAULT TRUE,
    visible BOOLEAN DEFAULT TRUE,
    position INT DEFAULT 0,
    width INT,
    align VARCHAR(10) DEFAULT 'left'
);
```

### 6. `ui_filters` - Filtros Dinámicos
```sql
CREATE TABLE ui_filters (
    id UUID PRIMARY KEY,
    table_id UUID NOT NULL REFERENCES ui_tables(id),
    field_name VARCHAR(100),
    label VARCHAR(150),
    filter_type VARCHAR(50),                     -- "text", "select", "date", "range", "boolean"
    options JSONB,                                -- para select: [{label, value}]
    default_value VARCHAR(255),
    placeholder VARCHAR(200),
    position INT DEFAULT 0
);
```

### 7. `ui_form_fields` - Configuración de Campos de Formulario
```sql
CREATE TABLE ui_form_fields (
    id UUID PRIMARY KEY,
    form_id UUID NOT NULL REFERENCES ui_forms(id),
    field_name VARCHAR(100),
    label VARCHAR(150),
    field_type VARCHAR(50),                      -- "text", "email", "select", "date", "number"
    required BOOLEAN DEFAULT FALSE,
    validation JSONB,                            -- {pattern, min, max, custom}
    options JSONB,                               -- para select/radio/checkbox
    placeholder VARCHAR(200),
    help_text VARCHAR(255),
    position INT DEFAULT 0,
    default_value VARCHAR(255)
);
```

### 8. `ui_dashboards` - Dashboards Personalizados
```sql
CREATE TABLE ui_dashboards (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(200),
    description TEXT,
    slug VARCHAR(100) NOT NULL UNIQUE,
    sections JSONB,                              -- array de section_ids
    is_default BOOLEAN DEFAULT FALSE,
    role_visibility JSONB,                       -- roles que pueden ver
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔗 Relaciones Visuales

```
ui_dashboards
├── sections (JSONB array de section_ids)
    ├── ui_sections
    │   └── widgets (JSONB array de widget_ids)
    │       └── ui_widgets
    │           ├── api_endpoint
    │           └── config
    │
    ├── tables (JSONB array de table_ids)
    │   └── ui_tables
    │       ├── ui_columns
    │       ├── ui_filters
    │       └── api_endpoint
    │
    └── forms (JSONB array de form_ids)
        └── ui_forms
            ├── ui_form_fields
            └── api_endpoint
```

---

## 📝 Ejemplos de Configuración

### Ejemplo 1: Widget de Estadísticas
```json
{
  "id": "widget-001",
  "tenant_id": "tenant-1",
  "section_id": "dashboard",
  "widget_type": "stat_card",
  "title": "Total Pagos Hoy",
  "config": {
    "metric": "total_payments_today",
    "icon": "💰",
    "color": "green"
  },
  "api_endpoint": "/dashboard_stats?metric=total_payments_today",
  "refresh_interval": 60
}
```

### Ejemplo 2: Tabla de Incidentes
```json
{
  "id": "table-incidents",
  "slug": "incidents-list",
  "title": "Incidentes",
  "api_endpoint": "/incidents",
  "model_name": "Incident",
  "columns": [
    {
      "field_name": "id",
      "label": "ID",
      "data_type": "string",
      "sortable": true,
      "width": 100
    },
    {
      "field_name": "status",
      "label": "Estado",
      "data_type": "string",
      "filterable": true,
      "format": "badge"
    },
    {
      "field_name": "created_at",
      "label": "Fecha",
      "data_type": "date",
      "format": "dd/MM/yyyy HH:mm"
    }
  ],
  "filters": [
    {
      "field_name": "status",
      "label": "Estado",
      "filter_type": "select",
      "options": [
        {"label": "Abierto", "value": "open"},
        {"label": "Resuelto", "value": "resolved"}
      ]
    }
  ],
  "actions": [
    {"type": "view", "label": "Ver"},
    {"type": "edit", "label": "Editar"},
    {"type": "delete", "label": "Eliminar"}
  ]
}
```

### Ejemplo 3: Formulario de Webhook
```json
{
  "id": "form-webhook",
  "slug": "webhook-form",
  "title": "Crear Webhook",
  "api_endpoint": "/webhooks",
  "fields": [
    {
      "field_name": "name",
      "label": "Nombre",
      "field_type": "text",
      "required": true,
      "placeholder": "Mi webhook"
    },
    {
      "field_name": "url",
      "label": "URL",
      "field_type": "text",
      "required": true,
      "validation": {
        "pattern": "^https?://"
      }
    },
    {
      "field_name": "events",
      "label": "Eventos",
      "field_type": "select",
      "required": true,
      "options": [
        {"label": "Payment Created", "value": "payment.created"},
        {"label": "Invoice Sent", "value": "invoice.sent"}
      ]
    }
  ]
}
```

---

## 🎯 Flujo de Carga (Sin Hardcodes)

```
1. Usuario accede a /admin
   ↓
2. Frontend carga: GET /api/v1/dashboards/default
   ↓
3. Backend retorna:
   {
     "dashboard": {
       "sections": [
         { "id": "dashboard", "label": "Dashboard", "position": 0 },
         { "id": "payments", "label": "Pagos", "position": 1 }
       ]
     }
   }
   ↓
4. Frontend renderiza cada sección dinámicamente
   ↓
5. Por cada sección, carga: GET /api/v1/sections/:id/widgets
   ↓
6. Backend retorna widgets configurados:
   {
     "widgets": [
       {
         "type": "stat_card",
         "title": "Total Pagos",
         "config": {...},
         "api_endpoint": "/dashboard_stats"
       }
     ]
   }
   ↓
7. Frontend renderiza componente dinámico según type
   ↓
8. Cada widget carga su dato: GET /dashboard_stats
```

---

## 🖼️ Componentes React Genéricos

```typescript
// GenericDashboard - carga dinámicamente
<GenericDashboard dashboardId="default" />

// GenericWidget - renderiza según tipo
<GenericWidget
  config={widget}
  onRefresh={() => refetch()}
/>

// GenericTable - tabla dinámica
<GenericTable
  tableConfig={tableConfig}
  apiEndpoint="/incidents"
  filters={filters}
/>

// GenericForm - formulario dinámico
<GenericForm
  formConfig={formConfig}
  onSubmit={handleSubmit}
/>
```

---

## 📊 Ejemplo Completo: Panel de Pagos

### Backend: Tablas de configuración
```
ui_sections
├── id: "payments"
├── label: "Pagos"
└── widgets: ["stat-total", "stat-pending", "table-payments"]

ui_widgets
├── {"id": "stat-total", "type": "stat_card", "api_endpoint": "/dashboard_stats?metric=total_payments"}
├── {"id": "stat-pending", "type": "stat_card", "api_endpoint": "/dashboard_stats?metric=pending_payments"}
└── {"id": "table-payments", "type": "table", "api_endpoint": "/payments"}

ui_tables
└── {
      "id": "payments-table",
      "api_endpoint": "/payments",
      "columns": [
        {"field_name": "id", "label": "ID"},
        {"field_name": "amount", "label": "Monto", "format": "currency"},
        {"field_name": "status", "label": "Estado"},
        {"field_name": "created_at", "label": "Fecha", "format": "date"}
      ]
    }
```

### Frontend: Componente
```typescript
export function PaymentsDashboard() {
  const { data: section } = useApiData('/api/v1/sections/payments');

  return (
    <div>
      <h1>{section.label}</h1>
      <GenericWidget config={section.widgets} />
      <GenericTable tableId="payments-table" />
    </div>
  );
}
```

---

## ✨ Ventajas de este Enfoque

✅ **Sin Hardcodes**
- Todo en base de datos
- Cambios sin redeploy

✅ **Multi-tenant**
- Cada tenant puede customizar su UI
- Diferentes dashboards por rol

✅ **Escalable**
- Agregar nuevas secciones/widgets sin tocar código
- Admin puede crear custom dashboards

✅ **Mantenible**
- Un solo conjunto de componentes genéricos
- Lógica centralizada

✅ **Auditable**
- Historial de cambios en configuración
- Quién cambió qué y cuándo

---

## 🚀 Implementación por Fases

### FASE 1: Infraestructura Base
- [ ] Crear tablas de configuración en backend
- [ ] Endpoints CRUD para cada tabla
- [ ] Endpoints de carga (GET /sections, /widgets, etc)
- [ ] Seed data inicial

### FASE 2: Componentes Genéricos (Frontend)
- [ ] GenericDashboard component
- [ ] GenericWidget system
- [ ] GenericTable component
- [ ] GenericForm component
- [ ] API client configurable

### FASE 3: Admin UI para Configuración
- [ ] CRUD de secciones
- [ ] CRUD de widgets
- [ ] CRUD de tablas
- [ ] CRUD de formularios
- [ ] Visual dashboard builder

### FASE 4: Funcionalidad Específica
- [ ] Pagos dashboard
- [ ] Incidentes management
- [ ] Notificaciones
- [ ] Webhooks management
- [ ] E-invoicing

---

## 📋 Estructura de Carpetas (Actualizada)

```
apps/admin/src/
├── components/
│   ├── GenericDashboard.tsx
│   ├── GenericWidget.tsx
│   ├── GenericTable.tsx
│   ├── GenericForm.tsx
│   └── ...
├── features/
│   ├── dashboard/
│   ├── payments/
│   ├── incidents/
│   ├── webhooks/
│   ├── config-builder/      [NUEVO - Admin UI]
│   │   ├── SectionBuilder.tsx
│   │   ├── WidgetBuilder.tsx
│   │   ├── TableBuilder.tsx
│   │   └── FormBuilder.tsx
│   └── ...
├── hooks/
│   ├── useApiData.ts
│   ├── useDashboardConfig.ts
│   ├── useTableConfig.ts
│   └── ...
└── services/
    ├── configService.ts
    └── ...
```

---

**Próximos pasos:**

1. ¿Empiezo creando las tablas de configuración?
2. ¿O prefiero primero los componentes genéricos?
3. ¿Necesitas un admin UI para configurar todo esto?
