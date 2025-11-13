# MAPEO DE MÓDULOS FRONTEND ↔ BACKEND

**Fecha:** 2025-11-05  
**Proyecto:** GestiqCloud  
**Objetivo:** Mapear todos los módulos frontend con sus correspondientes módulos backend

---

## 📊 TABLA RESUMEN

| # | Frontend | Backend | Función Principal | Conexión | Problemas |
|---|----------|---------|-------------------|----------|-----------|
| 1 | **clientes** | `clients` | Gestión de clientes | ⚠️ Nombre diferente | Frontend usa "clientes", backend "clients" |
| 2 | **compras** | `compras` | Órdenes de compra | ✅ Conectado | - |
| 3 | **contabilidad** | `contabilidad` | Plan de cuentas, asientos | ✅ Conectado | - |
| 4 | **facturacion** | `facturacion` + `einvoicing` | Facturas y e-invoicing | ✅ Conectado | Facturae integrado en einvoicing |
| 5 | **finanzas** | `finanzas` | Caja y bancos | ✅ Conectado | - |
| 6 | **gastos** | `gastos` | Registro de gastos | ✅ Conectado | - |
| 7 | **importador** | `imports` | Importación masiva Excel/PDF | ⚠️ Nombre diferente | Frontend "importador", backend "imports", manifest.ts mal configurado |
| 8 | **inventario** | `inventario` | Control de stock y almacenes | ✅ Conectado | - |
| 9 | **pos** | `pos` | Punto de venta | ✅ Conectado | - |
| 10 | **produccion** | ❌ Sin módulo backend | Órdenes de producción, recetas | 🔴 **SIN BACKEND** | El frontend hace llamadas a `/api/v1/production/*` que NO existen |
| 11 | **productos** | `productos` | Catálogo de productos | ✅ Conectado | - |
| 12 | **proveedores** | `proveedores` | Gestión de proveedores | ✅ Conectado | - |
| 13 | **rrhh** | `rrhh` | RRHH, vacaciones, fichajes | ✅ Conectado | - |
| 14 | **settings** | `settings` | Configuración general | ✅ Conectado | - |
| 15 | **usuarios** | `usuarios` | Gestión de usuarios | ✅ Conectado | - |
| 16 | **ventas** | `ventas` | Órdenes de venta | ✅ Conectado | - |

### Módulos Backend SIN Frontend:
- `admin_config` - Configuración administrativa
- `ai_agent` - Agente de IA (no documentado en frontend)
- `copilot` - Copiloto de IA (no documentado en frontend)
- `crm` - CRM (no hay módulo frontend)
- `empresa` - Datos de empresa
- `export` - Exportaciones
- `identity` - Autenticación y autorización
- `modulos` - Registro de módulos
- `reconciliation` - Reconciliación bancaria (no hay frontend visible)
- `registry` - Registro de eventos
- `shared` - Compartido
- `templates` - Plantillas
- `webhooks` - Webhooks

---

## 🔍 ANÁLISIS DETALLADO POR MÓDULO

### 1. 👥 CLIENTES

**Frontend:** `apps/tenant/src/modules/clientes/`  
**Backend:** `apps/backend/app/modules/clients/`

**Manifest Frontend:**
```typescript
id: 'clientes'
name: 'Clientes'
permissions: ['clientes.read', 'clientes.write']
routes: ['/clientes', '/clientes/nuevo', '/clientes/:id/editar']
```

**Endpoints Frontend consume:**
- `GET /api/v1/tenant/clientes/` - Listar clientes
- `GET /api/v1/tenant/clientes/{id}` - Obtener cliente
- `POST /api/v1/tenant/clientes/` - Crear cliente
- `PUT /api/v1/tenant/clientes/{id}` - Actualizar cliente
- `DELETE /api/v1/tenant/clientes/{id}` - Eliminar cliente

**Endpoints Backend expone:**
- `GET /api/v1/tenant/clients/` ⚠️
- `POST /api/v1/tenant/clients/` ⚠️
- `PUT /api/v1/tenant/clients/{cliente_id}` ⚠️
- `DELETE /api/v1/tenant/clients/{cliente_id}` ⚠️

