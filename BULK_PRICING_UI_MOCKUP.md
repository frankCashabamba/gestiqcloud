# UI Mockup: Venta por Cantidad (Panadería)

## Ubicación en Aplicación

```
┌─ GestIQ Cloud ────────────────────────────────────────────┐
│ Dashboard | Productos | Ventas | Configuración | Ayuda   │
│                                    ↓                       │
│            ┌─ Configuración ──────────────────────┐       │
│            │ General | Fiscal | Operativo | Admin │       │
│            │                ↓                      │       │
│            │     [VISTA OPERATIVO]                │       │
│            └──────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────┘
```

## Pantalla: Configuración Operativa

```
═══════════════════════════════════════════════════════════════════════════════
                         ⚙️ CONFIGURACIÓN OPERATIVA
═══════════════════════════════════════════════════════════════════════════════

┌─ POS SETTINGS ─────────────────────────────────────────────────────────────┐
│                                                                             │
│  📏 Ancho ticket (mm)              IVA default (%)            Ventana        │
│  ┌──────────────────┐             ┌──────────────┐          devolución      │
│  │ 80               │             │ 12           │          ┌───────────┐   │
│  └──────────────────┘             └──────────────┘          │ 30        │   │
│                                                              └───────────┘   │
│  ☑ Precios incluyen impuestos                               ☑ Store credit  │
│  ☑ Store credit habil.            ☑ Store credit un solo uso               │
│  Expiracion store credit (meses)   Minimo para exigir factura               │
│  ┌──────────────────┐              ┌──────────────────────┐                 │
│  │ 12               │              │ 100                  │                 │
│  └──────────────────┘              └──────────────────────┘                 │
│  ☑ Requerir datos del comprador sobre ese monto                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ VENTA POR CANTIDAD (PANADERÍA) ──────────────────────────────────────────┐
│                                                                             │
│  Configura el precio fijo para una cantidad específica de cada producto    │
│  (ej: 6 tapapados por $1)                                                 │
│                                                                             │
│  ┌─ AGREGAR PRODUCTO ────────────────────────────────────────────────┐    │
│  │                                                                   │    │
│  │  Seleccionar Producto*    Cantidad*    Precio*           [Botón] │    │
│  │  ┌──────────────────────┐ ┌────────┐  ┌──────────┐               │    │
│  │  │ -- Seleccionar -- ▼ │ │ 6      │  │ 1.00     │               │    │
│  │  │ Tapapados            │ │        │  │          │               │    │
│  │  │ Roscas               │ └────────┘  └──────────┘       [Agregar]│    │
│  │  │ Biscochos            │                                 │    │
│  │  │ Churros              │                                 │    │
│  │  └──────────────────────┘                                 │    │
│  │                                                                   │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─ PRODUCTOS CONFIGURADOS ──────────────────────────────────────────┐    │
│  │                                                                   │    │
│  │  Producto    │ Cantidad │ Precio  │ Precio/Unidad │ Acción      │    │
│  │  ─────────────┼──────────┼─────────┼───────────────┼─────────────│    │
│  │  Tapapados   │    6     │ $1.00   │ $0.1667       │ [Eliminar]  │    │
│  │  Roscas      │   12     │ $1.80   │ $0.1500       │ [Eliminar]  │    │
│  │  Biscochos   │   24     │ $2.40   │ $0.1000       │ [Eliminar]  │    │
│  │                                                                   │    │
│  │  No hay más productos configurados...                           │    │
│  │                                                                   │    │
│  └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─ NUMERACIÓN ───────────────────────────────────────────────────────────────┐
│ [...]                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

                              [💾 Save configuration]

═══════════════════════════════════════════════════════════════════════════════
```

## Secuencia de Acciones: Agregar Producto

