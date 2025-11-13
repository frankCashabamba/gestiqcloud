# 📘 Plan de Desarrollo de Módulos por Sector - GestiQCloud

**Versión:** 1.0
**Fecha:** Octubre 2025
**Cliente:** GestiQCloud Multi-Tenant
**Sectores Activos:** Panadería, Retail/Bazar, Taller Mecánico
***TOdos los ficheros que se cree deben ser UTF-8

---

## 🎯 Visión General del Proyecto

GestiQCloud es un sistema ERP/CRM multi-tenant diseñado para **autónomos y pymes (1-10 empleados)** en España y Ecuador. El sistema se adapta dinámicamente a las necesidades específicas de cada sector mediante:

1. **Configuración dinámica de campos por módulo**
2. **Defaults por sector** (heredables)
3. **Overrides por tenant** (personalizables)
4. **4 modos de formulario:** mixed, tenant, sector, basic

### ✅ Estado Actual

| Módulo | Panadería | Retail/Bazar | Taller Mecánico | Restaurante | Estado |
|--------|-----------|--------------|-----------------|-------------|--------|
| **Clientes** | ✅ | ✅ | ✅ | ✅ | 100% - Universal |
| **Productos** | ✅ | ✅ | ✅ | ✅ | 100% - Configurable |
| **Inventario** | ✅ | ✅ | ✅ | ✅ | 100% - Configurable |
| **POS/TPV** | ✅ | ✅ | ❌ | ✅ | 100% - Configurable |
| **Importador** | ✅ | ✅ | ✅ | ✅ | 110% - Universal |
| Ventas | ⏳ | ⏳ | ⏳ | ⏳ | 100% Backend |
| Producción | ✅ | ❌ | ❌ | ✅ | 70% - Portable |
| Proveedores | ⏳ | ⏳ | ⏳ | ⏳ | 95% |
| Compras | ⏳ | ⏳ | ⏳ | ⏳ | 90% |

---

## 🔄 Análisis de Portabilidad de Módulos

### 📊 **Módulos 100% Genéricos (Sin Modificaciones)**

Estos módulos funcionan **idénticamente** en todos los sectores sin necesidad de cambios en el código:

#### 1. **📦 CLIENTES** - Universal
```
✅ Panadería → RETAIL/BAZAR: 100% compatible
✅ Panadería → RESTAURANTE: 100% compatible
✅ Panadería → TALLER: 100% compatible

Razón: Todos los sectores necesitan gestión de clientes.
Solo varían campos opcionales (NIF, matrícula, etc.) mediante configuración.
```

#### 2. **📦 IMPORTADOR** - Universal
```
✅ Panadería → RETAIL/BAZAR: 100% compatible
✅ Panadería → RESTAURANTE: 100% compatible
✅ Panadería → TALLER: 100% compatible

Razón: Carga masiva de datos es universal.
Soporta cualquier entityType (productos, clientes, inventario).
Auto-mapeo de columnas independiente del sector.
```

### ⚠️ **Módulos Configurables (Mínima Adaptación)**

Requieren **solo ajustes de configuración**, no código nuevo:

#### 3. **📦 PRODUCTOS** - Configurable por Sector

| Campo | Panadería | Retail/Bazar | Restaurante | Taller |
|-------|-----------|--------------|-------------|--------|
| **Genéricos** | codigo, nombre, precio, iva | ✅ | ✅ | ✅ |
| peso_unitario | ✅ | ❌ | ⚠️ Opcional | ❌ |
| caducidad_dias | ✅ | ❌ | ✅ | ❌ |
| ingredientes | ✅ | ❌ | ✅ | ❌ |
| receta_id | ✅ | ❌ | ✅ | ❌ |
| marca | ❌ | ✅ | ❌ | ⚠️ Opcional |
| modelo | ❌ | ✅ | ❌ | ✅ |
| talla/color | ❌ | ✅ | ❌ | ❌ |
| margen | ❌ | ✅ | ❌ | ⚠️ Opcional |
| tipo_servicio | ❌ | ❌ | ❌ | ✅ |
| tiempo_instalacion | ❌ | ❌ | ❌ | ✅ |

**Adaptación necesaria:**
```python
# apps/backend/app/services/field_config.py

# ✅ Ya existe para Panadería
SECTOR_DEFAULTS['panaderia'] = { ... }

# 🆕 Solo agregar configuración Retail
SECTOR_DEFAULTS['retail'] = {
    'productos': [
        {'field': 'marca', 'visible': True, 'ord': 27},
        {'field': 'modelo', 'visible': True, 'ord': 28},
        {'field': 'talla', 'visible': True, 'ord': 29},
        {'field': 'color', 'visible': True, 'ord': 30},
        {'field': 'margen', 'visible': True, 'ord': 45},
    ]
}

# 🆕 Solo agregar configuración Restaurante
SECTOR_DEFAULTS['restaurante'] = {
    'productos': [
        {'field': 'ingredientes', 'visible': True, 'ord': 40},
        {'field': 'receta_id', 'visible': True, 'ord': 45},
        {'field': 'tiempo_preparacion', 'visible': True, 'ord': 50},
    ]
}
```

**Líneas de código nuevas:** ~30 (solo config)
**Código reutilizado:** 1,424 líneas (100%)

#### 4. **📦 INVENTARIO** - Configurable por Sector

| Característica | Panadería | Retail/Bazar | Restaurante | Taller |
|----------------|-----------|--------------|-------------|--------|
| Stock básico | ✅ | ✅ | ✅ | ✅ |
| Lotes | ✅ | ⚠️ Opcional | ⚠️ Opcional | ⚠️ Opcional |
| Caducidades | ✅ | ❌ | ✅ | ❌ |
| Ubicaciones | ⚠️ Opcional | ✅ | ❌ | ✅ |
| Movimientos auto (POS) | ✅ | ✅ | ✅ | ❌ |

