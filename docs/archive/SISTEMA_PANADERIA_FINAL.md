# 🍞 SISTEMA PANADERÍA KUSI - PROFESIONAL

## ✅ CONFIGURACIÓN COMPLETADA

### 🎯 Al entrar al sistema:
```
http://localhost:8082/kusi-panaderia
```
**→ Redirige AUTOMÁTICAMENTE al POS** (Punto de Venta)

---

## 📱 MÓDULOS DISPONIBLES (Solo 8 - Panadería Profesional)

### 1. 🛒 **PUNTO DE VENTA (POS)**
**URL:** `/kusi-panaderia/mod/pos`

**Funciones:**
- ✅ Grid de productos (239 disponibles)
- ✅ Ventas rápidas con un click
- ✅ Búsqueda instantánea
- ✅ Scanner de código de barras
- ✅ Múltiples formas de pago
- ✅ Impresión de tickets
- ✅ Turnos de caja
- ✅ Devoluciones con vales

---

### 2. 🍞 **PRODUCCIÓN (Recetas)**
**URL:** `/kusi-panaderia/mod/produccion/recetas`

**Receta incluida: PAN TAPADO - 144 unidades**

**Ingredientes:**
1. Harina: 10 lb (Saco 110 lb - $25)
2. Grasa: 2.5 lb (Caja 50 kg - $80)
3. Manteca vegetal: 0.02 lb (Caja 50 lb - $45)
4. Margarina: 1 lb (Caja 50 lb - $35)
5. Huevos: 8 und (Cubeta 360 - $50)
6. Agua: 2 litros
7. Manteca chancho: 0.5 lb (Balde 10 lb - $15)
8. Azúcar: 1.5 lb (Saco 50 lb - $22)
9. Sal: 0.1875 lb (Saco 50 lb - $8)
10. Levadura: 0.375 lb (Bolsa 1 lb - $12)

**Cálculos automáticos:**
- ✅ Costo total receta
- ✅ Costo por unidad
- ✅ Precio sugerido de venta
- ✅ Análisis de rentabilidad (3 escenarios)
- ✅ Edición de precios en tiempo real

---

### 3. 📦 **INVENTARIO**
**URL:** `/kusi-panaderia/mod/inventario/productos`

**Funciones:**
- ✅ Lista completa (239 productos)
- ✅ Edición inline (click "Editar")
- ✅ Filtro por categoría
- ✅ Búsqueda rápida
- ✅ Campos editables:
  - Nombre
  - Código/SKU
  - Precio
  - Stock
  - Categoría

**Categorías:**
- Panadería
- Pastelería
- Bollería
- Bebidas
- Otros

---

### 4. 📊 **VENTAS**
Reportes de ventas diarias/mensuales

---

### 5. 🛍️ **COMPRAS**
Control de compras de insumos

---

### 6. 👥 **PROVEEDORES**
Gestión de proveedores de insumos

---

### 7. 💵 **GASTOS**
Control de gastos diarios (luz, agua, salarios, etc.)

---

### 8. 👤 **USUARIOS**
Gestión de empleados y permisos

---

## ⚙️ CONFIGURACIÓN DEL SISTEMA

### Moneda y Regional:
- **Moneda:** USD ($)
- **País:** Ecuador (EC)
- **IVA:** 15%
- **Idioma:** es-EC
- **Zona horaria:** America/Guayaquil

### POS:
- **Tickets:** 58mm
- **Precios:** Incluyen IVA
- **Devoluciones:** 15 días
- **Vales:** Un solo uso, 12 meses caducidad

---

## 🚀 CÓMO USAR

### 1. Iniciar Sistema:
```bash
docker compose up -d
```

### 2. Acceder:
```
http://localhost:8082/kusi-panaderia
```
**→ Abre automáticamente el POS**

### 3. Flujo Diario:

#### 🌅 MAÑANA:
1. Entra al sistema → POS se abre automáticamente
2. Abre turno de caja
3. Ve a **Producción/Recetas** para ver costos del día
4. Actualiza stock de productos horneados

#### 🏪 DURANTE EL DÍA:
1. **POS** → Vende con clicks (ya estás ahí)
2. Grid de productos visible
3. Click en producto → añade al carrito
4. Click "COBRAR" → recibe pago
5. Imprime ticket automático