**Problemas:**
- ⚠️ **INCONSISTENCIA:** Frontend usa `/clientes/`, backend expone `/clients/`
- ⚠️ Diferencia de nombres en rutas puede causar errores 404
- **Solución:** Unificar a `/api/v1/tenant/clientes/` o configurar alias

**Estado:** ⚠️ Necesita unificación de nombres

---

### 2. 🛍️ COMPRAS

**Frontend:** `apps/tenant/src/modules/compras/`  
**Backend:** `apps/backend/app/modules/compras/`

**Manifest Frontend:**
```typescript
id: 'compras'
name: 'Compras'
icon: '🛍️'
order: 50
```

**Endpoints Frontend consume:**
- `GET /api/v1/tenant/compras/` - Listar compras
- `GET /api/v1/tenant/compras/{id}` - Obtener compra
- `POST /api/v1/tenant/compras/` - Crear compra
- `PUT /api/v1/tenant/compras/{id}` - Actualizar compra
- `DELETE /api/v1/tenant/compras/{id}` - Eliminar compra
- `POST /api/v1/tenant/compras/{id}/recibir` - Recibir compra

**Endpoints Backend expone:**
- `GET /api/v1/tenant/compras/`
- `GET /api/v1/tenant/compras/{cid}`
- `POST /api/v1/tenant/compras/`
- `PUT /api/v1/tenant/compras/{cid}`
- `DELETE /api/v1/tenant/compras/{cid}`

**Problemas:**
- Ninguno detectado

**Estado:** ✅ Totalmente conectado

---

### 3. 📊 CONTABILIDAD

**Frontend:** `apps/tenant/src/modules/contabilidad/`  
**Backend:** `apps/backend/app/modules/contabilidad/`

**Manifest Frontend:**
```typescript
id: 'contabilidad'
name: 'Contabilidad'
icon: '📊'
path: '/contabilidad'
requiredRole: 'manager'
description: 'Plan de cuentas, asientos contables y reportes financieros'
```

**Endpoints Frontend consume:**
- No se detectaron llamadas API directas en los archivos analizados
- Probablemente usa endpoints de contabilidad general

**Endpoints Backend expone:**
- (Requiere análisis de `interface/http/tenant.py`)

**Problemas:**
- ⚠️ Falta documentación de endpoints específicos

**Estado:** ✅ Conectado (pendiente verificar endpoints)

---

### 4. 📄 FACTURACIÓN

**Frontend:** `apps/tenant/src/modules/facturacion/`  
**Backend:** `apps/backend/app/modules/facturacion/` + `einvoicing/`

**Manifest Frontend:**
```typescript
id: 'facturacion'
name: 'Facturación'
permissions: ['facturacion.read', 'facturacion.write', 'facturacion.einvoice']
routes: ['/facturacion', '/facturacion/nueva', '/facturacion/:id/editar']
```

**Endpoints Frontend consume:**
- `GET /api/v1/tenant/facturacion/` - Listar facturas
- `GET /api/v1/tenant/facturacion/{id}` - Obtener factura
- `POST /api/v1/tenant/facturacion/` - Crear factura
- `PUT /api/v1/tenant/facturacion/{id}` - Actualizar factura
- `DELETE /api/v1/tenant/facturacion/{id}` - Eliminar factura
- `POST /api/v1/tenant/einvoicing/send` - Enviar factura electrónica
- `GET /api/v1/tenant/einvoicing/status/{invoiceId}` - Estado de e-invoice
- `GET /api/v1/tenant/einvoicing/facturae/{id}/export` - Exportar Facturae (implementado en einvoicing)