**Adaptación necesaria:**
```json
// SectorPlantilla config_json

// Panadería
{
  "inventory": {
    "enable_expiry_tracking": true,
    "enable_lot_tracking": true,
    "enable_serial_tracking": false
  }
}

// Retail/Bazar
{
  "inventory": {
    "enable_expiry_tracking": false,
    "enable_lot_tracking": true,
    "enable_serial_tracking": false
  }
}

// Restaurante
{
  "inventory": {
    "enable_expiry_tracking": true,
    "enable_lot_tracking": false,
    "enable_serial_tracking": false
  }
}
```

**Líneas de código nuevas:** 0 (solo config JSON)
**Código reutilizado:** 1,260 líneas (100%)

#### 5. **📦 POS/TPV** - Configurable por Sector

| Característica | Panadería | Retail/Bazar | Restaurante | Taller |
|----------------|-----------|--------------|-------------|--------|
| Venta rápida | ✅ | ✅ | ✅ | ❌ N/A |
| Scanner barcode | ✅ | ✅ | ⚠️ Opcional | ❌ |
| Productos a peso | ✅ | ❌ | ⚠️ Opcional | ❌ |
| Mesas/Comandas | ❌ | ❌ | ✅ | ❌ |
| Devoluciones | ✅ | ✅ | ⚠️ Limitado | ❌ |
| Ticket → Factura | ✅ | ✅ | ✅ | ❌ |

**Adaptación necesaria:**
```json
// Panadería
{
  "pos": {
    "enable_weights": true,
    "enable_batch_tracking": true,
    "receipt_width_mm": 58
  }
}

// Retail/Bazar
{
  "pos": {
    "enable_weights": false,
    "enable_batch_tracking": false,
    "receipt_width_mm": 80
  }
}

// Restaurante
{
  "pos": {
    "enable_weights": true,
    "enable_batch_tracking": false,
    "enable_tables": true,
    "receipt_width_mm": 58
  }
}
```

**Líneas de código nuevas:** ~150 (solo para mesas en Restaurante)
**Código reutilizado:** 1,160 líneas (88%)

### 🏭 **Módulo Sector-Específico (Portable con Renombrado)**

#### 6. **📦 PRODUCCIÓN** - Panadería ↔️ Restaurante

```
✅ Panadería → RESTAURANTE: 95% compatible
❌ Panadería → RETAIL/BAZAR: No aplicable
❌ Panadería → TALLER: No aplicable
```

| Concepto | Panadería | Restaurante | Código Compartido |
|----------|-----------|-------------|-------------------|
| Recetas | Pan, bollería | Platos, menús | ✅ 100% |
| Ingredientes | Harina, levadura | Carne, verduras | ✅ 100% |
| Órdenes producción | Horneadas | Mise en place | ✅ 95% |
| BOM (Bill of Materials) | ✅ | ✅ | ✅ 100% |
| Consumo stock | ✅ | ✅ | ✅ 100% |
| Mermas | Pan no vendido | Desperdicio | ✅ 100% |
| Lotes | Número horneada | Lote preparación | ✅ 100% |

**Archivos existentes reutilizables:**
```
✅ RecetaForm.tsx       → 100% reutilizable
✅ RecetasView.tsx      → 100% reutilizable
✅ CalculadoraProduccion.tsx → 100% reutilizable
✅ services.ts          → 100% reutilizable
```

**Adaptación necesaria:**
```typescript
// Solo renombrar labels en configuración

// Panadería
{
  labels: {
    batch: "Horneada",
    expiry: "Días de caducidad",
    unit: "Unidad/Peso"
  }
}

// Restaurante
{
  labels: {
    batch: "Preparación",
    expiry: "Días de consumo",
    unit: "Ración/Porción"
  },
  categories: ["Entrantes", "Principales", "Postres", "Bebidas"]
}
```

**Líneas de código nuevas:** ~50 (labels + categorías)
**Código reutilizado:** ~800 líneas (94%)

---

## 🎯 Resumen: ¿Qué Se Necesita para RETAIL/BAZAR?

### ❌ **Módulos Nuevos a Desarrollar:** 0

### ✅ **Solo Configuración (3 archivos):**

1. **field_config.py** → Agregar `SECTOR_DEFAULTS['retail']`
   - Productos: marca, modelo, talla, color, margen
   - ~30 líneas

2. **SectorPlantilla** → Crear plantilla "Retail/Bazar"
   ```json
   {
     "modules": {
       "pos": {"enabled": true},
       "inventory": {"enabled": true},
       "productos": {"enabled": true},
       "clientes": {"enabled": true}
     },
     "inventory": {
       "enable_expiry_tracking": false,
       "enable_lot_tracking": true
     },
     "pos": {
       "enable_weights": false,
       "receipt_width_mm": 80
     }
   }
   ```

3. **Categorías por defecto:**
   ```python
   defaults: {
     "categories": ["Ropa", "Electrónica", "Hogar", "Juguetes", "Deportes"]
   }
   ```

### 📊 **Esfuerzo Total:**
- **Tiempo:** 2-3 horas
- **Archivos nuevos:** 0
- **Archivos modificados:** 2
- **Líneas de código:** ~50
- **Código reutilizado:** ~8,340 líneas (99.4%)

---

## 🏭 Resumen: ¿Qué Se Necesita para RESTAURANTE con Producción?

### ✅ **Módulos Reutilizables:** 6
- Clientes (100%)
- Productos (95% - ajustar campos)
- Inventario (100%)
- POS (88% - agregar mesas/comandas)
- Importador (100%)
- **Producción** (94% - renombrar labels)

