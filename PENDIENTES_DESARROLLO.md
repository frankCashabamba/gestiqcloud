# Análisis de Pendientes - Backend y Frontend

**Fecha**: Enero 2025  
**Proyecto**: GestiQCloud ERP/CRM Multi-Tenant

---

## 📊 Resumen Ejecutivo

### Backend
- **Estado**: 90% completo ✅
- **Endpoints API**: ~150 implementados
- **Faltantes**: 10% (principalmente frontend de módulos existentes)

### Frontend
- **Estado**: 50% completo ⚠️
- **Módulos con UI**: 40% (8 de 15)
- **Faltantes críticos**: POS UI, Inventario UI, algunos módulos sin frontend

---

## 🔴 CRÍTICO - Debe completarse para MVP

### 1. Frontend POS/TPV ⚠️ CRÍTICO
**Backend**: ✅ 100% (900 líneas - pos.py)  
**Frontend**: ❌ 0%

**Endpoints disponibles**:
- ✅ `POST /api/v1/pos/shifts` (abrir/cerrar turno)
- ✅ `POST /api/v1/pos/receipts` (crear ticket)
- ✅ `POST /api/v1/pos/receipts/{id}/pay` (cobrar)
- ✅ `POST /api/v1/pos/receipts/{id}/to_invoice` (convertir a factura)
- ✅ `POST /api/v1/pos/receipts/{id}/refund` (devolución)
- ✅ `GET /api/v1/pos/receipts/{id}/print` (imprimir 58/80mm)

**Falta implementar**:
```
apps/tenant/src/modules/pos/
├── index.tsx                # Router
├── Dashboard.tsx            # Vista principal caja
├── ShiftManager.tsx         # Abrir/cerrar turno
├── TicketCreator.tsx        # Crear tickets
├── PaymentModal.tsx         # Cobro (efectivo, tarjeta, vale)
├── InvoiceConverter.tsx     # Ticket → Factura
├── RefundModal.tsx          # Devoluciones (YA EXISTE stub)
└── PrintPreview.tsx         # Vista previa impresión
```

**Tiempo estimado**: 3-4 días  
**Prioridad**: 🔴 CRÍTICA

---

### 2. Frontend Inventario ⚠️ CRÍTICO
**Backend**: ✅ 100%  
**Frontend**: ❌ 0%

**Endpoints disponibles**:
- ✅ Stock items, stock moves, warehouses

**Falta implementar**:
```
apps/tenant/src/modules/inventario/
├── index.tsx
├── StockList.tsx           # Lista de stock actual
├── StockMovesList.tsx      # Historial de movimientos
├── WarehousesList.tsx      # Gestión almacenes
└── AdjustmentForm.tsx      # Ajustes de inventario
```

**Tiempo estimado**: 2-3 días  
**Prioridad**: 🔴 CRÍTICA

---

### 3. Numeración Documental (Backend) ⚠️
**Estado**: ✅ 80% (servicio existe - numbering.py)  
**Falta**: Endpoints REST

**Implementar**:
```python
# apps/backend/app/routers/doc_series.py
GET    /api/v1/doc-series/              # Listar series
POST   /api/v1/doc-series/              # Crear serie
PUT    /api/v1/doc-series/{id}          # Actualizar
DELETE /api/v1/doc-series/{id}          # Eliminar
POST   /api/v1/doc-series/{id}/reset    # Resetear contador
```

**Tiempo estimado**: 2-3 horas  
**Prioridad**: 🟡 ALTA

---

## 🟡 IMPORTANTE - Completar para funcionalidad completa

### 4. E-factura Endpoints (Backend)
**Estado**: ✅ 95% (workers completos - 700 líneas)  
**Falta**: Endpoints REST

**Implementar**:
```python
# apps/backend/app/routers/einvoicing.py (expandir)
POST   /api/v1/einvoicing/send           # Enviar e-factura (✅ stub existe)
GET    /api/v1/einvoicing/status/{id}    # Estado (✅ stub existe)
GET    /api/v1/einvoicing/facturae/{id}/export  # Exportar XML
POST   /api/v1/einvoicing/sri/retry      # Reintentar SRI
GET    /api/v1/einvoicing/credentials    # Ver credenciales
PUT    /api/v1/einvoicing/credentials    # Actualizar certificados
```

**Tiempo estimado**: 4-6 horas  
**Prioridad**: 🟡 ALTA

---

### 5. Frontend E-factura
**Backend**: ✅ 95%  
**Frontend**: ❌ 0%

**Implementar**:
```
apps/tenant/src/modules/facturacion/
├── (ya existe List.tsx)
├── EInvoiceStatus.tsx      # Estado de e-facturas
├── CredentialsForm.tsx     # Config certificados
└── RetryPanel.tsx          # Reintentos fallidos
```

**Tiempo estimado**: 1-2 días  
**Prioridad**: 🟡 ALTA