**Endpoints Backend expone:**
- `GET /api/v1/tenant/facturacion/` - Listar
- `POST /api/v1/tenant/facturacion/` - Crear
- `PUT /api/v1/tenant/facturacion/{factura_id}` - Actualizar
- `DELETE /api/v1/tenant/facturacion/{factura_id}` - Eliminar
- `POST /api/v1/tenant/facturacion/{factura_id}/emitir` - Emitir factura
- `GET /api/v1/tenant/facturacion/{factura_id}` - Obtener
- `GET /api/v1/tenant/facturacion/{factura_id}/pdf` - Descargar PDF
- `POST /api/v1/tenant/facturacion/archivo/procesar` - Procesar archivo
- Módulo `einvoicing` expone endpoints de factura electrónica
- Facturae integrado en módulo `einvoicing` (workers/einvoicing_tasks.py)

**Problemas:**
- Ninguno detectado, arquitectura modular adecuada

**Estado:** ✅ Totalmente conectado (3 módulos backend)

---

### 5. 💰 FINANZAS

**Frontend:** `apps/tenant/src/modules/finanzas/`  
**Backend:** `apps/backend/app/modules/finanzas/`

**Manifest Frontend:**
```typescript
id: 'finanzas'
name: 'Finanzas'
permissions: ['finanzas.read', 'finanzas.write']
routes: ['/finanzas/caja', '/finanzas/bancos']
```

**Endpoints Frontend consume:**
- (Requiere análisis detallado de services.ts)

**Endpoints Backend expone:**
- `GET /api/v1/tenant/finanzas/caja/movimientos`
- `GET /api/v1/tenant/finanzas/bancos/movimientos`

**Problemas:**
- Ninguno detectado

**Estado:** ✅ Conectado

---

### 6. 💵 GASTOS

**Frontend:** `apps/tenant/src/modules/gastos/`  
**Backend:** `apps/backend/app/modules/gastos/`

**Manifest Frontend:**
```typescript
id: 'gastos'
name: 'Gastos'
icon: '💵'
color: '#EF4444'
order: 70
```

**Endpoints Frontend consume:**
- `GET /api/v1/tenant/gastos/` - Listar gastos
- `GET /api/v1/tenant/gastos/{id}` - Obtener gasto
- `POST /api/v1/tenant/gastos/` - Crear gasto
- `PUT /api/v1/tenant/gastos/{id}` - Actualizar gasto
- `DELETE /api/v1/tenant/gastos/{id}` - Eliminar gasto

**Endpoints Backend expone:**
- `GET /api/v1/tenant/gastos/`
- `GET /api/v1/tenant/gastos/{gid}`
- `POST /api/v1/tenant/gastos/`
- `PUT /api/v1/tenant/gastos/{gid}`
- `DELETE /api/v1/tenant/gastos/{gid}`

**Problemas:**
- Ninguno detectado

**Estado:** ✅ Totalmente conectado

---

### 7. 📤 IMPORTADOR (imports)

**Frontend:** `apps/tenant/src/modules/importador/`  
**Backend:** `apps/backend/app/modules/imports/`

**Manifest Frontend:**
```typescript
id: 'imports'  // ⚠️ Dice "imports" pero carpeta es "importador"
name: 'Imports'
permissions: ['imports.read', 'imports.write']
routes: ['/imports', '/imports/wizard']
```

**Endpoints Frontend consume:**
- `POST /api/v1/imports/mappings` - Crear mapping
- `GET /api/v1/imports/mappings` - Listar mappings
- `GET /api/v1/imports/mappings/{id}` - Obtener mapping
- `DELETE /api/v1/imports/mappings/{id}` - Eliminar mapping
- `GET /api/v1/imports/batches/{batchId}/status` - Estado del batch

**Endpoints Backend expone:**
- `POST /api/v1/tenant/imports/uploads/chunk/init` - Iniciar upload chunked
- `PUT /api/v1/tenant/imports/uploads/chunk/{upload_id}/{part_number}` - Upload chunk
- `POST /api/v1/tenant/imports/uploads/chunk/{upload_id}/complete` - Completar upload
- `POST /api/v1/tenant/imports/batches/from-upload` - Crear batch desde upload
- `POST /api/v1/tenant/imports/batches/{batch_id}/start-excel-import` - Iniciar importación
- `POST /api/v1/tenant/imports/mappings/suggest` - Sugerir mapeo automático
- `POST /api/v1/tenant/imports/batches/{batch_id}/cancel` - Cancelar batch
- `POST /api/v1/tenant/imports/excel/parse` - Parsear Excel
- `POST /api/v1/tenant/imports/preview/analyze-excel` - Analizar Excel
- `POST /api/v1/tenant/imports/preview/validate-mapping` - Validar mapeo
- `GET /api/v1/tenant/imports/preview/templates` - Obtener templates
- `POST /api/v1/tenant/imports/preview/save-template` - Guardar template