### 🆕 **Funcionalidad Nueva:**
- Gestión de mesas (POS)
- Comandas (kitchen display)
- Split de cuenta

### 📊 **Esfuerzo Total:**
- **Tiempo:** 5-7 días
- **Archivos nuevos:** ~6 (mesas, comandas)
- **Líneas de código nuevas:** ~400
- **Código reutilizado:** ~8,000 líneas (95%)

---

## 📐 Arquitectura de Referencia: Módulo CLIENTES

El módulo de **Clientes** es nuestro **estándar de oro** (100% completitud). Todos los módulos deben seguir esta estructura.

### 📁 Estructura de Archivos

```
apps/tenant/src/modules/clientes/
├── Form.tsx                    # Formulario dinámico con config de campos
├── List.tsx                    # Lista con paginación/sort/búsqueda
├── Routes.tsx                  # Rutas del módulo
├── services.ts                 # API client TypeScript
├── manifest.ts                 # Configuración del módulo
└── README.md                   # Documentación completa (81 líneas)
```

### 🔑 Características Obligatorias

#### 1. **Form.tsx** - Formulario Dinámico
```typescript
✅ useEffect para cargar configuración de campos desde API
✅ GET /api/v1/tenant/settings/fields?module={nombre}&empresa={slug}
✅ Fallback a campos base si API falla
✅ Validación de campos required
✅ Validación específica por tipo (email, teléfono, etc.)
✅ Toast notifications (success/error)
✅ Loading states
✅ Modo crear/editar (reutiliza mismo componente)
```

#### 2. **List.tsx** - Lista con Funcionalidad Avanzada
```typescript
✅ Búsqueda en tiempo real (nombre, email, etc.)
✅ Ordenamiento por columnas (asc/desc)
✅ Paginación configurable (10/25/50 registros)
✅ Botones de acción: Nuevo, Editar, Eliminar
✅ Confirmación de eliminación
✅ Loading/error states
✅ Tabla responsive
✅ useMemo para optimización
```

#### 3. **services.ts** - API Client
```typescript
✅ Tipos TypeScript exportados
✅ CRUD completo:
   - listClientes(): Promise<Cliente[]>
   - getCliente(id: string): Promise<Cliente>
   - createCliente(data: Partial<Cliente>): Promise<Cliente>
   - updateCliente(id: string, data: Partial<Cliente>): Promise<Cliente>
   - removeCliente(id: string): Promise<void>
✅ Manejo de errores con try/catch
```

#### 4. **manifest.ts** - Configuración del Módulo
```typescript
export const clientesManifest = {
  id: 'clientes',
  name: 'Clientes',
  icon: '👥',
  path: '/clientes',
  enabled: true,
  requiredRole: 'operario', // o 'manager', 'owner'
}
```

#### 5. **Routes.tsx** - Rutas del Módulo
```typescript
✅ Route principal: /:empresa/clientes
✅ Route lista: index
✅ Route nuevo: nuevo
✅ Route editar: :id/editar
✅ (Opcional) Route detalle: :id
```

#### 6. **README.md** - Documentación
```markdown
✅ Resumen del módulo
✅ Arquitectura de archivos
✅ Integración con configuración de campos
✅ Modos de formulario (mixed/tenant/sector/basic)
✅ Cómo añadir campos personalizados
✅ Verificación rápida (curl ejemplo)
✅ Endpoints relacionados
✅ Problemas comunes y soluciones
✅ Buenas prácticas
```

---

## 🏗️ Plan de Desarrollo Módulo por Módulo

### Prioridad 1: PRODUCTOS (Crítico para los 3 sectores)

#### 📋 Especificación General

**Objetivo:** Sistema de catálogo de productos con gestión de precios, códigos de barras y categorización por sector.

#### 🎯 Campos por Sector

##### **PANADERÍA**
| Campo | Tipo | Required | Ord | Label | Help | Sector-Specific |
|-------|------|----------|-----|-------|------|-----------------|
| codigo | text | ✅ | 10 | Código | PLU o código interno | - |
| codigo_barras | text | ❌ | 15 | Código de barras | EAN-13 | - |
| nombre | text | ✅ | 20 | Nombre | Ej: Pan integral 400g | - |
| categoria | select | ✅ | 25 | Categoría | Pan, Bollería, Pastelería | ✅ Panadería |
| precio | number | ✅ | 30 | Precio de venta | € por unidad | - |
| peso_unitario | number | ❌ | 35 | Peso unitario (kg) | Para productos a peso | ✅ Panadería |
| receta_id | select | ❌ | 40 | Receta asociada | Vínculo a producción | ✅ Panadería |
| caducidad_dias | number | ❌ | 45 | Días de caducidad | Días desde producción | ✅ Panadería |
| ingredientes | textarea | ❌ | 50 | Ingredientes | Lista de alérgenos | ✅ Panadería |
| impuesto | select | ✅ | 60 | IVA | 21%, 10%, 4% | - |
| activo | boolean | ✅ | 70 | Activo | Visible en POS | - |

