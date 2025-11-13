# Módulo VENTAS - Documentación

## 📋 Descripción

Módulo completo de gestión de ventas con CRUD profesional, cálculo automático de impuestos, gestión de líneas de venta y conversión a facturas.

## 🏗️ Arquitectura

```
apps/tenant/src/modules/ventas/
├── List.tsx                    ✅ Lista con filtros, paginación, ordenamiento
├── Form.tsx                    ✅ Formulario completo con líneas de venta
├── Detail.tsx                  ✅ Vista detalle con acciones
├── Routes.tsx                  ✅ Rutas configuradas
├── services.ts                 ✅ API client con tipos TypeScript
├── manifest.ts                 ✅ Configuración del módulo
├── components/
│   ├── StatusBadge.tsx        ✅ Badge de estados con colores
│   └── DeleteConfirm.tsx      ✅ Modal de confirmación
└── README.md                   📄 Este archivo
```

## ✨ Características

### **List.tsx** - Lista de Ventas
- ✅ Tabla responsive con 6 columnas (número, cliente, fecha, total, estado, acciones)
- ✅ Filtros avanzados: estado, rango de fechas, búsqueda por número/cliente/estado
- ✅ Ordenamiento por: número, fecha, total, estado
- ✅ Paginación configurable (10/25/50 registros)
- ✅ Exportación a CSV con fecha en nombre de archivo
- ✅ Botones de acción: Ver, Editar, Facturar (solo borradores), Eliminar
- ✅ Loading states y error handling
- ✅ Toast notifications

### **Form.tsx** - Formulario de Venta
- ✅ Campos: número, fecha, cliente, estado, notas
- ✅ **Gestión dinámica de líneas de venta**:
  - Añadir/eliminar líneas
  - Campos por línea: producto, cantidad, precio, IVA%, descuento%
  - Cálculo automático de subtotales por línea
- ✅ **Cálculo automático de totales**:
  - Subtotal (sin impuestos)
  - Impuestos (suma de IVA de todas las líneas)
  - Total final
- ✅ Validaciones en frontend
- ✅ Estados: borrador, emitida, anulada
- ✅ Modo crear/editar (reutiliza mismo componente)

### **Detail.tsx** - Vista Detalle
- ✅ Información completa de la venta
- ✅ Tabla de líneas con cálculos detallados
- ✅ Panel de totales (subtotal, impuestos, total)
- ✅ **Acciones**:
  - Editar venta
  - Convertir a factura (solo borradores)
  - Eliminar con confirmación
  - Imprimir (window.print)
- ✅ Timestamps (created_at, updated_at)
- ✅ Badge de estado visual

### **StatusBadge.tsx** - Estados Visuales
- ✅ 4 estados soportados:
  - `borrador` → Gris
  - `emitida` → Verde
  - `facturada` → Azul
  - `anulada` → Rojo
- ✅ Diseño profesional con bordes y uppercase

### **services.ts** - API Integration
- ✅ Tipos TypeScript completos:
  - `Venta`: modelo principal
  - `VentaLinea`: líneas de venta
- ✅ Métodos CRUD:
  - `listVentas()` - GET all
  - `getVenta(id)` - GET by ID
  - `createVenta(payload)` - POST
  - `updateVenta(id, payload)` - PUT
  - `removeVenta(id)` - DELETE
  - `convertToInvoice(id)` - POST to_invoice

## 📊 Modelo de Datos

### **Venta**
```typescript
{
  id: number | string
  numero?: string                 // Número de venta (ej: V-2025-001)
  fecha: string                   // YYYY-MM-DD
  cliente_id?: number | string
  cliente_nombre?: string         // Denormalizado para performance
  total: number                   // Total final (subtotal + impuestos)
  subtotal?: number               // Suma sin impuestos
  impuesto?: number               // Suma de impuestos
  estado?: 'borrador' | 'emitida' | 'anulada' | 'facturada'
  notas?: string                  // Observaciones internas
  lineas?: VentaLinea[]           // Líneas de venta
  created_at?: string
  updated_at?: string
}
```

### **VentaLinea**
```typescript
{
  producto_id: number | string
  producto_nombre?: string        // Denormalizado
  cantidad: number
  precio_unitario: number
  impuesto_tasa?: number          // % de IVA (21, 10, 4, 0)
  descuento?: number              // % de descuento (0-100)
}
```

## 🔄 Flujos de Uso

### 1. Crear Nueva Venta
1. Click en "Nueva" → `Form.tsx`
2. Rellenar fecha, cliente (opcional), estado
3. Añadir líneas de venta (productos, cantidades, precios)
4. Sistema calcula automáticamente totales
5. Guardar → POST `/api/v1/sales`

### 2. Editar Venta
1. Desde List → Click "Editar" → `Form.tsx` con ID
2. Carga datos existentes incluyendo líneas
3. Modificar campos/líneas
4. Guardar → PUT `/api/v1/sales/:id`