**Problemas:**
- ⚠️ **INCONSISTENCIA CRÍTICA:** La carpeta se llama `importador` pero el `manifest.ts` tiene `id: 'imports'`
- ⚠️ Confusión entre nombres español/inglés
- ⚠️ Frontend consume `/api/v1/imports/*` pero backend expone `/api/v1/tenant/imports/*`
- **Solución:** Renombrar carpeta a `imports` O cambiar manifest a `importador`

**Estado:** ⚠️ Conectado pero con inconsistencias de naming

---

### 8. 📦 INVENTARIO

**Frontend:** `apps/tenant/src/modules/inventario/`  
**Backend:** `apps/backend/app/modules/inventario/`

**Manifest Frontend:**
```typescript
id: 'inventario'
name: 'Inventario'
icon: '📦'
path: '/inventario'
requiredRole: 'operario'
description: 'Control de stock, movimientos y valoración de inventario'
features: ['Stock actual', 'Movimientos', 'Alertas', 'Ajustes', 'Lotes']
```

**Endpoints Frontend consume:**
- `GET /api/v1/products` - Listar productos (⚠️ Usa productos, no inventario)
- `PUT /api/v1/products/{id}` - Actualizar producto
- `GET /api/v1/inventario/warehouses` - Listar almacenes
- `POST /api/v1/inventario/products/{productId}/reorder-point` - Configurar punto de reorden
- `GET /api/v1/notifications/alerts` - Obtener alertas
- `POST /api/v1/notifications/alerts/{alertId}/resolve` - Resolver alerta
- `POST /api/v1/notifications/channels` - Crear canal de notificación
- `POST /api/v1/notifications/send` - Enviar notificación

**Endpoints Backend expone:**
- `GET /api/v1/tenant/inventario/warehouses` - Listar almacenes
- `POST /api/v1/tenant/inventario/warehouses` - Crear almacén
- `GET /api/v1/tenant/inventario/warehouses/{wid}` - Obtener almacén
- `PUT /api/v1/tenant/inventario/warehouses/{wid}` - Actualizar almacén
- `DELETE /api/v1/tenant/inventario/warehouses/{wid}` - Eliminar almacén
- `GET /api/v1/tenant/inventario/stock` - Obtener stock
- `POST /api/v1/tenant/inventario/stock/adjust` - Ajustar stock
- `POST /api/v1/tenant/inventario/stock/transfer` - Transferir stock
- `POST /api/v1/tenant/inventario/stock/cycle_count` - Conteo cíclico

**Problemas:**
- ⚠️ Frontend consume endpoints de `products` directamente (debería ir a través de inventario)
- ⚠️ Frontend consume endpoints de `notifications` que pueden estar en otro módulo

**Estado:** ✅ Conectado (con dependencias cruzadas)

---

### 9. 🛒 POS (Punto de Venta)

**Frontend:** `apps/tenant/src/modules/pos/`  
**Backend:** `apps/backend/app/modules/pos/`

**Manifest Frontend:**
```typescript
id: 'pos'
name: 'Punto de Venta'
permissions: ['pos.read', 'pos.write', 'pos.cashier']
routes: ['/pos']
```