##### **RETAIL/BAZAR**
| Campo | Tipo | Required | Ord | Label | Help | Sector-Specific |
|-------|------|----------|-----|-------|------|-----------------|
| codigo | text | ✅ | 10 | SKU | Código único | - |
| codigo_barras | text | ✅ | 15 | EAN | Código de barras | - |
| nombre | text | ✅ | 20 | Nombre | Nombre del producto | - |
| categoria | select | ✅ | 25 | Categoría | Ropa, Electrónica, Hogar | ✅ Retail |
| marca | text | ❌ | 27 | Marca | Fabricante | ✅ Retail |
| modelo | text | ❌ | 28 | Modelo | Referencia del modelo | ✅ Retail |
| talla | text | ❌ | 29 | Talla | S/M/L/XL o numérico | ✅ Retail |
| color | text | ❌ | 30 | Color | Color principal | ✅ Retail |
| precio_compra | number | ❌ | 35 | Precio de compra | Para calcular margen | ✅ Retail |
| precio_venta | number | ✅ | 40 | Precio de venta | PVP | - |
| margen | number | ❌ | 45 | Margen (%) | Auto-calculado | ✅ Retail |
| stock_minimo | number | ❌ | 50 | Stock mínimo | Alerta de reposición | - |
| stock_maximo | number | ❌ | 55 | Stock máximo | Control de sobre-stock | - |
| impuesto | select | ✅ | 60 | IVA | 21%, 10% | - |
| activo | boolean | ✅ | 70 | Activo | Visible en catálogo | - |

##### **TALLER MECÁNICO**
| Campo | Tipo | Required | Ord | Label | Help | Sector-Specific |
|-------|------|----------|-----|-------|------|-----------------|
| codigo | text | ✅ | 10 | Código OEM | Código del fabricante | ✅ Taller |
| codigo_interno | text | ❌ | 12 | Código interno | Referencia propia | - |
| nombre | text | ✅ | 20 | Descripción | Pieza o servicio | - |
| tipo | select | ✅ | 25 | Tipo | Repuesto, MO, Servicio | ✅ Taller |
| categoria | select | ✅ | 30 | Categoría | Motor, Frenos, Suspensión | ✅ Taller |
| marca_vehiculo | text | ❌ | 35 | Marca vehículo | Compatibilidad | ✅ Taller |
| modelo_vehiculo | text | ❌ | 40 | Modelo vehículo | Año inicio-fin | ✅ Taller |
| proveedor_ref | text | ❌ | 45 | Ref. proveedor | Código del proveedor | - |
| precio_compra | number | ❌ | 50 | Precio compra | Sin IVA | - |
| precio_venta | number | ✅ | 55 | Precio venta | PVP sin IVA | - |
| tiempo_instalacion | number | ❌ | 60 | Tiempo instalación (h) | Para presupuestos | ✅ Taller |
| stock_minimo | number | ❌ | 65 | Stock mínimo | Piezas críticas | - |
| impuesto | select | ✅ | 70 | IVA | 21% | - |
| activo | boolean | ✅ | 80 | Activo | Disponible | - |

#### 🛠️ Implementación Paso a Paso

**PASO 1: Backend - Configuración de Campos**

1. Crear defaults por sector en:
```sql
-- apps/backend/app/services/field_config.py
SECTOR_DEFAULTS = {
    'panaderia': {
        'productos': [
            {'field': 'codigo', 'visible': True, 'required': True, 'ord': 10, 'label': 'Código'},
            {'field': 'nombre', 'visible': True, 'required': True, 'ord': 20, 'label': 'Nombre'},
            {'field': 'categoria', 'visible': True, 'required': True, 'ord': 25, 'label': 'Categoría'},
            {'field': 'peso_unitario', 'visible': True, 'required': False, 'ord': 35, 'label': 'Peso unitario (kg)'},
            {'field': 'caducidad_dias', 'visible': True, 'required': False, 'ord': 45, 'label': 'Días de caducidad'},
            # ... resto de campos
        ]
    },
    'retail': {
        'productos': [
            {'field': 'codigo', 'visible': True, 'required': True, 'ord': 10, 'label': 'SKU'},
            {'field': 'codigo_barras', 'visible': True, 'required': True, 'ord': 15, 'label': 'EAN'},
            {'field': 'marca', 'visible': True, 'required': False, 'ord': 27, 'label': 'Marca'},
            # ... resto de campos
        ]
    },
    'taller': {
        'productos': [
            {'field': 'codigo', 'visible': True, 'required': True, 'ord': 10, 'label': 'Código OEM'},
            {'field': 'tipo', 'visible': True, 'required': True, 'ord': 25, 'label': 'Tipo'},
            {'field': 'tiempo_instalacion', 'visible': True, 'required': False, 'ord': 60, 'label': 'Tiempo instalación (h)'},
            # ... resto de campos
        ]
    }
}
```

2. Endpoint ya existe:
```
GET /api/v1/tenant/settings/fields?module=productos&empresa={slug}
```

**PASO 2: Frontend - Crear Estructura**

```bash
cd apps/tenant/src/modules
mkdir productos
cd productos
```

**PASO 3: services.ts**

```typescript
// apps/tenant/src/modules/productos/services.ts
import { apiFetch } from '../../lib/http'

export type Producto = {
  id: string
  codigo: string
  codigo_barras?: string | null
  nombre: string
  categoria?: string | null
  precio: number
  impuesto: number
  activo: boolean
  // Campos específicos panadería
  peso_unitario?: number | null
  caducidad_dias?: number | null
  receta_id?: string | null
  ingredientes?: string | null
  // Campos específicos retail
  marca?: string | null
  modelo?: string | null
  talla?: string | null
  color?: string | null
  precio_compra?: number | null
  margen?: number | null
  // Campos específicos taller
  codigo_interno?: string | null
  tipo?: string | null
  marca_vehiculo?: string | null
  modelo_vehiculo?: string | null
  tiempo_instalacion?: number | null
  stock_minimo?: number | null
  stock_maximo?: number | null
  created_at?: string
  updated_at?: string
}

export async function listProductos(): Promise<Producto[]> {
  return apiFetch<Producto[]>('/api/v1/tenant/productos')
}

export async function getProducto(id: string): Promise<Producto> {
  return apiFetch<Producto>(`/api/v1/tenant/productos/${id}`)
}

export async function createProducto(data: Partial<Producto>): Promise<Producto> {
  return apiFetch<Producto>('/api/v1/tenant/productos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function updateProducto(id: string, data: Partial<Producto>): Promise<Producto> {
  return apiFetch<Producto>(`/api/v1/tenant/productos/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function removeProducto(id: string): Promise<void> {
  await apiFetch(`/api/v1/tenant/productos/${id}`, { method: 'DELETE' })
}
```

**PASO 4: Form.tsx** (Copiar de clientes y adaptar)

```typescript
// apps/tenant/src/modules/productos/Form.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createProducto, getProducto, updateProducto, type Producto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type FieldCfg = {
  field: string
  visible?: boolean
  required?: boolean
  ord?: number | null
  label?: string | null
  help?: string | null
  type?: string | null  // text, number, select, textarea, boolean
  options?: string[] | null  // Para campos select
}