---

### 6. Frontend Pagos Online
**Backend**: ✅ 100% (3 providers - 250 líneas)  
**Frontend**: ❌ 0%

**Implementar**:
```
apps/tenant/src/modules/pagos/
├── index.tsx
├── PaymentLinkGenerator.tsx  # Generar enlaces
├── PaymentsList.tsx          # Listado pagos
└── WebhookLogs.tsx           # Logs de webhooks
```

**Tiempo estimado**: 1 día  
**Prioridad**: 🟡 ALTA

---

## 🟢 MEJORAR - Módulos existentes con frontend básico

### 7. Módulos con Services pero sin UI completa

#### Clientes ⚠️
- **Backend**: ✅ CRUD completo
- **Frontend**: ✅ List.tsx existe
- **Falta**: Form.tsx, Detail.tsx

#### Proveedores ⚠️
- **Backend**: ✅ CRUD completo
- **Frontend**: ✅ List.tsx existe  
- **Falta**: Form.tsx, Detail.tsx

#### Compras ⚠️
- **Backend**: ✅ CRUD completo
- **Frontend**: ✅ List.tsx existe
- **Falta**: Form.tsx, Detail.tsx

#### Gastos ⚠️
- **Backend**: ✅ CRUD completo
- **Frontend**: ✅ List.tsx existe
- **Falta**: Form.tsx, Detail.tsx

#### Ventas ⚠️
- **Backend**: ✅ CRUD completo
- **Frontend**: ✅ List.tsx existe
- **Falta**: Form.tsx, Detail.tsx

#### Facturación ⚠️
- **Backend**: ✅ CRUD completo
- **Frontend**: ✅ List.tsx existe
- **Falta**: Form.tsx (crear factura completa), Detail.tsx

**Tiempo estimado por módulo**: 4-6 horas  
**Total**: 2-3 días para completar los 6  
**Prioridad**: 🟢 MEDIA

---

### 8. Contabilidad
**Backend**: ❌ No implementado (opcional SPEC-1)  
**Frontend**: ❌ No implementado

**Estado**: En carpeta pero vacío  
**Prioridad**: 🔵 BAJA (opcional para M3)

---

### 9. RRHH
**Backend**: ⚠️ Parcial (solo vacaciones)  
**Frontend**: ❌ No implementado

**Implementar**:
- Empleados CRUD
- Asistencia
- Nóminas básicas

**Tiempo estimado**: 1 semana  
**Prioridad**: 🔵 BAJA (post-MVP)

---

### 10. Finanzas (Caja/Bancos)
**Backend**: ⚠️ Stub (comentado en services.ts)  
**Frontend**: ❌ No implementado

**Implementar**:
- Movimientos de caja
- Conciliación bancaria
- Flujo de caja

**Tiempo estimado**: 1 semana  
**Prioridad**: 🔵 BAJA (post-MVP)

---

## 📋 Checklist de Completitud por Módulo

### Backend Routers Disponibles
- [x] POS (900 líneas) ✅
- [x] Payments (250 líneas) ✅
- [x] SPEC-1 Daily Inventory (220 líneas) ✅
- [x] SPEC-1 Purchase (160 líneas) ✅
- [x] SPEC-1 Milk Record (150 líneas) ✅
- [x] SPEC-1 Importer (100 líneas) ✅
- [x] E-invoicing (700 líneas workers, stub REST) ⚠️
- [x] Imports (genérico) ✅
- [x] Roles ✅
- [x] Categorías ✅
- [x] Listados Generales ✅
- [ ] Doc Series (solo servicio) ⚠️
- [ ] Clientes/Proveedores (falta router REST) ⚠️
- [ ] Compras/Gastos (falta router REST) ⚠️
- [ ] Ventas (falta router REST) ⚠️
- [ ] Facturación (partial) ⚠️

**Completitud Backend**: 85% ✅

---

### Frontend Módulos Disponibles
- [x] Panadería (100% completo - 7 componentes) ✅
- [x] Importador (genérico) ✅
- [x] Settings ✅
- [x] Usuarios ✅
- [x] Clientes (solo List) ⚠️
- [x] Proveedores (solo List) ⚠️
- [x] Compras (solo List) ⚠️
- [x] Gastos (solo List) ⚠️
- [x] Ventas (solo List) ⚠️
- [x] Facturación (solo List) ⚠️
- [ ] POS ❌ CRÍTICO
- [ ] Inventario ❌ CRÍTICO
- [ ] E-factura ❌
- [ ] Pagos Online ❌
- [ ] Contabilidad ❌
- [ ] RRHH ❌
- [ ] Finanzas ❌

**Completitud Frontend**: 45% ⚠️

---

## 🎯 Plan de Acción Recomendado

### Sprint 1 (1 semana) - CRÍTICO
**Objetivo**: MVP funcional para panadería

