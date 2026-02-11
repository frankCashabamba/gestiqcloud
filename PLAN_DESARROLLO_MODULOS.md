# Plan Desarrollo Módulos - GestiqCloud 2026

**Estado actual:** 23 módulos, solo 11 tests (importer/sales/pos). Binario: "parcialmente completo" → "profesional y vendible"

---

## FASE 1: FUNDACIÓN (Semanas 1-2)
### Objs: Infraestructura compartida, seguridad base, tests

**1.1 Seguridad y permisos**
- [x] Esquema de permisos (RBAC) en frontend
  - [x] `apps/tenant/src/contexts/PermissionsContext.tsx` (CREADO)
  - [x] HOC protector de rutas: `ProtectedRoute.tsx` (CREADO)
  - [x] Hook: `usePermission()` (CREADO)
  - [x] Hook: `usePermissionLabel()` (CREADO)
  - [x] Componente: `ProtectedButton.tsx` (CREADO)
  - [x] Componente: `PermissionDenied.tsx` (CREADO)
  - [x] Caché: `permissionsCache.ts` (CREADO)
  - [x] i18n: `locales/es/permissions.json` + `en/permissions.json` (CREADO)
  - [x] Integración en AuthContext (HECHO)
- [ ] Validación de entrada en formularios (Zod/valibot)
- [ ] Rate limiting en cliente (debounce en búsquedas/filtros)
- [ ] Auditoría cliente: logs de cambios críticos en localStorage

**1.2 Internacionalización (i18n)**
- [ ] Revisar `apps/tenant/src/i18n/` y `locales/`
- [ ] Namespace por módulo (ej: `modules.billing.forms.invoice`)
- [ ] Agregar es/en/pt en todos los módulos
- [ ] Tool: traductor de clave → valor

**1.3 Base de tests**
- [ ] Configurar Playwright para E2E críticos
- [ ] Scaffolds de tests unitarios + integración (vitest)
- [ ] Fixtures de datos por país (CFDI/SRI/SII)
- [ ] CI/CD: ejecutar tests en pull requests

**1.4 Logging y observabilidad**
- [ ] Logger estructurado (winston/pino en backend ya; espejo en cliente)
- [ ] Traces en módulos críticos (Billing, Finanzas, E-invoicing)
- [ ] Dashboard de logs/métricas (opcional: integrar con DataDog/New Relic)

---

## FASE 2: MÓDULOS CRÍTICOS (Semanas 3-5)

### 2.1 Einvoicing (E-facturación)
**Brecha:** solo placeholder en frontend; backend listo

- [ ] **UI:**
  - `modules/einvoicing/pages/EinvoicingDashboard.tsx` (listar env íos)
  - Form envío: `modules/einvoicing/components/SendEinvoiceForm.tsx`
  - Visor XML/PDF: `modules/einvoicing/components/EinvoiceViewer.tsx`
  - Estados: pending → sent → verified → error → retry
  - Integraciones: CFDI (MX), SRI (EC), SII (CL), DAFI (CO)

- [ ] **Lógica:**
  - Hook: `useEinvoiceActions()` → POST /einvoicing/send con estado
  - Manejo errores: reintentos automáticos, SLA alertas
  - Webhook verificación: firma HMAC
  - Descargas: PDF/XML con auditoría (quién descargó)

- [ ] **Tests:**
  - E2E: flujo completo (crear factura → enviar → verificar → descargar)
  - Contract tests con backend
  - Por país: validaciones específicas

### 2.2 Reconciliation (Conciliación)
**Brecha:** backend listo, frontend solo placeholder

- [ ] **UI:**
  - Dashboard: `modules/reconciliation/pages/ReconciliationDashboard.tsx`
  - Tabla de transacciones vs facturas (con fuzzy match)
  - Sugerencias automáticas: `ReconciliationSuggestions.tsx`
  - Match manual: drag&drop o checkbox
  - Reporte de diferencias: `DifferenceReport.tsx`

- [ ] **Lógica:**
  - Hook: `useReconciliation()` → GET suggestions, POST match, POST undo
  - Estados: unmatched → suggested → matched → disputed
  - Bulk reconciliation: procesar 1000+ transacciones
  - Reversiones y auditoría

- [ ] **Tests:**
  - E2E: reconocer + coincidir + reportar
  - Performance: 1000+ filas
  - Conflictos: múltiples usuarios, race conditions

### 2.3 Billing (mejora: validaciones fiscales)
**Brecha:** completo pero sin validaciones país-específicas + rollback offline