export default function ProductoForm() {
  const { id, empresa } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<Partial<Producto>>({
    codigo: '',
    nombre: '',
    precio: 0,
    impuesto: 21,
    activo: true
  })
  const { success, error } = useToast()
  const [fields, setFields] = useState<FieldCfg[] | null>(null)
  const [loadingCfg, setLoadingCfg] = useState(false)

  useEffect(() => {
    if (!id) return
    getProducto(id).then((x) => setForm({ ...x }))
  }, [id])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoadingCfg(true)
        const q = new URLSearchParams({ module: 'productos', ...(empresa ? { empresa } : {}) }).toString()
        const data = await apiFetch<{ items?: FieldCfg[] }>(`/api/v1/tenant/settings/fields?${q}`)
        if (!cancelled) setFields((data?.items || []).filter(it => it.visible !== false))
      } catch {
        if (!cancelled) setFields(null)
      } finally {
        if (!cancelled) setLoadingCfg(false)
      }
    })()
    return () => { cancelled = true }
  }, [empresa])

  const fieldList = useMemo(() => {
    const base: FieldCfg[] = [
      { field: 'codigo', visible: true, required: true, ord: 10, label: 'Código', type: 'text' },
      { field: 'nombre', visible: true, required: true, ord: 20, label: 'Nombre', type: 'text' },
      { field: 'precio', visible: true, required: true, ord: 30, label: 'Precio', type: 'number' },
      { field: 'impuesto', visible: true, required: true, ord: 40, label: 'IVA (%)', type: 'number' },
      { field: 'activo', visible: true, required: false, ord: 50, label: 'Activo', type: 'boolean' },
    ]
    const list = (fields && fields.length > 0 ? fields : base).slice().sort((a, b) => (a.ord || 999) - (b.ord || 999))
    return list
  }, [fields])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      // Validación de campos required
      for (const f of fieldList) {
        if (f.required && f.visible !== false) {
          const val = (form as any)[f.field]
          if (val === undefined || val === null || String(val).trim() === '') {
            throw new Error(`El campo "${f.label || f.field}" es obligatorio`)
          }
        }
      }

      // Validación de precio
      if (form.precio !== undefined && form.precio < 0) {
        throw new Error('El precio no puede ser negativo')
      }

      if (id) await updateProducto(id, form)
      else await createProducto(form)

      success('Producto guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const renderField = (f: FieldCfg) => {
    const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
    const value = (form as any)[f.field] ?? ''
    const fieldType = f.type || 'text'

    switch (fieldType) {
      case 'number':
        return (
          <input
            type="number"
            step="0.01"
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: parseFloat(e.target.value) || 0 })}
            className="border px-2 py-1 w-full rounded"
            required={!!f.required}
            placeholder={f.help || ''}
          />
        )

      case 'boolean':
        return (
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => setForm({ ...form, [f.field]: e.target.checked })}
            className="border px-2 py-1 rounded"
          />
        )

      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={3}
            required={!!f.required}
            placeholder={f.help || ''}
          />
        )

      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required={!!f.required}
          >
            <option value="">Seleccionar...</option>
            {(f.options || []).map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        )

      default: // text
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required={!!f.required}
            placeholder={f.help || ''}
          />
        )
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar producto' : 'Nuevo producto'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        {loadingCfg && <div className="text-sm text-gray-500">Cargando campos…</div>}
        {fieldList.map((f) => (
          <div key={f.field}>
            <label className="block mb-1 font-medium">
              {f.label || f.field.replace(/_/g, ' ')}
              {f.required && <span className="text-red-600">*</span>}
            </label>
            {renderField(f)}
            {f.help && <p className="text-xs text-gray-500 mt-1">{f.help}</p>}
          </div>
        ))}
        <div className="pt-2 flex gap-2">
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Guardar
          </button>
          <button type="button" className="px-4 py-2 border rounded hover:bg-gray-100" onClick={() => nav('..')}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