```
PASO 1: Abrir dropdown
┌──────────────────────────────────────────────────────────────────┐
│ Seleccionar Producto *                                           │
│ ┌──────────────────────────────────┐                             │
│ │ -- Seleccionar -- ▼              │                             │
│ │                                  │                             │
│ ├──────────────────────────────────┤                             │
│ │ Tapapados                    ← ← ← Usuario hace clic           │
│ │ Roscas                                                          │
│ │ Biscochos                                                       │
│ │ Churros                                                         │
│ └──────────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────────┘

PASO 2: Seleccionar producto
┌──────────────────────────────────────────────────────────────────┐
│ Seleccionar Producto *                                           │
│ ┌──────────────────────────────────┐                             │
│ │ Roscas ▼                         │ ← Usuario selecciona        │
│ └──────────────────────────────────┘                             │
│                                                                  │
│ Cantidad (unidades) *   Precio (por conjunto) *                 │
│ ┌──────────────────────┐ ┌──────────────────────┐               │
│ │ 6                    │ │ 1.00                 │               │
│ └──────────────────────┘ └──────────────────────┘               │
│                                    [Agregar]                     │
└──────────────────────────────────────────────────────────────────┘

PASO 3: Cambiar cantidad
┌──────────────────────────────────────────────────────────────────┐
│ Cantidad (unidades) *                                            │
│ ┌──────────────────────┐                                         │
│ │ 6                    │ ← Usuario limpia y escribe 12           │
│ │ 1                    │                                         │
│ │ 2                    │                                         │
│ │ ...                  │                                         │
│ │ 12                   │ ← Muestra el valor mientras escribe     │
│ └──────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────┘

PASO 4: Cambiar precio
┌──────────────────────────────────────────────────────────────────┐
│ Precio (por conjunto) *                                          │
│ ┌──────────────────────┐                                         │
│ │ 1.00                 │ ← Usuario limpia y escribe 1.80         │
│ └──────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────┘

PASO 5: Hacer clic en Agregar
┌──────────────────────────────────────────────────────────────────┐
│ [Agregar] ← Usuario hace clic                                    │
│                                                                  │
│ ✓ Validaciones:                                                  │
│   ✓ ¿Producto seleccionado? SI                                  │
│   ✓ ¿Cantidad > 0? SI (12)                                      │
│   ✓ ¿Precio ≥ 0? SI (1.80)                                      │
│   ✓ ¿Producto no está duplicado? SI                             │
│                                                                  │
│ → RESULTADO: ✓ Producto agregado a bulk pricing                │
│ → TABLA ACTUALIZA: Nueva fila "Roscas 12 × $1.80"              │
│ → FORMULARIO SE LIMPIA para agregar otro producto              │
└──────────────────────────────────────────────────────────────────┘

PASO 6: Tabla actualizada
┌──────────────────────────────────────────────────────────────────┐
│  Productos Configurados                                          │
│  ──────────────────────────────────────────────────────────────  │
│  Producto    │ Cantidad │ Precio  │ Precio/Unidad │ Acción      │
│  ──────────────┼──────────┼─────────┼───────────────┼─────────────│
│  Tapapados   │    6     │ $1.00   │ $0.1667       │ [Eliminar]  │
│  Roscas      │   12     │ $1.80   │ $0.1500       │ [Eliminar]  │ ← NUEVA
│  Biscochos   │   24     │ $2.40   │ $0.1000       │ [Eliminar]  │
└──────────────────────────────────────────────────────────────────┘

PASO 7: Guardar
┌──────────────────────────────────────────────────────────────────┐
│                    [💾 Save configuration]                        │
│                                                                  │
│ → ENVIADO al servidor: PUT /company-settings                    │
│ → JSON: { pos_config: { bulk_pricing_items: [...] } }           │
│ → RESPUESTA: ✓ Configuración guardada                           │
│ → UI: ✓ Guardada exitosamente                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Secuencia: Eliminar Producto

```
┌──────────────────────────────────────────────────────────────────┐
│  Productos Configurados                                          │
│  ──────────────────────────────────────────────────────────────  │
│  Producto    │ Cantidad │ Precio  │ Precio/Unidad │ Acción      │
│  ──────────────┼──────────┼─────────┼───────────────┼─────────────│
│  Tapapados   │    6     │ $1.00   │ $0.1667       │ [Eliminar]  │
│  Roscas      │   12     │ $1.80   │ $0.1500       │ [Eliminar] │ ← Click
│  Biscochos   │   24     │ $2.40   │ $0.1000       │ [Eliminar]  │
└──────────────────────────────────────────────────────────────────┘

RESULTADO:

