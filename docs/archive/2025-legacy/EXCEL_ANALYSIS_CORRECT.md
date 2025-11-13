# 📊 Análisis Correcto - Excel del Cliente (Panadería Kusi)

## 🔍 Estructura Real del Excel

### Hoja: "REGISTRO"
```
| PRODUCTO | CANTIDAD | PRECIO UNITARIO VENTA | SOBRANTE DIARIO | VENTA DIARIA | TOTAL  |
|----------|----------|----------------------|-----------------|--------------|--------|
| PAN      |          |                      |                 |              | 146.44 | ← CATEGORÍA
| tapados  | 196      | 0.15                 |                 | 196          | 29.4   | ← PRODUCTO
| mestizo  | 10       | 0.15                 |                 | 10           | 1.5    | ← PRODUCTO
| TONI     |          |                      |                 |              |        | ← CATEGORÍA
| muffins  | 30       | 0.25                 |                 | 30           | 7.5    | ← PRODUCTO
```

---

## ✅ Mapeo Correcto para Nuestro Sistema

| Columna Excel | Mapear a | Razón |
|---------------|----------|-------|
| **PRODUCTO** | ✅ `name` | Nombre del producto para catálogo |
| **CANTIDAD** | ✅ `stock_initial` (opcional) | Stock de apertura/producción |
| **PRECIO UNITARIO VENTA** | ✅ `price` | Precio de venta del catálogo |
| **SOBRANTE DIARIO** | ❌ **IGNORAR** | Dato operacional (mermas, no es stock) |
| **VENTA DIARIA** | ❌ **IGNORAR** | Dato operacional (reporting, no catálogo) |
| **TOTAL** | ❌ **IGNORAR** | Cálculo derivado (precio × venta) |

---

## 🎯 Lógica de Negocio del Cliente

**Contexto**: Panadería que produce diariamente.

### Columnas Operacionales (NO para catálogo):
- **SOBRANTE DIARIO**: Productos NO vendidos al cierre → Para control de mermas
- **VENTA DIARIA**: Unidades vendidas ese día → Para reporting de ventas
- **TOTAL**: Ingresos del día (precio × venta_diaria) → Para caja diaria

### Columnas de Catálogo (SÍ importar):
- **PRODUCTO**: Nombre del producto master
- **PRECIO UNITARIO VENTA**: Precio estándar
- **CANTIDAD**: Puede ser stock inicial o producción típica (opcional)

---

## 🚫 Error Anterior

### ❌ Mapeo Incorrecto:
```python
keywords_map = {
    "cantidad": [..., "sobrante", ...]  # ❌ INCORRECTO
}
```

**Problema**: "SOBRANTE DIARIO" se mapeaba a `cantidad`, pero:
- **SOBRANTE** = Lo que NO se vendió (dato histórico)
- **CANTIDAD/STOCK** = Inventario actual (dato de catálogo)

### ✅ Mapeo Correcto:
```python
# Excel del cliente:
"SOBRANTE DIARIO" → IGNORAR ✅
"VENTA DIARIA" → IGNORAR ✅
"TOTAL" → IGNORAR ✅
"CANTIDAD" → stock_initial (opcional) ✅
"PRECIO UNITARIO VENTA" → price ✅
```

---

## 📋 Reglas de Mapeo Definitivas

### 1. **Columnas para Catálogo de Productos** (Datos Master)
```python
IMPORTAR = {
    "PRODUCTO": "name",              # Obligatorio
    "PRECIO UNITARIO VENTA": "price", # Obligatorio
    "CANTIDAD": "stock_initial",      # Opcional - puede ser None
    # Categoría: Auto-detectada por algoritmo (filas sin precio/cantidad)
}
```

### 2. **Columnas Operacionales** (Datos Temporales - IGNORAR)
```python
IGNORAR = [
    "SOBRANTE DIARIO",   # Control de mermas del día
    "VENTA DIARIA",      # Reporte de ventas del día
    "TOTAL",             # Cálculo (precio × venta)
    "Unnamed: X",        # Columnas sin nombre
]
```

### 3. **Detección de Categorías** (Algoritmo)
```python
# Si fila tiene nombre pero NO precio NI cantidad:
if precio_empty and cantidad_empty:
    current_category = nombre.upper()  # Es categoría
    # Productos siguientes heredan esta categoría
```

---

## 🎨 Vista Previa Correcta

### Lo que debería mostrar el sistema:

```
┌─────────────────────────────────────────────────┐
│  📊 Vista Previa - Stock-02-11-2025.xlsx        │
│  283 productos • 4 categorías                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  🏷️ Categorías: [PAN] [TONI] [EMPANADAS] [...]│
│                                                 │
│  🔗 Mapeo Auto-detectado:                       │
│      PRODUCTO → name ✅                          │
│      PRECIO UNITARIO VENTA → price ✅            │
│      CANTIDAD → stock_initial ✅                 │
│      SOBRANTE DIARIO → (ignorado) ⚪            │
│      VENTA DIARIA → (ignorado) ⚪                │
│      TOTAL → (ignorado) ⚪                       │
│                                                 │
│  👁️ Preview:                                    │
│  ┌────┬──────────┬────────┬──────┬──────────┐  │
│  │ #  │ Nombre   │ Precio │ Stock│ Categoría│  │
│  ├────┼──────────┼────────┼──────┼──────────┤  │
│  │ 1  │ tapados  │ $0.15  │  196 │ PAN      │✅│
│  │ 2  │ mestizo  │ $0.15  │   10 │ PAN      │✅│
│  │ 3  │ empanadas│ $0.20  │   30 │ PAN      │✅│
│  │ 4  │ muffins  │ $0.25  │   30 │ TONI     │✅│
│  └────┴──────────┴────────┴──────┴──────────┴──┘
│                                                 │
│  ℹ️ Columnas ignoradas (datos operacionales):  │
│     • SOBRANTE DIARIO                           │
│     • VENTA DIARIA                              │
│     • TOTAL                                     │
│                                                 │
│  [Cancelar]          [Importar 283 Productos →]│
└─────────────────────────────────────────────────┘
```

---

## 💡 Filosofía de Diseño

### Principio: "Separar Datos Master vs Datos Operacionales"

**Datos Master** (Catálogo de Productos):
- Nombre, Precio, Categoría
- Cambian raramente
- Son la "verdad única" del negocio
- **SÍ importar**

**Datos Operacionales** (Transacciones Diarias):
- Ventas diarias, sobrantes, mermas
- Cambian constantemente
- Son resultados de operaciones
- **NO importar al catálogo**
- Van a: `pos_receipts`, `sales`, `stock_moves`

---

## 🔄 Flujo Ideal para Panadería

### Escenario 1: Importar Catálogo (Una vez)
```python
# De Excel → products (master data)
{
  "name": "tapados",
  "price": 0.15,
  "category": "PAN",
  "unit": "unit"
}
```

### Escenario 2: Registrar Ventas Diarias (Diario)
```python
# No desde Excel, sino desde POS/Backend
# → pos_receipts, stock_moves
{
  "product_id": "uuid-tapados",
  "qty_sold": 196,
  "qty_remaining": 0,  # SOBRANTE DIARIO
  "date": "2025-11-02"
}
```

---

## ✅ Cambios Aplicados

1. **excel_analyzer.py**:
   - ❌ Eliminado "sobrante" de keywords de `cantidad`
   - ✅ Agregado "sobrante", "venta", "total", "diario" a keywords **IGNORAR**

2. **products_excel.py**:
   - ✅ Filtro explícito: NO mapear si columna contiene "sobrante", "venta", "diaria"
   - ✅ Solo mapea `CANTIDAD` si es dato de stock (no operacional)

3. **Documentación**:
   - ✅ Aclarado diferencia entre datos master vs operacionales

---

## 🧪 Testing con Excel Real

### Comando:
```bash
docker restart backend

# Importar Stock-02-11-2025.xlsx
# Resultado esperado:
# - PRODUCTO → name ✅
# - PRECIO UNITARIO VENTA → price ✅
# - CANTIDAD → stock_initial ✅
# - SOBRANTE DIARIO → (ignorado) ✅
# - VENTA DIARIA → (ignorado) ✅
# - TOTAL → (ignorado) ✅
```

---

## 📝 Recomendación Final

**El Excel del cliente es perfecto para SU negocio** (control diario).
**Nuestro sistema debe**:
1. ✅ Importar SOLO datos de catálogo (nombre, precio, categoría)
2. ❌ IGNORAR datos operacionales (sobrante, ventas, totales)
3. ✅ Generar datos operacionales desde nuestro POS/sistema

**No forzar al cliente a cambiar su Excel** ✅
**Extraer solo lo relevante para productos master** ✅

---

**Estado**: ✅ Correcciones aplicadas
**Testing**: Probar con Excel real
**Filosofía**: Datos Master ≠ Datos Operacionales