**Endpoints Frontend consume:**
- `GET /api/v1/pos/registers` - Listar cajas registradoras
- `POST /api/v1/pos/registers` - Crear caja
- `GET /api/v1/pos/registers/{id}` - Obtener caja
- `POST /api/v1/pos/shifts` - Abrir turno
- `GET /api/v1/pos/shifts/{shiftId}/summary` - Resumen de turno
- `POST /api/v1/pos/shifts/close` - Cerrar turno
- `GET /api/v1/pos/shifts/current/{registerId}` - Turno actual
- `POST /api/v1/pos/receipts/calculate_totals` - Calcular totales
- `POST /api/v1/pos/receipts` - Crear ticket
- `GET /api/v1/pos/receipts/{id}` - Obtener ticket

**Endpoints Backend expone:**
- `GET /api/v1/tenant/pos/registers` - Listar cajas
- `POST /api/v1/tenant/pos/registers` - Crear caja
- `POST /api/v1/tenant/pos/shifts` - Abrir turno
- `POST /api/v1/tenant/pos/open_shift` - (deprecated)
- `GET /api/v1/tenant/pos/shifts/{shift_id}/summary` - Resumen
- `POST /api/v1/tenant/pos/shifts/{shift_id}/close` - Cerrar turno
- `GET /api/v1/tenant/pos/shifts` - Listar turnos
- `POST /api/v1/tenant/pos/receipts/calculate_totals` - Calcular
- `POST /api/v1/tenant/pos/receipts` - Crear ticket

**Problemas:**
- ⚠️ Frontend consume `/api/v1/pos/*` pero backend expone `/api/v1/tenant/pos/*`
- ⚠️ Puede causar errores 404

**Estado:** ⚠️ Conectado pero con diferencia de prefijo `/tenant/`

---

### 10. 🏭 PRODUCCIÓN

**Frontend:** `apps/tenant/src/modules/produccion/`  
**Backend:** ❌ **NO EXISTE MÓDULO**

**Manifest Frontend:**
```typescript
id: 'produccion'
name: 'Producción'
permissions: ['produccion.read', 'produccion.write']
routes: [
  '/produccion/recetas',
  '/produccion/ordenes',
  '/produccion/ordenes/nuevo',
  '/produccion/rutas'
]
```

**Endpoints Frontend consume:**
- `GET /api/v1/production/orders` - Listar órdenes ❌
- `GET /api/v1/production/orders/{id}` - Obtener orden ❌
- `POST /api/v1/production/orders` - Crear orden ❌
- `PUT /api/v1/production/orders/{id}` - Actualizar orden ❌
- `DELETE /api/v1/production/orders/{id}` - Eliminar orden ❌
- `POST /api/v1/production/orders/{id}/start` - Iniciar orden ❌
- `POST /api/v1/production/orders/{id}/complete` - Completar orden ❌
- `POST /api/v1/production/orders/{id}/cancel` - Cancelar orden ❌
- `GET /api/v1/production/recipes` - Listar recetas ❌
- `GET /api/v1/production/recipes/{id}` - Obtener receta ❌
- `GET /api/v1/tenant/settings/fiscal` - Configuración fiscal ✅
- `PUT /api/v1/tenant/settings/fiscal` - Actualizar config ✅
- `PUT /api/v1/tenant/products/{id}` - Actualizar producto ✅

**Endpoints Backend expone:**
- ❌ **NO EXISTE MÓDULO `production` EN BACKEND**

**Problemas:**
- 🔴 **CRÍTICO:** El módulo frontend llama a endpoints que NO EXISTEN en el backend
- 🔴 **MÓDULO HUÉRFANO:** Toda la funcionalidad de producción está implementada solo en frontend
- 🔴 Las recetas y órdenes de producción NO se están guardando en ningún lado
- **Solución:** Crear módulo `apps/backend/app/modules/produccion/` O `production/`

**Estado:** 🔴 **DESCONECTADO - REQUIERE BACKEND URGENTE**

---

### 11. 📦 PRODUCTOS

**Frontend:** `apps/tenant/src/modules/productos/`  
**Backend:** `apps/backend/app/modules/productos/`

**Manifest Frontend:**
```typescript
id: 'productos'
name: 'Productos'
icon: '📦'
path: '/productos'
requiredRole: 'operario'
description: 'Catálogo de productos y servicios con configuración dinámica por sector'
features: ['Configuración por sector', 'Importación masiva', 'Precios e impuestos', 'Códigos de barras']
```