#### 🌙 NOCHE:
1. Cierra turno en POS
2. Revisa **Ventas** del día
3. **Inventario** → Ajusta stock si es necesario
4. **Recetas** → Planifica producción de mañana

---

## 🎯 NAVEGACIÓN RÁPIDA

### URLs Directas:
```
Inicio (→POS):  http://localhost:8082/kusi-panaderia
POS:            http://localhost:8082/kusi-panaderia/mod/pos
Recetas:        http://localhost:8082/kusi-panaderia/mod/produccion/recetas
Inventario:     http://localhost:8082/kusi-panaderia/mod/inventario/productos
Ventas:         http://localhost:8082/kusi-panaderia/mod/ventas
Compras:        http://localhost:8082/kusi-panaderia/mod/compras
Proveedores:    http://localhost:8082/kusi-panaderia/mod/proveedores
Gastos:         http://localhost:8082/kusi-panaderia/mod/gastos
Usuarios:       http://localhost:8082/kusi-panaderia/mod/usuarios
```

### Menú Lateral:
Solo muestra 8 módulos esenciales:
1. 🛒 Punto de Venta
2. 🍞 Producción
3. 📦 Inventario
4. 📊 Ventas
5. 🛍️ Compras
6. 👥 Proveedores
7. 💵 Gastos
8. 👤 Usuarios



---

## 💰 EJEMPLO COMPLETO - PAN TAPADO

### Costos Calculados:
```
Ingredientes:  $7.50 (aprox)
Rendimiento:   144 unidades
Costo/unidad:  $0.052

Precio venta sugerido: $0.13 (margen 150%)
```

### Análisis de Rentabilidad:

| Precio | Margen | Ganancia/und | Ganancia total |
|--------|--------|--------------|----------------|
| $0.10  | 92%    | $0.048       | $6.91          |
| $0.15  | 188%   | $0.098       | $14.11         |
| $0.20  | 285%   | $0.148       | $21.31         |

---

## 🔧 AJUSTAR PRECIOS REALES

### En Recetas:
1. Ve a `http://localhost:8082/kusi-panaderia/mod/produccion/recetas`
2. Click "✏️ Editar"
3. Cambia los precios de compra a los reales
4. Los costos se actualizan automáticamente
5. Click "💾 Guardar"

### En Inventario:
1. Ve a `http://localhost:8082/kusi-panaderia/mod/inventario/productos`
2. Busca un producto
3. Click "✏️ Editar"
4. Cambia precio, stock, categoría
5. Click "✓ Guardar"

---

## 📊 BASE DE DATOS

### Productos: 239
### Tenant ID: `5c7bea07-05ca-457f-b321-722b1628b170`
### Moneda: USD
### IVA: 15%

---

## ✅ LO QUE FUNCIONA AL 100%

1. ✅ **Entrada automática al POS** (sin dashboard innecesario)
2. ✅ **Grid de productos visible** (239 productos)
3. ✅ **Ventas con 1 click**
4. ✅ **Receta Pan Tapado** con cálculos automáticos
5. ✅ **Edición de productos** en inventario
6. ✅ **Moneda parametrizada** (USD, se puede cambiar)
7. ✅ **Solo 8 módulos** (sin ruido)
8. ✅ **Backend operativo** con todos los endpoints

---

## 🆘 SI ALGO NO FUNCIONA

### Verificar servicios:
```bash
docker compose ps
```

### Reiniciar todo:
```bash
docker compose down
docker compose up -d
```

### Ver logs:
```bash
docker logs backend --tail 50
docker logs tenant --tail 20
```

### Verificar productos:
```bash
curl http://localhost:8000/api/v1/products/?limit=3
```

---

## 🎯 PRÓXIMOS PASOS (Opcional)

1. **Ajustar precios reales** en recetas
2. **Asignar categorías** a todos los productos
3. **Configurar impresora** térmica
4. **Agregar más recetas** (bollos, empanadas, etc.)
5. **Personalizar** colores y logo

---

**Sistema optimizado para panadería.**
**Sin módulos innecesarios.**
**Directo al POS al entrar.**
**100% funcional.**

Última actualización: Enero 2025
