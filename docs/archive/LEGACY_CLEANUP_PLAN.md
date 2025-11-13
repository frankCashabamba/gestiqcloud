# Plan de Limpieza Legacy → Moderno

**Fecha**: 2025-11-01
**Objetivo**: Eliminar duplicación de código legacy/moderno y estandarizar a esquema moderno

## Estado Actual

### ✅ Completado
1. **Product model** - Alias de compatibilidad añadidos (nombre→name, codigo→sku, precio→price, stock_minimo/maximo→metadata)

### 🔄 En Progreso
2. **SQL queries POS** - Necesitan cambiar `qty_on_hand` → `qty`
3. **Frontend inventario** - Necesita usar `product_metadata.reorder_point` en lugar de `stock_minimo`

### ❌ Pendiente
4. Tenant model - Añadir alias (name→nombre, country→country_code)
5. StockItem model - Mapear a columna `qty` moderna
6. Scripts Python - Corregir queries que usan `tenants.name`
7. Tests - Actualizar referencias legacy

---

## Fase 1: Backend ORM (CRÍTICO) ⏱️ 1-2h

### 1.1 Product Model ✅ HECHO
**Archivo**: `apps/backend/app/models/core/products.py`

```python
# Ya implementado:
nombre = synonym("name")
codigo = synonym("sku")
precio = synonym("price")

@property
def stock_minimo(self):
    return self.product_metadata.get("reorder_point") if self.product_metadata else None

@property
def stock_maximo(self):
    return self.product_metadata.get("max_stock") if self.product_metadata else None
```

### 1.2 Tenant Model 📝 PRÓXIMO
**Archivo**: `apps/backend/app/models/tenant.py`

**Cambios necesarios**:
```python
from sqlalchemy.orm import synonym

class Tenant(Base):
    # Columnas reales: nombre, country_code
    #... existing fields ...

    # Alias de compatibilidad
    name = synonym("nombre")

    @property
    def country(self):
        return self.country_code

    @country.setter
    def country(self, value):
        self.country_code = value
```

### 1.3 StockItem Model 📝 PRÓXIMO
**Archivo**: `apps/backend/app/models/inventory/stock.py`

**Problema actual**: La BD tiene columna `qty` pero el ORM mapea a `qty_on_hand`

**Verificar primero**:
```sql
\d stock_items  -- ¿columna se llama 'qty' o 'qty_on_hand'?
```

**Opción A** (si BD tiene `qty`):
```python
class StockItem(Base):
    qty: Mapped[float] = mapped_column("qty", Numeric(14,3), default=0)

    # Alias legacy
    @property
    def qty_on_hand(self):
        return self.qty

    @qty_on_hand.setter
    def qty_on_hand(self, value):
        self.qty = value
```

**Opción B** (si BD tiene `qty_on_hand`):
```python
# Mantener el mapeo actual y corregir SQL queries para usar qty_on_hand
```

---

## Fase 2: SQL Queries (CRÍTICO) ⏱️ 1h

### 2.1 POS Module - stock_items queries
**Archivo**: `apps/backend/app/modules/pos/interface/http/tenant.py`

**Línea 752**:
```python
# ANTES:
"SELECT id, qty_on_hand FROM stock_items WHERE ..."

# DESPUÉS:
"SELECT id, qty FROM stock_items WHERE ..."
```

**Línea 764**:
```python
# ANTES:
"INSERT INTO stock_items(id, tenant_id, warehouse_id, product_id, qty_on_hand) VALUES ..."

# DESPUÉS:
"INSERT INTO stock_items(id, tenant_id, warehouse_id, product_id, qty) VALUES ..."
```

**Línea 788**:
```python
# ANTES:
"UPDATE stock_items SET qty_on_hand = :q WHERE ..."

# DESPUÉS:
"UPDATE stock_items SET qty = :q WHERE ..."
```

### 2.2 Scripts - tenant queries
**Archivo**: `scripts/create_default_series.py` (Línea 28)
```python
# ANTES:
"SELECT id, name FROM tenants ORDER BY created_at"

# DESPUÉS:
"SELECT id, nombre FROM tenants ORDER BY created_at"
```

**Archivo**: `scripts/init_pos_demo.py` (Línea 29)
```python
# ANTES:
tenant_query = text("SELECT id, name FROM tenants LIMIT 1")

# DESPUÉS:
tenant_query = text("SELECT id, nombre FROM tenants LIMIT 1")
```

**Archivo**: `scripts/test_settings.py`
```python
# ANTES:
from app.models.empresa.tenant import Tenant
print(tenant.name)
print(tenant.country)

# DESPUÉS:
from app.models.tenant import Tenant  # Ruta correcta
print(tenant.nombre)
print(tenant.country_code)
```

---

## Fase 3: Frontend Inventario ⏱️ 1-3h

### 3.1 Tipos TypeScript
**Archivo**: `apps/tenant/src/modules/inventario/services.ts`

**Líneas 26-32**:
```typescript
// ANTES:
product?: {
    codigo: string
    nombre: string
    precio: number
    stock_minimo?: number
    stock_maximo?: number
}

// DESPUÉS:
product?: {
    codigo: string  // Backend lo mapea desde 'sku'
    nombre: string  // Backend lo mapea desde 'name'
    precio: number  // Backend lo mapea desde 'price'
    product_metadata?: {
        reorder_point?: number
        max_stock?: number
    }
    // DEPRECATED: mantener por compatibilidad temporal
    stock_minimo?: number
    stock_maximo?: number
}
```

### 3.2 StockList Component
**Archivo**: `apps/tenant/src/modules/inventario/StockList.tsx`

