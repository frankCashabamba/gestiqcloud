# 🚀 PLAN DE DESARROLLO - MÓDULOS FALTANTES FRONTEND

**Fecha**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Estado**: 📋 PLANIFICADO

---

## 📊 ESTADO ACTUAL

### Módulos Backend: 30
### Módulos Frontend Tenant: 16
### **GAP: 14 módulos faltantes**

---

## 🎯 PRIORIZACIÓN

### 🔴 PRIORIDAD ALTA (Hacer YA)

#### 1. CRM - Customer Relationship Management
**Esfuerzo**: 2-3 días
**Valor**: ⭐⭐⭐⭐⭐

**Archivos a crear**:
```
apps/tenant/src/modules/crm/
├── manifest.ts ✅ CREADO
├── Routes.tsx
├── services.ts
├── types.ts
├── pages/
│   ├── Dashboard.tsx
│   ├── Leads/
│   │   ├── List.tsx
│   │   ├── Form.tsx
│   │   └── Detail.tsx
│   ├── Opportunities/
│   │   ├── List.tsx
│   │   ├── Form.tsx
│   │   └── Detail.tsx
│   └── Pipeline/
│       └── Kanban.tsx
└── components/
    ├── LeadCard.tsx
    ├── OpportunityCard.tsx
    ├── PipelineStage.tsx
    └── ActivityTimeline.tsx
```

**Funcionalidades**:
- ✅ Dashboard con métricas clave (conversión, pipeline value)
- ✅ Gestión de leads (crear, editar, eliminar, asignar)
- ✅ Gestión de oportunidades (estados, probabilidad, valor estimado)
- ✅ Pipeline visual (drag & drop entre etapas)
- ✅ Timeline de actividades
- ✅ Filtros y búsqueda
- ✅ Exportación a Excel

**Endpoints Backend** (verificar existen):
```
GET    /api/v1/tenant/crm/leads
POST   /api/v1/tenant/crm/leads
PUT    /api/v1/tenant/crm/leads/{id}
DELETE /api/v1/tenant/crm/leads/{id}

GET    /api/v1/tenant/crm/opportunities
POST   /api/v1/tenant/crm/opportunities
PUT    /api/v1/tenant/crm/opportunities/{id}
DELETE /api/v1/tenant/crm/opportunities/{id}

GET    /api/v1/tenant/crm/pipeline
GET    /api/v1/tenant/crm/dashboard
```

---

#### 2. Reconciliation - Conciliación Bancaria
**Esfuerzo**: 2-3 días
**Valor**: ⭐⭐⭐⭐⭐

**Archivos a crear**:
```
apps/tenant/src/modules/reconciliation/
├── manifest.ts
├── Routes.tsx
├── services.ts
├── types.ts
├── pages/
│   ├── Dashboard.tsx
│   ├── BankTransactions/
│   │   └── List.tsx
│   ├── Invoices/
│   │   └── List.tsx
│   └── Reconcile/
│       ├── Match.tsx
│       └── Manual.tsx
└── components/
    ├── TransactionCard.tsx
    ├── InvoiceCard.tsx
    ├── MatchSuggestions.tsx
    └── ReconciliationSummary.tsx
```

**Funcionalidades**:
- ✅ Dashboard de conciliación (pendientes, conciliados, diferencias)
- ✅ Lista de transacciones bancarias sin conciliar
- ✅ Lista de facturas sin pagar
- ✅ Matching automático (sugerencias)
- ✅ Matching manual
- ✅ Historial de conciliaciones
- ✅ Reportes de diferencias

**Endpoints Backend** (verificar existen):
```
GET    /api/v1/tenant/reconciliation/dashboard
GET    /api/v1/tenant/reconciliation/unmatched-transactions
GET    /api/v1/tenant/reconciliation/unpaid-invoices
POST   /api/v1/tenant/reconciliation/match
GET    /api/v1/tenant/reconciliation/suggestions
GET    /api/v1/tenant/reconciliation/history
```

---

#### 3. E-Invoicing Dashboard (Mejorar existente)
**Esfuerzo**: 1 día
**Valor**: ⭐⭐⭐⭐

**Archivos a mejorar**:
```
apps/tenant/src/modules/facturacion/
├── pages/
│   └── Einvoicing/ (NUEVO)
│       ├── Dashboard.tsx
│       ├── Status.tsx
│       └── Errors.tsx
└── components/
    └── Einvoicing/ (NUEVO)
        ├── StatusBadge.tsx
        ├── SubmissionTimeline.tsx
        └── ErrorDetails.tsx
```

**Funcionalidades**:
- ✅ Dashboard de envíos fiscales
- ✅ Estado en tiempo real (SRI/SII)
- ✅ Facturas pendientes de envío
- ✅ Facturas enviadas (autorizadas/rechazadas)
- ✅ Gestión de errores y reintentos
- ✅ Estadísticas y gráficos