┌──────────────────────────────────────────────────────────────────┐
│  Productos Configurados                                          │
│  ──────────────────────────────────────────────────────────────  │
│  Producto    │ Cantidad │ Precio  │ Precio/Unidad │ Acción      │
│  ──────────────┼──────────┼─────────┼───────────────┼─────────────│
│  Tapapados   │    6     │ $1.00   │ $0.1667       │ [Eliminar]  │
│  Biscochos   │   24     │ $2.40   │ $0.1000       │ [Eliminar]  │
│                                                                  │
│  ✓ Producto eliminado                                           │
└──────────────────────────────────────────────────────────────────┘
```

## Estados y Mensajes

### ✓ Éxito
```
┌─────────────────────────────────────────┐
│ ✓ Producto agregado a bulk pricing      │
│                                         │
│ Formulario limpiado. Listo para más.   │
└─────────────────────────────────────────┘
```

### ❌ Errores
```
Error 1: Falta seleccionar producto
┌─────────────────────────────────────────┐
│ ❌ Debes seleccionar un producto       │
└─────────────────────────────────────────┘

Error 2: Cantidad inválida
┌─────────────────────────────────────────┐
│ ❌ La cantidad debe ser mayor a 0       │
└─────────────────────────────────────────┘

Error 3: Producto duplicado
┌────────────────────────────────────────────────────┐
│ ❌ Este producto ya está en la lista.             │
│ Edítalo o elimínalo primero.                       │
└────────────────────────────────────────────────────┘

Error 4: Guardado
┌─────────────────────────────────────────┐
│ ❌ Error al guardar configuración       │
│ Por favor, intenta de nuevo.            │
└─────────────────────────────────────────┘
```

### 💾 Guardado
```
┌─────────────────────────────────────────┐
│ 💾 Guardando configuración...           │
│                                         │
│ (Spinner girando)                       │
└─────────────────────────────────────────┘

↓

┌─────────────────────────────────────────┐
│ ✓ Configuración guardada exitosamente   │
│                                         │
│ Los cambios aplican inmediatamente.     │
└─────────────────────────────────────────┘
```

## Estados de Carga

```
INICIAL: Cargando productos
┌──────────────────────────────────────────────────────────────────┐
│ Seleccionar Producto *                                           │
│ ┌──────────────────────────────────┐                             │
│ │ ⏳ Cargando productos...        │                             │
│ └──────────────────────────────────┘                             │
│                                                                  │
│ [Agregar] (deshabilitado)                                        │
└──────────────────────────────────────────────────────────────────┘

CARGADO: Lista disponible
┌──────────────────────────────────────────────────────────────────┐
│ Seleccionar Producto *                                           │
│ ┌──────────────────────────────────┐                             │
│ │ -- Seleccionar -- ▼              │                             │
│ │ Tapapados (1234)                 │                             │
│ │ Roscas (5678)                    │                             │
│ │ Biscochos (9012)                 │                             │
│ └──────────────────────────────────┘                             │
│                                                                  │
│ [Agregar] (habilitado al seleccionar)                            │
└──────────────────────────────────────────────────────────────────┘
```

## Tabla Vacía

```
┌──────────────────────────────────────────────────────────────────┐
│  Productos Configurados                                          │
│  ──────────────────────────────────────────────────────────────  │
│  Producto    │ Cantidad │ Precio  │ Precio/Unidad │ Acción      │
│  ──────────────┼──────────┼─────────┼───────────────┼─────────────│
│                                                                  │
│       No hay productos configurados. Agrega uno arriba.         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Responsive Design

### Desktop (1024+px)
```
┌─────────────────────────────────────────────────────────────────┐
│ Seleccionar  Cantidad  Precio  [Agregar]                        │
│ [Dropdown]   [Input]   [Input]  [Botón]                         │
└─────────────────────────────────────────────────────────────────┘
```

### Tablet (768px)
```
┌─────────────────────────────────────────────────────────────────┐
│ Seleccionar              [Agregar]                              │
│ [Dropdown]                                                      │
│                                                                 │
│ Cantidad        Precio                                          │
│ [Input]         [Input]                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile (< 768px)
```
┌──────────────────────────┐
│ Seleccionar Producto *   │
│ [Dropdown ▼]             │
│                          │
│ Cantidad (unidades) *    │
│ [Input: 6]               │
│                          │
│ Precio (por conjunto) *  │
│ [Input: 1.00]            │
│                          │
│ [Agregar 📲]             │
└──────────────────────────┘

Tabla se vuelve horizontal (scroll)
```

---

Este mockup muestra exactamente cómo se verá la interfaz de usuario en la sección Operativa. El diseño es intuitivo, responsive y fácil de usar.