**KPIs (Líneas 222-231)** ✅ YA CORREGIDO PARCIALMENTE:
```typescript
// Usar metadata como fuente primaria:
{items.filter(i => {
  const reorderPoint = i.product?.product_metadata?.reorder_point || i.product?.stock_minimo
  return reorderPoint && i.qty < reorderPoint
}).length}
```

**Función getAlertaInfo (Líneas 151-162)**:
```typescript
// ANTES:
const min = item.product?.stock_minimo
const max = item.product?.stock_maximo

// DESPUÉS:
const min = item.product?.product_metadata?.reorder_point || item.product?.stock_minimo
const max = item.product?.product_metadata?.max_stock || item.product?.stock_maximo
```

**Filtrado (Líneas 92-99)**:
```typescript
// ANTES:
if (filterAlerta === 'bajo') {
  const min = item.product?.stock_minimo
  if (!min || item.qty >= min) return false
}

// DESPUÉS:
if (filterAlerta === 'bajo') {
  const min = item.product?.product_metadata?.reorder_point || item.product?.stock_minimo
  if (!min || item.qty >= min) return false
}
```

### 3.3 StockListFixed Component
**Archivo**: `apps/tenant/src/modules/inventario/StockListFixed.tsx`

**Aplicar los mismos cambios que en StockList.tsx**

---

## Fase 4: Docs & Tests ⏱️ <1h

### 4.1 Documentación
**Archivo**: `SETUP_AND_TEST.md` (Línea 325)
```sql
-- ANTES:
SELECT nombre FROM products WHERE id = ...

-- DESPUÉS:
SELECT name FROM products WHERE id = ...
```

### 4.2 Tests
**Comando para encontrar referencias**:
```bash
# Buscar usos legacy en tests
grep -r "stock_minimo" apps/backend/app/tests/
grep -r "stock_maximo" apps/backend/app/tests/
grep -r "\.nombre" apps/backend/app/tests/ | grep -i product
grep -r "qty_on_hand" apps/backend/app/tests/
```

---

## Orden de Implementación Recomendado

### Día 1 - Backend Core (Sin Romper) ⏱️ 2-3h
1. ✅ **Product model alias** - HECHO
2. 📝 **Tenant model alias** - 20 min
3. 📝 **StockItem verificación+ajuste** - 30 min
4. 📝 **SQL queries POS** - 30 min
5. 📝 **Scripts tenant queries** - 15 min
6. ✅ **Reiniciar backend y probar** - 10 min

### Día 2 - Frontend (Mejorar UX) ⏱️ 2-3h
7. 📝 **services.ts tipos** - 20 min
8. 📝 **StockList.tsx completo** - 60 min
9. 📝 **StockListFixed.tsx** - 30 min
10. ✅ **Rebuild frontend y probar** - 15 min

### Día 3 - Limpieza Final ⏱️ 1h
11. 📝 **Docs actualizar** - 15 min
12. 📝 **Tests verificar/corregir** - 30 min
13. ✅ **Smoke test completo** - 15 min

---

## Comandos de Verificación

### Backend
```bash
# Reiniciar backend
docker restart backend

# Ver logs
docker logs -f backend

# Probar endpoint
curl http://localhost:8082/api/v1/inventory/stock
```

### Frontend
```bash
# Rebuild (si es necesario)
cd apps/tenant
npm run build

# Verificar en navegador
# http://localhost:8081/inventory
```

### Base de Datos
```bash
# Verificar esquema stock_items
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d stock_items"

# Verificar metadata de productos
docker exec db psql -U postgres -d gestiqclouddb_dev -c "SELECT name, product_metadata FROM products LIMIT 3;"
```

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Alias ORM no funciona con filtros SQL | Baja | Medio | Usar siempre nombres modernos en queries SQL |
| Frontend rompe con datos legacy | Media | Alto | Mantener fallback temporal `field_new || field_old` |
| Tests fallan por nombres antiguos | Media | Bajo | Ejecutar suite completa antes de commit |
| Scripts externos usan campos legacy | Baja | Bajo | Documentar cambios en CHANGELOG |

---

## Criterios de Éxito

- [ ] Backend se inicia sin errores
- [ ] POS checkout funciona correctamente
- [ ] Impresión de tickets funciona
- [ ] Dashboard inventario muestra alertas correctamente
- [ ] No hay errores "column does not exist" en logs
- [ ] Tests pasan (al menos los críticos)

---

## Siguiente Paso Inmediato

**EJECUTAR AHORA**:

```bash
# 1. Verificar si stock_items tiene 'qty' o 'qty_on_hand'
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d stock_items"

# 2. Según resultado, decidir Opción A o B para StockItem model
```

**Luego implementar Fase 2.1** (SQL queries POS) siguiendo la tabla de cambios.

---

## Notas Técnicas

### ¿Por qué Synonym?
- `synonym` permite que código legacy como `product.nombre` siga funcionando
- NO funciona en queries SQL (`Product.nombre == "test"` falla)
- Solo para acceso directo a atributos del objeto

### ¿Por qué Properties?
- `@property` para campos que necesitan transformación (metadata → stock_minimo)
- Permite lectura/escritura con lógica custom
- Perfecto para migrar datos de estructura plana → JSONB

### Compatibilidad Temporal
- Los fallbacks `field_new || field_old` deben eliminarse en **Sprint +2**
- Documentar en código con `# TODO: Remove legacy fallback after 2025-12-01`

---

## Referencias
- Oracle Analysis: Thread context
- Schema moderno: `ops/migrations/2025-10-27_208_products_modernize_schema/`
- Modelo actual: `apps/backend/app/models/core/products.py`