---

### 🟡 PRIORIDAD MEDIA (Hacer después)

#### 4. Export - Exportaciones
**Esfuerzo**: 1-2 días
**Valor**: ⭐⭐⭐

**Archivos a crear**:
```
apps/tenant/src/modules/export/
├── manifest.ts
├── Routes.tsx
├── services.ts
├── types.ts
├── pages/
│   ├── Templates.tsx
│   ├── Jobs.tsx
│   └── History.tsx
└── components/
    ├── TemplateEditor.tsx
    ├── ExportForm.tsx
    └── JobStatus.tsx
```

**Funcionalidades**:
- ✅ Exportar cualquier módulo a Excel/CSV/PDF
- ✅ Plantillas de exportación personalizadas
- ✅ Programar exportaciones automáticas
- ✅ Historial de exportaciones
- ✅ Descargar archivos generados

**Endpoints Backend**:
```
GET    /api/v1/tenant/export/templates
POST   /api/v1/tenant/export/templates
POST   /api/v1/tenant/export/execute
GET    /api/v1/tenant/export/jobs
GET    /api/v1/tenant/export/download/{job_id}
```

---

#### 5. Webhooks - Integraciones
**Esfuerzo**: 1-2 días
**Valor**: ⭐⭐⭐

**Archivos a crear**:
```
apps/tenant/src/modules/webhooks/
├── manifest.ts
├── Routes.tsx
├── services.ts
├── types.ts
├── pages/
│   ├── Subscriptions.tsx
│   ├── Deliveries.tsx
│   └── Logs.tsx
└── components/
    ├── WebhookForm.tsx
    ├── DeliveryTimeline.tsx
    └── EventSelector.tsx
```

**Funcionalidades**:
- ✅ Configurar webhooks (URL, eventos, headers)
- ✅ Ver entregas (exitosas/fallidas)
- ✅ Reintentar entregas fallidas
- ✅ Logs detallados
- ✅ Test endpoint

**Endpoints Backend**:
```
GET    /api/v1/tenant/webhooks/subscriptions
POST   /api/v1/tenant/webhooks/subscriptions
PUT    /api/v1/tenant/webhooks/subscriptions/{id}
DELETE /api/v1/tenant/webhooks/subscriptions/{id}
GET    /api/v1/tenant/webhooks/deliveries
POST   /api/v1/tenant/webhooks/deliveries/{id}/retry
GET    /api/v1/tenant/webhooks/logs
POST   /api/v1/tenant/webhooks/test
```

---

### 🟢 PRIORIDAD BAJA (Opcional)

#### 6. AI Agent / Copilot
**Esfuerzo**: 3-5 días
**Valor**: ⭐⭐

**Nota**: Implementar cuando backend esté listo

#### 7. Templates
**Esfuerzo**: 1-2 días
**Valor**: ⭐⭐

**Funcionalidad**: Editor de plantillas (PDF, Email, etc.)

#### 8. Empresa (Settings)
**Esfuerzo**: 1 día
**Valor**: ⭐⭐

**Nota**: Probablemente ya está en settings

---

## 📦 PACKAGES COMPARTIDOS A CREAR

### 1. @packages/api-types
**Esfuerzo**: 1 día

**Propósito**: Types TypeScript generados desde backend

**Estructura**:
```typescript
// apps/packages/api-types/src/
export type Lead = {
  id: string
  name: string
  email: string
  phone: string
  status: LeadStatus
  source: string
  assigned_to?: string
  created_at: string
  updated_at: string
}

export type Opportunity = {
  id: string
  lead_id: string
  title: string
  value: number
  probability: number
  stage: OpportunityStage
  expected_close_date: string
  ...
}

// etc.
```

**Generación automática**:
```bash
# Script para generar types desde backend
pnpm run generate:types
```

---

### 2. @packages/api-client
**Esfuerzo**: 2 días

**Propósito**: Cliente API tipado para cada módulo

**Estructura**:
```typescript
// apps/packages/api-client/src/modules/crm.ts
import { Lead, Opportunity } from '@packages/api-types'
import { apiClient } from '../client'

export const crmApi = {
  leads: {
    list: (params?) => apiClient.get<Lead[]>('/crm/leads', { params }),
    get: (id: string) => apiClient.get<Lead>(`/crm/leads/${id}`),
    create: (data: Partial<Lead>) => apiClient.post<Lead>('/crm/leads', data),
    update: (id: string, data: Partial<Lead>) => apiClient.put<Lead>(`/crm/leads/${id}`, data),
    delete: (id: string) => apiClient.delete(`/crm/leads/${id}`),
  },
  opportunities: {
    // ...
  },
  dashboard: {
    getMetrics: () => apiClient.get('/crm/dashboard'),
  },
}
```