1. **Frontend POS** (3 días)
   - Dashboard caja
   - Crear tickets
   - Cobro (efectivo, tarjeta)
   - Convertir a factura

2. **Frontend Inventario** (2 días)
   - Lista de stock
   - Movimientos
   - Ajustes

3. **Endpoints Doc Series** (0.5 días)
   - CRUD completo REST

**Resultado**: POS + Inventario operativos ✅

---

### Sprint 2 (1 semana) - IMPORTANTE
**Objetivo**: E-factura y pagos operativos

1. **Endpoints E-factura** (1 día)
   - Completar REST API
   - Gestión credenciales

2. **Frontend E-factura** (2 días)
   - Estado e-facturas
   - Config certificados
   - Reintentos

3. **Frontend Pagos** (1 día)
   - Generar enlaces
   - Ver estado pagos

4. **Completar Forms básicos** (1 día)
   - Clientes Form
   - Proveedores Form

**Resultado**: E-factura y pagos online operativos ✅

---

### Sprint 3 (1 semana) - MEJORAR
**Objetivo**: Completar módulos básicos

1. **Forms restantes** (3 días)
   - Compras, Gastos, Ventas, Facturación
   - 6 módulos × 4-6 horas c/u

2. **Testing** (2 días)
   - Tests unitarios críticos
   - Tests E2E básicos

**Resultado**: Todos los módulos básicos con UI completa ✅

---

## 📊 Métricas Actuales

### Backend
| Categoría | Total | Implementado | % |
|-----------|-------|--------------|---|
| Routers | 20 | 17 | 85% |
| Endpoints | 150+ | 135+ | 90% |
| Models | 50+ | 50+ | 100% |
| Services | 20+ | 18+ | 90% |

### Frontend
| Categoría | Total | Implementado | % |
|-----------|-------|--------------|---|
| Módulos | 15 | 7 | 47% |
| Services | 15 | 10 | 67% |
| List Views | 15 | 11 | 73% |
| Forms | 15 | 4 | 27% |
| Detail Views | 15 | 2 | 13% |

---

## 🎓 Próximas Mejoras (Post-MVP)

### M2 - Offline First Real
- ElectricSQL integración
- PGlite para offline total
- Sincronización diferencial

### M3 - Producción Avanzada
- Production Orders completas
- Backflush automático activado
- Costeo por lotes

### M4 - Reporting Avanzado
- Dashboards personalizables
- Exportación PDF/Excel mejorada
- Gráficos interactivos (Chart.js)

### M5 - Mobile App
- Capacitor para Android/iOS
- Bluetooth printing nativo
- Scanner códigos de barras

---

## 📚 Archivos a Crear (Estimación)

### Backend (10 archivos)
- `routers/doc_series.py` (150 líneas)
- `routers/clientes.py` (200 líneas)
- `routers/proveedores.py` (200 líneas)
- `routers/compras.py` (200 líneas)
- `routers/gastos.py` (200 líneas)
- `routers/ventas.py` (200 líneas)
- `routers/einvoicing.py` (expandir +100 líneas)
- `schemas/clientes.py` (100 líneas)
- `schemas/proveedores.py` (100 líneas)
- etc.

**Total estimado**: ~2,000 líneas

### Frontend (40+ archivos)
**POS** (8 archivos, ~1,500 líneas):
- index.tsx, Dashboard.tsx, ShiftManager.tsx, TicketCreator.tsx, PaymentModal.tsx, InvoiceConverter.tsx, RefundModal.tsx, PrintPreview.tsx

**Inventario** (4 archivos, ~800 líneas):
- index.tsx, StockList.tsx, StockMovesList.tsx, AdjustmentForm.tsx

**E-factura** (3 archivos, ~600 líneas):
- EInvoiceStatus.tsx, CredentialsForm.tsx, RetryPanel.tsx

**Pagos** (3 archivos, ~500 líneas):
- index.tsx, PaymentLinkGenerator.tsx, PaymentsList.tsx

**Forms básicos** (18 archivos, ~3,000 líneas):
- 6 módulos × (Form.tsx + Detail.tsx + schemas)

**Total estimado**: ~6,400 líneas

---

## ✅ Conclusión

### Estado Actual
- **Backend**: 90% completo - Muy sólido ✅
- **Frontend**: 45% completo - Necesita trabajo ⚠️

### Crítico para MVP
1. Frontend POS (3 días)
2. Frontend Inventario (2 días)
3. Endpoints Doc Series (0.5 días)

**Total Sprint 1**: 5.5 días de trabajo

### Recomendación
Priorizar Sprint 1 para tener un MVP funcional de panadería con POS e inventario operativos. Los demás módulos pueden completarse incrementalmente.

**Esfuerzo total estimado para completar 100%**: 3-4 semanas

---

**Versión**: 1.0  
**Fecha**: Enero 2025  
**Próxima revisión**: Post Sprint 1