- [ ] **Validaciones fiscales:**
  - MX: CFDI folio/serie, RFC, retenciones (ISR/IVA)
  - EC: RUC, números secuencial/SRI, IVA regional
  - CL: RUT, numeración correlativa, DTE timbrado
  - CO: RES número, IVA diferenciado, retenciones
  - Hooks: `useCountryValidation(country)` → validadores

- [ ] **Offline sync (mejora):**
  - Estados retry: pending → synced → conflict
  - Rollback seguro: versioning + transaction logs
  - Reconciliación automática
  - Indicador visual: "3 cambios sin sincronizar"

- [ ] **UI/UX accesible:**
  - ARIA labels en formularios/tablas
  - Contraste ≥ 4.5:1 (WCAG AA)
  - Keyboard nav: Tab/Enter en listas
  - Estados vacíos: mensajes claros

- [ ] **Tests:**
  - E2E: crear factura → pagar → sincronizar
  - Offline: desconectar, cambiar, reconectar
  - Validaciones país por país

---

## FASE 3: MÓDULOS SECUNDARIOS (Semanas 6-7)

Para cada módulo: Sales, Purchases, Inventory, Expenses, Customers, Suppliers, HR, Finances, Accounting, Reportes, Settings, Usuarios, POS, Produccion

- [ ] **Permisos:** cada ruta verificable por `usePermission()`
- [ ] **Paginación:** todas las listas > 50 filas
- [ ] **Filtros y búsqueda:** debounced, 0.5s max
- [ ] **Manejo errores:**
  - Formularios: validación inline + submits con retry
  - Tablas: load states, error states, empty states
  - Operaciones batch: progress + cancel
- [ ] **i18n:** español/inglés minimum
- [ ] **Tests:** 2 E2E por módulo (flujo crear/editar/eliminar)

**Subprioridad:**
1. **Sales** (→ facturación) 
2. **Purchases** (→ pagos)
3. **Inventory** (gestión stock)
4. **Customers/Suppliers** (catálogos)
5. Resto

---

## FASE 4: OBSERVABILIDAD Y CALIDAD (Semana 8)

- [ ] **Monitoreo Celery/offline:**
  - Alertas: tareas fallidas > 3 intentos
  - Dashboard: cola, latencia, errores/min
  - Dead letter queue: tareas no procesables
  
- [ ] **Cobertura tests:**
  - Meta: 70% unitarios, 100% flujos críticos E2E
  - Report: `npm run test:coverage`
  
- [ ] **Performance budgets:**
  - Lazy load modules (Vite dynamic imports)
  - Code splitting por módulo
  - Lighthouse: performance ≥ 80

- [ ] **Auditoría y seguridad:**
  - Logging de acciones críticas: quién editó qué, cuándo
  - Encriptación sensibles en localStorage (datos offline)
  - OWASP Top 10: XSS (sanitize HTML), CSRF (tokens), SQL injection (prepared)

---

## FASE 5: COMERCIALIZACIÓN Y DEPLOYMENT (Semana 9)

- [ ] **Feature flags** por tier (Free/Pro/Enterprise)
  - `useFeature('einvoicing')` en componentes
  - Backend: checks en endpoints
  
- [ ] **Documentación:**
  - Manual usuario: screenshots, flows
  - Runbooks ops: backups, SSL, scaling
  - Go-live checklist: permisos, datos, webhooks, alertas
  
- [ ] **Branding:**
  - Logos/colores configurable por tenant
  - White label: remover "GestiqCloud" si es B2B reseller
  
- [ ] **Planes y facturación:**
  - Mapear features → tiers
  - Usage billing (API calls, storage)
  - Límites soft (warning) y hard (block)

---

## Dependencias críticas

```
Permisos (1.1) → Todas las rutas
i18n (1.2) → Todos los módulos
Tests (1.3) → FASE 2, 3, 4
Einvoicing (2.1) → Reportes, Finanzas
Reconciliation (2.2) → Billing, Finanzas
Billing mejorado (2.3) → Payments, Einvoicing, Taxes
Módulos secundarios (3) → Reportes finales
```

---

## Métrica de éxito

**Hito 1 (Semana 3):** Permisos, i18n, tests base → 0 hardcodes, 1-2 tests por módulo
**Hito 2 (Semana 5):** Einvoicing + Reconciliation → 95% flujos E2E pasando
**Hito 3 (Semana 7):** Todos módulos con permisos, paginación, errores
**Hito 4 (Semana 8):** 70% cobertura tests, alertas, dashboards
**Hito 5 (Semana 9):** Documentación, feature flags, go-live ready

---

## Próximo paso

¿Comenzamos con **FASE 1.1 (Permisos)**? Te ayudaré a:
1. Diseñar esquema de permisos
2. Implementar PermissionsContext + HOCs
3. Proteger rutas en cada módulo
4. Ejemplos con Billing + Sales