```

**PASO 5: List.tsx**

```typescript
// apps/tenant/src/modules/productos/List.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listProductos, removeProducto, type Producto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function ProductosList() {
  const [items, setItems] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [q, setQ] = useState('')

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listProductos())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const [sortKey, setSortKey] = useState<'nombre' | 'codigo' | 'precio'>('nombre')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(10)

  const filtered = useMemo(
    () => items.filter(p =>
      (p.nombre || '').toLowerCase().includes(q.toLowerCase()) ||
      (p.codigo || '').toLowerCase().includes(q.toLowerCase()) ||
      (p.codigo_barras || '').toLowerCase().includes(q.toLowerCase())
    ),
    [items, q]
  )

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = ((a as any)[sortKey] || '').toString().toLowerCase()
      const bv = ((b as any)[sortKey] || '').toString().toLowerCase()
      return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, perPage, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">Productos</h2>
        <button className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700" onClick={() => nav('nuevo')}>
          ➕ Nuevo
        </button>
      </div>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Buscar por nombre, código o EAN..."
        className="mb-3 w-full px-3 py-2 border rounded text-sm"
        aria-label="Buscar productos"
      />

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>Por página</label>
        <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b bg-gray-50">
              <th className="p-2">
                <button className="underline font-semibold" onClick={() => { setSortKey('codigo'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>
                  Código {sortKey === 'codigo' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </button>
              </th>
              <th className="p-2">
                <button className="underline font-semibold" onClick={() => { setSortKey('nombre'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>
                  Nombre {sortKey === 'nombre' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </button>
              </th>
              <th className="p-2">EAN</th>
              <th className="p-2">
                <button className="underline font-semibold" onClick={() => { setSortKey('precio'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>
                  Precio {sortKey === 'precio' ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </button>
              </th>
              <th className="p-2">IVA</th>
              <th className="p-2">Estado</th>
              <th className="p-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {view.map((p) => (
              <tr key={p.id} className="border-b hover:bg-gray-50">
                <td className="p-2 font-mono text-xs">{p.codigo}</td>
                <td className="p-2 font-medium">{p.nombre}</td>
                <td className="p-2 text-xs text-gray-600">{p.codigo_barras || '-'}</td>
                <td className="p-2">{p.precio.toFixed(2)} €</td>
                <td className="p-2">{p.impuesto}%</td>
                <td className="p-2">
                  <span className={`px-2 py-1 rounded text-xs ${p.activo ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                    {p.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="p-2">
                  <Link to={`${p.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                  <button
                    className="text-red-700 hover:underline"
                    onClick={async () => {
                      if (!confirm('¿Eliminar producto?')) return
                      try {
                        await removeProducto(p.id)
                        setItems((prev) => prev.filter(x => x.id !== p.id))
                        success('Producto eliminado')
                      } catch (e: any) {
                        toastError(getErrorMessage(e))
                      }
                    }}
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td className="py-8 px-3 text-center text-gray-500" colSpan={7}>
                  No hay productos registrados. <button className="text-blue-600 hover:underline" onClick={() => nav('nuevo')}>Crear el primero</button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
```

**PASO 6: Routes.tsx**

```typescript
// apps/tenant/src/modules/productos/Routes.tsx
import React from 'react'
import { Route, Routes as RouterRoutes } from 'react-router-dom'
import ProductosList from './List'
import ProductoForm from './Form'

export default function ProductosRoutes() {
  return (
    <RouterRoutes>
      <Route index element={<ProductosList />} />
      <Route path="nuevo" element={<ProductoForm />} />
      <Route path=":id/editar" element={<ProductoForm />} />
    </RouterRoutes>
  )
}
```

**PASO 7: manifest.ts**

```typescript
// apps/tenant/src/modules/productos/manifest.ts
export const productosManifest = {
  id: 'productos',
  name: 'Productos',
  icon: '📦',
  path: '/productos',
  enabled: true,
  requiredRole: 'operario',
  description: 'Catálogo de productos y servicios',
}
```

**PASO 8: README.md**

```markdown
# Módulo PRODUCTOS - Documentación

## 📋 Descripción

Módulo de gestión de productos con configuración dinámica de campos por sector (Panadería, Retail/Bazar, Taller Mecánico).

## 🏗️ Arquitectura

\`\`\`
apps/tenant/src/modules/productos/
├── List.tsx                    ✅ Lista con filtros, paginación, ordenamiento
├── Form.tsx                    ✅ Formulario dinámico con config por sector
├── Routes.tsx                  ✅ Rutas configuradas
├── services.ts                 ✅ API client con tipos TypeScript
├── manifest.ts                 ✅ Configuración del módulo
└── README.md                   📄 Este archivo
\`\`\`

## ✨ Características por Sector

### Panadería
- ✅ Peso unitario para productos a granel
- ✅ Días de caducidad
- ✅ Ingredientes y alérgenos
- ✅ Vínculo a recetas de producción

### Retail/Bazar
- ✅ Marca, modelo, talla, color
- ✅ Cálculo de margen
- ✅ Stock mínimo/máximo

### Taller Mecánico
- ✅ Código OEM y compatibilidad vehículos
- ✅ Tipo: Repuesto/MO/Servicio
- ✅ Tiempo de instalación para presupuestos

## 🔧 Configuración de Campos

GET /api/v1/tenant/settings/fields?module=productos&empresa={slug}

## 🧪 Testing

\`\`\`bash
# Listar productos
curl http://localhost:8000/api/v1/tenant/productos

# Crear producto
curl -X POST http://localhost:8000/api/v1/tenant/productos \
  -H "Content-Type: application/json" \
  -d '{"codigo":"PAN001","nombre":"Pan integral 400g","precio":2.50,"impuesto":10}'
\`\`\`
```

**PASO 9: Registrar en index.ts**

```typescript
// apps/tenant/src/modules/index.ts
import { productosManifest } from './productos/manifest'

export const modules = [
  clientesManifest,
  productosManifest,  // ← Añadir
  // ...
]
```

**PASO 10: Backend - Crear Endpoints**

```python
# apps/backend/app/routers/productos.py
from fastapi import APIRouter, Depends
from app.models import Producto
from app.middleware.rls import ensure_rls

router = APIRouter(prefix="/productos", tags=["productos"])

@router.get("/")
async def list_productos(db = Depends(get_db)):
    ensure_rls(db)
    return db.query(Producto).filter(Producto.activo == True).all()

@router.post("/")
async def create_producto(data: ProductoCreate, db = Depends(get_db)):
    ensure_rls(db)
    producto = Producto(**data.dict())
    db.add(producto)
    db.commit()
    return producto

# ... resto de endpoints
```

---

### Prioridad 2: INVENTARIO (Crítico para Retail/Bazar y Taller)

#### 📋 Especificación

**Objetivo:** Sistema de control de stock con movimientos, ajustes, valoración y alertas.

#### 🎯 Módulos a Implementar

1. **Movimientos de Stock** (stock_moves)
   - Entradas (compras, ajustes positivos, devoluciones clientes)
   - Salidas (ventas, ajustes negativos, mermas)
   - Transferencias entre almacenes

2. **Stock Items** (stock_items)
   - Cantidad actual por producto/almacén
   - Lotes y caducidades (panadería)
   - Ubicaciones (retail/taller)

3. **Ajustes de Inventario**
   - Recuentos físicos
   - Diferencias y auditoría
   - Motivos de ajuste

4. **Valoración**
   - FIFO (First In First Out)
   - Promedio ponderado
   - Último precio de compra

#### 📁 Estructura de Archivos

```
apps/tenant/src/modules/inventario/
├── MovimientosList.tsx         # Lista de movimientos
├── MovimientoForm.tsx          # Nuevo movimiento (entrada/salida/ajuste)
├── StockList.tsx               # Vista de stock actual
├── StockDetail.tsx             # Detalle de producto con histórico
├── AjusteInventario.tsx        # Herramienta de recuento
├── Panel.tsx                   # Dashboard con KPIs
├── Routes.tsx
├── services.ts
├── manifest.ts
└── README.md
```

#### 🎯 Campos Específicos por Sector

**PANADERÍA:**
- `lote` (número de horneada)
- `fecha_produccion` (para calcular caducidad)
- `caducidad_calculada` (fecha_produccion + dias_caducidad del producto)
- `estado` (fresco, día anterior, merma)

**RETAIL/BAZAR:**
- `ubicacion` (estantería/pasillo)
- `lote_proveedor`
- `fecha_compra`
- `alertas` (stock_minimo, stock_maximo, obsoleto)

**TALLER MECÁNICO:**
- `ubicacion` (almacén, mostrador, taller)
- `proveedor_id`
- `lote_proveedor`
- `garantia_hasta` (para repuestos con garantía)

#### ✅ Checklist de Implementación

- [ ] Backend: Migración de tablas (stock_items, stock_moves)
- [ ] Backend: Endpoints CRUD de movimientos
- [ ] Backend: Endpoint GET /stock (vista consolidada)
- [ ] Backend: Trigger auto-update stock_items al crear movimiento
- [ ] Backend: Función de valoración configurable
- [ ] Frontend: MovimientoForm.tsx
- [ ] Frontend: MovimientosList.tsx
- [ ] Frontend: StockList.tsx con filtros por almacén/producto
- [ ] Frontend: AjusteInventario.tsx (wizard de recuento)
- [ ] Frontend: Panel.tsx con KPIs (valor total, alertas, rotación)
- [ ] Testing: 10 casos de prueba por tipo de movimiento
- [ ] Documentación: README completo

---

### Prioridad 3: VENTAS/POS (Crítico para Panadería y Retail)

#### 📋 Especificación

**VENTAS** ya está al 100% en backend. Solo falta frontend (copiar estructura de clientes).

**POS** (Point of Sale) - Terminal de Venta

#### 🎯 Funcionalidades

**Para PANADERÍA:**
- ✅ Venta rápida con scanner o búsqueda
- ✅ Productos a peso (balanza integrada futura)
- ✅ Tickets y facturas simplificadas
- ✅ Arqueo de caja
- ✅ Turnos por cajero

**Para RETAIL/BAZAR:**
- ✅ Todo lo anterior
- ✅ Descuentos por producto
- ✅ Cupones y promociones
- ✅ Devoluciones con vale
- ✅ Múltiples métodos de pago

**Para TALLER MECÁNICO:**
- ❌ N/A (usan presupuestos y facturas tradicionales)

#### 📁 Estructura de Archivos

```
apps/tenant/src/modules/pos/
├── POSView.tsx                 # Vista principal del POS
├── components/
│   ├── ProductSearch.tsx       # Búsqueda/scanner
│   ├── Cart.tsx                # Carrito de la venta
│   ├── PaymentModal.tsx        # Modal de cobro
│   ├── CashDrawer.tsx          # Arqueo de caja
│   └── TicketPrint.tsx         # Impresión de ticket
├── Routes.tsx
├── services.ts
├── manifest.ts
└── README.md
```

---

### Prioridad 4: PRODUCCIÓN (Solo Panadería)

#### 📋 Especificación

**Objetivo:** Gestión de recetas, órdenes de producción y consumo de materias primas.

#### 🎯 Módulos

1. **Recetas** (ya existe RecetaForm.tsx, RecetasView.tsx)
   - Ingredientes y cantidades
   - Rendimiento (cuántas unidades produce)
   - Coste de producción

2. **Órdenes de Producción** (PENDIENTE)
   - Planificación diaria/semanal
   - Consumo automático de stock
   - Generación de lotes

3. **Calculadora de Producción** (ya existe)
   - Cálculo inverso: "necesito 100 panes, ¿cuánta harina?"

#### ✅ Checklist

- [x] RecetaForm.tsx
- [x] RecetasView.tsx
- [x] CalculadoraProduccion.tsx
- [ ] OrdenProduccion.tsx (nueva)
- [ ] ProduccionPanel.tsx (dashboard)
- [ ] Integración con inventario (consumo automático)
- [ ] Mermas y desperdicios

---

## 🗺️ Roadmap de Implementación (Recomendado)

### **SEMANA 1-2: PRODUCTOS**
- Día 1-2: Backend (defaults por sector + endpoints)
- Día 3-5: Frontend (Form + List + Routes)
- Día 6-7: Testing y documentación
- **Entregable:** Módulo Productos 100% operativo en 3 sectores

### **SEMANA 3-4: INVENTARIO**
- Día 1-3: Backend (migraciones + endpoints movimientos)
- Día 4-7: Frontend (MovimientoForm + StockList)
- Día 8-10: Ajustes y valoración
- **Entregable:** Control de stock básico funcional

### **SEMANA 5-6: POS**
- Día 1-3: POSView.tsx (interfaz principal)
- Día 4-5: Cart + PaymentModal
- Día 6-7: Integración con impresión
- Día 8-10: Arqueos y turnos
- **Entregable:** POS operativo para panadería y retail

### **SEMANA 7: PRODUCCIÓN (Solo Panadería)**
- Día 1-3: OrdenProduccion.tsx
- Día 4-5: Integración con inventario
- Día 6-7: Testing y ajustes
- **Entregable:** Módulo producción completo

### **SEMANA 8: PROVEEDORES + COMPRAS**
- Ya están al 95%/90%
- Solo ajustes y testing

---

## 📝 Plantilla de Desarrollo (Copiar y Pegar)

Para cada nuevo módulo, usa esta lista de verificación:

### ✅ Checklist Módulo Nuevo

```markdown
## Módulo: _______________

### Backend
- [ ] Crear defaults por sector en field_config.py
- [ ] Crear modelo SQLAlchemy (apps/backend/app/models)
- [ ] Crear router FastAPI (apps/backend/app/routers)
- [ ] Endpoints CRUD (GET, POST, PUT, DELETE)
- [ ] RLS aplicado (ensure_rls)
- [ ] Pruebas con curl

### Frontend
- [ ] Crear carpeta apps/tenant/src/modules/{nombre}
- [ ] services.ts con tipos TypeScript
- [ ] Form.tsx con configuración dinámica
- [ ] List.tsx con paginación/sort/búsqueda
- [ ] Routes.tsx
- [ ] manifest.ts
- [ ] Registrar en index.ts
- [ ] README.md completo (80+ líneas)

### Testing
- [ ] 5 casos de prueba backend (pytest)
- [ ] 3 casos de prueba frontend (manual)
- [ ] Testing con 3 sectores
- [ ] Validación de campos required
- [ ] Validación de permisos (roles)

### Documentación
- [ ] README del módulo
- [ ] Comentarios en código crítico
- [ ] Ejemplos en AGENTS.md
- [ ] Update de CHANGELOG.md
```

---

## 🔧 Herramientas y Comandos

### Crear configuración de campos para nuevo sector

```bash
# 1. Backend - Agregar sector a field_config.py
cd apps/backend/app/services
nano field_config.py

# 2. Agregar entry en SECTOR_DEFAULTS
SECTOR_DEFAULTS = {
    'panaderia': { ... },
    'retail': { ... },
    'taller': { ... },
    'nuevo_sector': {
        'productos': [
            {'field': 'codigo', 'visible': True, 'required': True, 'ord': 10},
            # ...
        ]
    }
}
```

### Probar configuración de campos

```bash
# Obtener campos para un módulo+sector
curl "http://localhost:8000/api/v1/tenant/settings/fields?module=productos&empresa=kusi-panaderia"

# Guardar override de tenant
curl -X PUT http://localhost:8000/api/v1/admin/field-config/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_slug": "kusi-panaderia",
    "module": "productos",
    "items": [
      {"field": "ingredientes", "visible": true, "required": true, "ord": 50}
    ]
  }'
```

### Ver logs de backend

```bash
docker logs -f backend --tail 100
```

---

## 📞 Soporte y Consultas

**Documentación de referencia:**
- 📄 [AGENTS.md](../AGENTS.md) - Arquitectura completa
- 📄 [apps/tenant/src/modules/clientes/README.md](../apps/tenant/src/modules/clientes/README.md)
- 📄 [apps/tenant/src/modules/ventas/README.md](../apps/tenant/src/modules/ventas/README.md)

**Comandos útiles:**
```bash
# Ver estructura de un módulo existente
tree apps/tenant/src/modules/clientes

# Copiar estructura de clientes a nuevo módulo
cp -r apps/tenant/src/modules/clientes apps/tenant/src/modules/nuevo_modulo
```

---

## 🎓 Convenciones de Código

### TypeScript
- 4 espacios de indentación
- camelCase para variables/funciones
- PascalCase para componentes React
- Tipos explícitos (no `any`)

### React
- Functional components con hooks
- `useEffect` para side effects
- `useMemo` para cálculos pesados
- `useCallback` para funciones pasadas a hijos

### Nombres de archivos
- `List.tsx` - Lista principal
- `Form.tsx` - Formulario crear/editar
- `Detail.tsx` - Vista detalle (opcional)
- `Panel.tsx` - Dashboard/métricas
- `services.ts` - API client
- `types.ts` - Tipos compartidos (si hay muchos)

---

## 📊 KPIs de Calidad

Cada módulo debe cumplir:

| Métrica | Objetivo |
|---------|----------|
| **Cobertura de tests** | ≥ 80% |
| **Documentación README** | ≥ 80 líneas |
| **TypeScript strict** | 100% |
| **Campos configurables** | ≥ 70% del total |
| **Loading states** | 100% de requests |
| **Error handling** | 100% de try/catch |
| **Accesibilidad** | aria-label en inputs |
| **Responsive** | Desktop + Mobile |

---

**Última actualización:** Octubre 2025
**Versión del documento:** 1.0
**Autor:** Equipo GestiQCloud