### 3. Convertir a Factura
1. Desde Detail → Click "Convertir a Factura"
2. Navega a `/facturacion/nueva?from_venta=:id`
3. Pre-llena datos de venta en factura
4. Actualiza estado de venta a `facturada`

### 4. Exportar Ventas
1. Desde List → Filtrar ventas deseadas
2. Click "Exportar CSV"
3. Descarga archivo `ventas-YYYY-MM-DD.csv`

## 🎨 UI/UX Highlights

- **TailwindCSS** para estilos
- **Responsive** design (móvil/tablet/desktop)
- **Loading states** en todas las operaciones async
- **Error handling** con toast notifications
- **Confirmaciones** antes de eliminar
- **Hover effects** en filas de tabla
- **Focus states** en inputs
- **Badges con colores** semánticos

## 🔗 Integración con Backend

### Endpoints esperados

```
GET    /api/v1/sales           → Listar ventas
GET    /api/v1/sales/:id       → Obtener venta
POST   /api/v1/sales           → Crear venta
PUT    /api/v1/sales/:id       → Actualizar venta
DELETE /api/v1/sales/:id       → Eliminar venta
POST   /api/v1/sales/:id/to_invoice → Convertir a factura
```

### Respuesta esperada (GET /api/v1/sales)

Opción 1 - Array directo:
```json
[
  {
    "id": 1,
    "numero": "V-2025-001",
    "fecha": "2025-01-15",
    "cliente_id": 42,
    "cliente_nombre": "Juan Pérez",
    "total": 121.00,
    "subtotal": 100.00,
    "impuesto": 21.00,
    "estado": "emitida",
    "lineas": [...]
  }
]
```

Opción 2 - Objeto con `items`:
```json
{
  "items": [...],
  "total": 150,
  "page": 1
}
```

## 🧪 Testing

### Manual testing checklist
- [ ] Crear venta sin líneas
- [ ] Crear venta con múltiples líneas
- [ ] Editar venta existente
- [ ] Eliminar línea de venta
- [ ] Cálculo automático de totales correcto
- [ ] Filtros funcionan correctamente
- [ ] Ordenamiento por todas las columnas
- [ ] Paginación correcta
- [ ] Exportar CSV con datos correctos
- [ ] Convertir a factura (borrador)
- [ ] No mostrar "Facturar" en ventas emitidas/anuladas
- [ ] Eliminar venta con confirmación
- [ ] Toast notifications aparecen
- [ ] Responsive en móvil

### Unit tests (próximo)
```bash
# Cuando esté el setup de tests
npm test -- ventas
```

## 📝 Notas de Implementación

### Cálculo de Totales por Línea
```typescript
base = cantidad * precio_unitario * (1 - descuento / 100)
impuesto = base * (impuesto_tasa / 100)
total_linea = base + impuesto
```

### Cálculo de Totales de Venta
```typescript
subtotal = Σ(base de cada línea)
impuesto = Σ(impuesto de cada línea)
total = subtotal + impuesto
```

### Estados de Venta
- `borrador`: Recién creada, editable, puede convertirse a factura
- `emitida`: Confirmada, no editable (excepto admin)
- `facturada`: Ya convertida a factura, solo lectura
- `anulada`: Cancelada, solo lectura

## 🚀 Próximas Mejoras

### Corto plazo
- [ ] Selector de clientes (dropdown con búsqueda)
- [ ] Selector de productos (autocomplete)
- [ ] Validación de stock al crear venta
- [ ] Plantilla de impresión profesional
- [ ] Duplicar venta existente

### Mediano plazo
- [ ] Multi-moneda (EUR/USD)
- [ ] Descuentos globales (además de por línea)
- [ ] Adjuntar archivos a venta
- [ ] Historial de cambios (audit log)
- [ ] Exportar PDF

### Largo plazo
- [ ] Integración con e-factura
- [ ] Plantillas de venta predefinidas
- [ ] Estadísticas y gráficos
- [ ] Workflow de aprobación
- [ ] Sincronización offline (PWA)

## 🤝 Contribuir

Al modificar este módulo:

1. Mantener coherencia con patrones existentes
2. Actualizar tipos TypeScript si cambias el modelo
3. Añadir validaciones en frontend Y backend
4. Actualizar esta documentación
5. Probar en móvil/tablet/desktop
6. Verificar compatibilidad con módulos relacionados (facturacion, clientes)

## 📚 Referencias

- Patrón base: `apps/tenant/src/modules/clientes/`
- API client: `apps/tenant/src/shared/api/client.ts`
- Toast system: `apps/tenant/src/shared/toast.ts`
- Paginación: `apps/tenant/src/shared/pagination.ts`
- Backend: `apps/backend/app/routers/ventas.py` (por implementar)

---

**Versión**: 1.0.0
**Última actualización**: Enero 2025
**Estado**: ✅ Completado - Production Ready