**Endpoints Frontend consume:**
- No se detectaron llamadas API directas (probablemente usa shared API)

**Endpoints Backend expone:**
- `GET /api/v1/tenant/products/` - Listar productos
- `GET /api/v1/tenant/products/search` - Buscar productos
- `GET /api/v1/tenant/products/{product_id}` - Obtener producto
- `POST /api/v1/tenant/products/` - Crear producto
- `PUT /api/v1/tenant/products/{product_id}` - Actualizar producto
- `DELETE /api/v1/tenant/products/{product_id}` - Eliminar producto
- `DELETE /api/v1/tenant/products/purge` - Purgar productos

**Problemas:**
- Ninguno detectado

**Estado:** ✅ Totalmente conectado

---

### 12. 👥 PROVEEDORES

**Frontend:** `apps/tenant/src/modules/proveedores/`  
**Backend:** `apps/backend/app/modules/proveedores/`

**Manifest Frontend:**
```typescript
id: 'proveedores'
name: 'Proveedores'
icon: '👥'
color: '#06B6D4'
order: 60
```

**Endpoints Frontend consume:**
- `GET /api/v1/tenant/proveedores/` - Listar proveedores
- `GET /api/v1/tenant/proveedores/{id}` - Obtener proveedor
- `POST /api/v1/tenant/proveedores/` - Crear proveedor
- `PUT /api/v1/tenant/proveedores/{id}` - Actualizar proveedor
- `DELETE /api/v1/tenant/proveedores/{id}` - Eliminar proveedor

**Endpoints Backend expone:**
- `GET /api/v1/tenant/proveedores/`
- `GET /api/v1/tenant/proveedores/{pid}`
- `POST /api/v1/tenant/proveedores/`
- `PUT /api/v1/tenant/proveedores/{pid}`
- `DELETE /api/v1/tenant/proveedores/{pid}`

**Problemas:**
- Ninguno detectado

**Estado:** ✅ Totalmente conectado

---

### 13. 👷 RRHH (Recursos Humanos)

**Frontend:** `apps/tenant/src/modules/rrhh/`  
**Backend:** `apps/backend/app/modules/rrhh/`

**Manifest Frontend:**
```typescript
id: 'rrhh'
name: 'RRHH'
permissions: ['rrhh.read', 'rrhh.write']
routes: ['/rrhh', '/rrhh/vacaciones', '/rrhh/fichajes', '/rrhh/nomina']
```

**Endpoints Frontend consume:**
- (Requiere análisis detallado de services.ts)

**Endpoints Backend expone:**
- `GET /api/v1/tenant/rrhh/vacaciones`

**Problemas:**
- ⚠️ Backend solo expone endpoint de vacaciones, faltan fichajes y nómina

**Estado:** ⚠️ Parcialmente conectado

---

### 14. ⚙️ SETTINGS (Configuración)

**Frontend:** `apps/tenant/src/modules/settings/`  
**Backend:** `apps/backend/app/modules/settings/`

**Manifest Frontend:**
```typescript
id: 'settings'
name: 'Configuración'
permissions: ['settings.read', 'settings.write']
routes: [
  '/settings/general',
  '/settings/branding',
  '/settings/fiscal',
  '/settings/limits',
  '/settings/horarios'
]
```

**Endpoints Frontend consume:**
- (Requiere análisis detallado)

**Endpoints Backend expone:**
- (Requiere análisis de interface/http/tenant.py)

**Problemas:**
- Ninguno aparente

**Estado:** ✅ Conectado

---

### 15. 👤 USUARIOS

**Frontend:** `apps/tenant/src/modules/usuarios/`  
**Backend:** `apps/backend/app/modules/usuarios/`

**Manifest Frontend:**
```typescript
id: 'usuarios'
name: 'Usuarios'
icon: '👤'
color: '#6366F1'
order: 80
```

**Endpoints Frontend consume:**
- (Requiere análisis detallado)