**Uso**:
```typescript
// En cualquier componente
import { crmApi } from '@packages/api-client'

const leads = await crmApi.leads.list({ status: 'open' })
```

---

### 3. @packages/validations
**Esfuerzo**: 1 día

**Propósito**: Validaciones Zod compartidas

**Estructura**:
```typescript
// apps/packages/validations/src/crm.ts
import { z } from 'zod'

export const leadSchema = z.object({
  name: z.string().min(1, 'Nombre requerido'),
  email: z.string().email('Email inválido'),
  phone: z.string().optional(),
  status: z.enum(['new', 'contacted', 'qualified', 'lost']),
  source: z.string(),
  assigned_to: z.string().optional(),
})

export type LeadInput = z.infer<typeof leadSchema>
```

**Uso**:
```typescript
// En formulario
import { leadSchema } from '@packages/validations'

const form = useForm({
  resolver: zodResolver(leadSchema),
})
```

---

## 🧰 COMPONENTES COMPARTIDOS A CREAR

### apps/packages/ui/src/modules/

```
modules/
├── crm/
│   ├── LeadCard.tsx
│   ├── OpportunityCard.tsx
│   ├── PipelineStage.tsx
│   └── ActivityTimeline.tsx
├── reconciliation/
│   ├── TransactionCard.tsx
│   ├── MatchSuggestions.tsx
│   └── ReconciliationSummary.tsx
└── einvoicing/
    ├── StatusBadge.tsx
    ├── SubmissionTimeline.tsx
    └── ErrorDetails.tsx
```

---

## 📅 CRONOGRAMA SUGERIDO

### Semana 1: CRM + Packages Base
- **Día 1-2**: Crear @packages/api-types y @packages/api-client
- **Día 3-5**: Implementar módulo CRM completo

### Semana 2: Reconciliation + E-Invoicing
- **Día 1-3**: Implementar módulo Reconciliation
- **Día 4-5**: Mejorar E-Invoicing dashboard

### Semana 3: Export + Webhooks
- **Día 1-2**: Implementar módulo Export
- **Día 3-4**: Implementar módulo Webhooks
- **Día 5**: Testing y ajustes

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Por cada módulo nuevo:

#### Backend
- [ ] Verificar que existen todos los endpoints necesarios
- [ ] Verificar schemas Pydantic
- [ ] Verificar permisos y autenticación
- [ ] Documentar API (OpenAPI/Swagger)

#### Frontend
- [ ] Crear estructura de carpetas
- [ ] Implementar manifest.ts
- [ ] Crear services.ts (usando @packages/api-client)
- [ ] Definir types.ts (usando @packages/api-types)
- [ ] Crear Routes.tsx
- [ ] Implementar páginas principales
- [ ] Crear componentes reutilizables
- [ ] Agregar al ModuleLoader
- [ ] Agregar permisos al sistema
- [ ] Testing (unit + integration)

#### Documentación
- [ ] Guía de usuario
- [ ] Guía de desarrollador
- [ ] Screenshots/demos
- [ ] Casos de uso

---

## 🚫 ANTI-PATRONES A EVITAR

### ❌ NO HACER:

1. **Hardcodear rutas API**
   ```typescript
   // ❌ MAL
   const response = await fetch('http://localhost:8000/api/v1/tenant/crm/leads')

   // ✅ BIEN
   const leads = await crmApi.leads.list()
   ```

2. **Castings innecesarios**
   ```typescript
   // ❌ MAL
   const id = String(lead.id)
   const value = Number(opportunity.value)

   // ✅ BIEN - usar types correctos desde backend
   const id: string = lead.id
   const value: number = opportunity.value
   ```

3. **Duplicar validaciones**
   ```typescript
   // ❌ MAL - validación duplicada en cada formulario
   const schema = z.object({ name: z.string().min(1) })

   // ✅ BIEN - usar schema compartido
   import { leadSchema } from '@packages/validations'
   ```

4. **Duplicar componentes**
   ```typescript
   // ❌ MAL - copiar componentes entre módulos

   // ✅ BIEN - mover a @packages/ui
   import { LeadCard } from '@packages/ui/modules/crm'
   ```

5. **No usar tipos**
   ```typescript
   // ❌ MAL
   const leads: any[] = await crmApi.leads.list()

   // ✅ BIEN
   const leads: Lead[] = await crmApi.leads.list()
   ```

---

## 🎯 PRÓXIMA ACCIÓN INMEDIATA

**Comenzar por orden de prioridad**:

1. ✅ **Ya hecho**: Auditoría completa
2. 🔄 **En progreso**: Estructura CRM manifest
3. 📋 **Siguiente**:
   - Crear @packages/api-types
   - Crear @packages/api-client
   - Implementar módulo CRM completo

---

**Estado**: 📋 PLAN COMPLETADO - LISTO PARA EJECUTAR
**Próximo paso**: Crear packages compartidos (@packages/api-types, @packages/api-client)
