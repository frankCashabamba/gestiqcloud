# Análisis Archivo Excel Cliente Real: 22-10-20251.xlsx

## 📊 Estructura del Archivo

**Total hojas:** 4
- **REGISTRO** (2,037 filas) → **Inventario diario de productos** ✅
- **compras** (34 filas) → Registro de compras a proveedores
- **LECHE** → Control de leche
- **Hoja1** → Vacía

## 🎯 Hoja REGISTRO - Inventario Diario

### Columnas Detectadas:
```
A: PRODUCTO
B: CANTIDAD (stock inicial del día)
C: PRECIO UNITARIO VENTA
D: SOBRANTE DIARIO
E: VENTA DIARIA (calculada: =CANTIDAD - SOBRANTE)
F: TOTAL (calculado: =VENTA * PRECIO)
G: (vacía/totales)
```

### Ejemplo de Datos Reales:
| PRODUCTO | CANTIDAD | PRECIO | SOBRANTE | VENTA | TOTAL |
|----------|----------|--------|----------|-------|-------|
| tapados | 196 | 0.15 | - | 196 | 29.40 |
| pan dulce-mestizo | 10 | 0.15 | - | 10 | 1.50 |
| empanadas queso | 30 | 0.20 | - | 30 | 6.00 |
| enrollados | 40 | 0.17 | - | 40 | 6.80 |
| bizcochos | 140 | 0.17 | - | 140 | 23.80 |

**Total productos:** ~2,000+ registros históricos

## ✅ Compatibilidad con SPEC-1

### El importador `excel_importer_spec1.py` PUEDE procesar este archivo:

**Mapeo automático:**
- `CANTIDAD` → `stock_inicial` en `daily_inventory`
- `VENTA DIARIA` → `venta_unidades` + `stock_moves` (kind='sale')
- `SOBRANTE DIARIO` → `stock_final`
- `PRECIO UNITARIO VENTA` → `precio_venta`
- `PRODUCTO` → `products` (crea/actualiza automáticamente)

### ✅ Funcionalidades que se poblarán:

1. **Tabla `products`**
   - Crea ~40+ productos únicos (tapados, pan dulce, empanadas, etc.)
   - Con nombre y precio inicial

2. **Tabla `daily_inventory`**
   - 2,037 registros de inventario histórico
   - Stock inicial, ventas, sobrante por día/producto

3. **Tabla `stock_moves`** (opcional con `simulate_sales=True`)
   - Genera movimientos de venta históricos
   - Permite análisis de tendencias

4. **Tabla `stock_items`**
   - Inicializa stock actual basado en último registro
   - **La columna CANTIDAD se convertirá en stock real** ✅

## 🚀 Cómo Importar

### Opción 1: API directa (Recomendado)
```bash
curl -X POST http://localhost:8082/api/v1/spec1/import-excel \
  -F "file=@22-10-20251.xlsx" \
  -F "sheet_name=REGISTRO" \
  -F "simulate_sales=true" \
  -H "Authorization: Bearer {tu-token}"
```

### Opción 2: Frontend (Interfaz gráfica)
1. Ir a `/panaderia/importador` 
2. Subir archivo `22-10-20251.xlsx`
3. Seleccionar hoja "REGISTRO"
4. Click "Importar"

### Resultado Esperado:
```json
{
  "status": "success",
  "stats": {
    "products_created": 40,
    "products_updated": 0,
    "daily_inventory_created": 2037,
    "stock_items_initialized": 40,
    "stock_moves_created": 2037,
    "errors": [],
    "warnings": []
  }
}
```

## 📦 Stock Inicial Poblado

**Sí, la columna CANTIDAD se guardará como stock:**

```sql
-- Ejemplo resultado en BD:
INSERT INTO stock_items (product_id, qty_on_hand, warehouse_id) 
VALUES 
  ('uuid-tapados', 196, 'default-warehouse'),
  ('uuid-pan-dulce', 10, 'default-warehouse'),
  ('uuid-empanadas-queso', 30, 'default-warehouse');
```

## 🔄 Otras Hojas del Archivo

### Hoja "compras"
- Proveedor Nestlé, Cocacola, etc.
- **Formato irregular** (necesita limpieza manual)
- Posible importador futuro para `purchase_records`

### Hoja "LECHE"
- Control de leche (probablemente para quesería)
- Compatible con `milk_records` de SPEC-1

## ⚠️ Consideraciones

1. **Fechas:** El importador usa la fecha actual si no se especifica
   - Para datos históricos, enviar parámetro `fecha=YYYY-MM-DD`

2. **Duplicados:** Sistema detecta por hash (producto+fecha+cantidad)
   - Re-importar NO duplica registros

3. **Validación:** Acepta hasta 5,000 filas por importación
   - Este archivo (2,037) está OK ✅

4. **Formato CSV:** El frontend también soporta CSV
   - Exportar desde Excel a CSV funciona igual

## 🎯 Siguiente Paso

**Para poblar ERP completo con datos reales:**

```bash
# 1. Levantar backend
docker compose up -d backend db

# 2. Importar productos y stock
python scripts/import_client_data.py --file 22-10-20251.xlsx --sheet REGISTRO

# O via API:
curl -X POST http://localhost:8082/api/v1/spec1/import-excel \
  -F "file=@22-10-20251.xlsx" \
  -F "sheet_name=REGISTRO" \
  -F "simulate_sales=true"
```

**Resultado:** ERP poblado con 40+ productos y 2,000+ registros históricos listos para probar ✅