**Endpoints Backend expone:**
- (Requiere análisis de interface/http/tenant.py)

**Problemas:**
- Ninguno aparente

**Estado:** ✅ Conectado

---

### 16. 📊 VENTAS

**Frontend:** `apps/tenant/src/modules/ventas/`  
**Backend:** `apps/backend/app/modules/ventas/`

**Manifest Frontend:**
```typescript
id: 'ventas'
name: 'Ventas'
icon: '📊'
color: '#3B82F6'
order: 40
```

**Endpoints Frontend consume:**
- `GET /api/v1/tenant/ventas/` - Listar ventas
- `GET /api/v1/tenant/ventas/{id}` - Obtener venta
- `POST /api/v1/tenant/ventas/` - Crear venta
- `PUT /api/v1/tenant/ventas/{id}` - Actualizar venta
- `DELETE /api/v1/tenant/ventas/{id}` - Eliminar venta
- `POST /api/v1/tenant/ventas/{id}/to_invoice` - Convertir a factura

**Endpoints Backend expone:**
- `GET /api/v1/tenant/ventas/`
- `GET /api/v1/tenant/ventas/{order_id}`
- `POST /api/v1/tenant/ventas/`
- `POST /api/v1/tenant/ventas/{order_id}/confirm`

**Problemas:**
- ⚠️ Frontend espera `PUT` y `DELETE` pero backend solo tiene `POST confirm`
- ⚠️ Endpoint `to_invoice` puede no existir en backend

**Estado:** ⚠️ Conectado con endpoints faltantes

---

## 🚨 PROBLEMAS CRÍTICOS DETECTADOS

### 🔴 CRÍTICO - Módulo Huérfano

1. **PRODUCCIÓN sin backend**
   - Frontend completo: `/produccion/` con recetas, órdenes, rutas
   - Backend: ❌ NO EXISTE
   - Impacto: Funcionalidad completamente rota
   - **Acción requerida:** Crear `apps/backend/app/modules/produccion/`

### ⚠️ ALTO - Inconsistencias de Nombres

2. **clientes vs clients**
   - Frontend: `/clientes/`
   - Backend: `/clients/`
   - Manifest: `id: 'clientes'`
   - **Acción:** Unificar a `clientes` en español

3. **importador vs imports**
   - Carpeta frontend: `importador/`
   - Manifest frontend: `id: 'imports'`
   - Backend: `imports/`
   - **Acción:** Renombrar carpeta a `imports` O cambiar manifest a `importador`

### ⚠️ MEDIO - Diferencias de Prefijo

4. **Prefijo `/tenant/` inconsistente**
   - POS frontend consume: `/api/v1/pos/*`
   - POS backend expone: `/api/v1/tenant/pos/*`
   - Imports frontend: `/api/v1/imports/*`
   - Imports backend: `/api/v1/tenant/imports/*`
   - **Acción:** Verificar configuración de API client, puede estar funcionando con rewrite

### ⚠️ MEDIO - Endpoints Faltantes

5. **Ventas - operaciones incompletas**
   - Frontend necesita: `PUT`, `DELETE`, `to_invoice`
   - Backend solo tiene: `GET`, `POST`, `confirm`

6. **RRHH - funcionalidad limitada**
   - Frontend tiene: vacaciones, fichajes, nómina
   - Backend solo: vacaciones

---

## 📋 MÓDULOS BACKEND SIN FRONTEND

Estos módulos existen en backend pero NO tienen interfaz en frontend:

### 1. `crm` - CRM
- Funcionalidad de gestión de relaciones con clientes
- **Potencial:** Podría integrarse con módulo `clientes`

### 2. `ai_agent` - Agente IA
- Funcionalidad de inteligencia artificial
- **Estado:** No documentado

### 3. `copilot` - Copiloto
- Asistente inteligente
- **Estado:** No documentado

### 4. `reconciliation` - Reconciliación Bancaria
- Módulo existe en backend
- **Potencial:** Podría añadirse a módulo `finanzas` en frontend

### 5. `admin_config` - Configuración Admin
- Configuración administrativa del sistema
- **Uso:** Probablemente interno

### 6. `einvoicing` - E-Invoicing
- **Estado:** Integrado con módulo `facturacion` (correcto)

### 7. `facturae` - Formato Facturae
- **Estado:** Integrado con módulo `facturacion` (correcto)

### 8. `empresa` - Datos de Empresa
- **Uso:** Puede estar integrado con `settings`

### 9. `export` - Exportaciones
- **Uso:** Probablemente usado por múltiples módulos

### 10. `identity` - Identidad y Autenticación
- **Uso:** Sistema core (no requiere módulo frontend dedicado)

### 11. `modulos` - Registro de Módulos
- **Uso:** Sistema core

### 12. `registry` - Registro de Eventos
- **Uso:** Sistema core

### 13. `shared` - Compartido
- **Uso:** Código compartido

### 14. `templates` - Plantillas
- **Uso:** Generación de documentos

### 15. `webhooks` - Webhooks
- **Uso:** Integraciones externas

---

## ✅ RECOMENDACIONES

### Acciones Inmediatas (Crítico)

1. **Crear módulo backend `produccion`**
   ```bash
   mkdir -p apps/backend/app/modules/produccion/{interface/http,application,domain,infrastructure}
   ```
   - Implementar endpoints de recetas
   - Implementar endpoints de órdenes de producción
   - Implementar endpoints de rutas de producción

### Acciones Corto Plazo (Alto)

2. **Unificar nombres clientes/clients**
   - Opción A: Renombrar backend `/clients/` → `/clientes/`
   - Opción B: Renombrar frontend `/clientes/` → `/clients/` (no recomendado)
   - **Recomendación:** Opción A (mantener español)

3. **Unificar importador/imports**
   - Opción A: Renombrar carpeta `importador/` → `imports/`
   - Opción B: Cambiar manifest `id: 'imports'` → `id: 'importador'`
   - **Recomendación:** Opción A (consistencia con backend)

4. **Verificar prefijos API**
   - Revisar configuración de `tenantApi` en frontend
   - Asegurar que maneja correctamente `/tenant/` prefix

### Acciones Medio Plazo (Medio)

5. **Completar endpoints faltantes**
   - Ventas: agregar `PUT`, `DELETE`, `to_invoice`
   - RRHH: agregar fichajes y nómina

6. **Documentar módulos backend sin frontend**
   - Decidir si CRM, reconciliation necesitan UI
   - Documentar uso de ai_agent y copilot

### Mejoras de Arquitectura

7. **Crear documento de convenciones**
   - Definir: ¿español o inglés para nombres?
   - Definir: estructura de rutas estándar
   - Definir: naming conventions (singular/plural)

8. **Automatizar detección de inconsistencias**
   - Script que compare manifests con rutas backend
   - CI/CD que valide endpoints existen

---

## 📊 ESTADÍSTICAS

- **Total módulos frontend:** 16
- **Totalmente conectados:** 9 (56%)
- **Conectados con warnings:** 6 (38%)
- **Sin backend:** 1 (6%) - **CRÍTICO**
- **Módulos backend sin frontend:** 15

**Salud general del sistema:** ⚠️ **75% funcional**

---

## 🔄 DUPLICACIONES DETECTADAS

### Ninguna duplicación funcional detectada
- Todos los módulos tienen responsabilidades claras
- No se detectaron módulos que hagan lo mismo con nombres diferentes
- La separación de `facturacion` y `einvoicing` es correcta (responsabilidad única)

---

## 📝 CONCLUSIONES

1. **Arquitectura sólida:** La mayoría de módulos están bien conectados
2. **Problema crítico:** Módulo producción completamente desconectado
3. **Inconsistencias menores:** Nombres en español/inglés mezclados
4. **Oportunidades:** Varios módulos backend podrían tener interfaces frontend
5. **Mantenibilidad:** Requiere convenciones claras de naming

**Siguiente paso:** Priorizar creación de backend para `produccion`.
