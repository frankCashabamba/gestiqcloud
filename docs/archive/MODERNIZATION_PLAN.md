# Plan de Modernización Definitiva - TODO EN INGLÉS

**Fecha**: 2025-11-01
**Objetivo**: Estandarizar TODO el sistema a inglés moderno - SIN ALIAS, SIN LEGACY

## Filosofía

- ✅ **Una sola fuente de verdad**: Campos en inglés
- ✅ **BD → Backend → Frontend**: Todo consistente
- ✅ **i18n después**: Labels traducidos en UI, pero datos en inglés
- ❌ **NO alias**: Sin compatibilidad legacy
- ❌ **NO duplicación**: Eliminar campos antiguos

---

## Esquema Moderno Definitivo

### Products
```sql
-- MODERNO (inglés)
name VARCHAR(255)           -- NO "nombre"
sku VARCHAR(100)            -- NO "codigo"
price NUMERIC(12,2)         -- NO "precio"
cost_price NUMERIC(12,2)    -- "precio_compra" → "cost_price"
description TEXT            -- NO "descripcion"
category VARCHAR(100)       -- OK (ya en inglés)
active BOOLEAN              -- NO "activo"
product_metadata JSONB      -- OK
  ├─ reorder_point: INT     -- NO "stock_minimo"
  └─ max_stock: INT         -- NO "stock_maximo"
```

### Tenants
```sql
-- MODERNO (inglés)
name VARCHAR(100)           -- NO "nombre"
slug VARCHAR(100)           -- OK
tax_id VARCHAR(30)          -- NO "ruc"
phone VARCHAR(20)           -- NO "telefono"
address TEXT                -- NO "direccion"
city VARCHAR(100)           -- NO "ciudad"
state VARCHAR(100)          -- NO "provincia"
postal_code VARCHAR(20)     -- NO "cp"
country_code VARCHAR(2)     -- Renombrar "pais" → "country_code"
website VARCHAR(255)        -- NO "sitio_web"
base_currency VARCHAR(3)    -- OK
primary_color VARCHAR(7)    -- NO "color_primario"
active BOOLEAN              -- NO "activo"
```

### Stock Items
```sql
-- MODERNO (inglés)
qty NUMERIC(14,3)           -- NO "qty_on_hand"
location VARCHAR(50)        -- NO "ubicacion"
lot VARCHAR(100)            -- OK (ya en inglés)
expires_at DATE             -- OK
```

---

## Fase 1: Migraciones SQL ⏱️ 2-3h

### 1.1 Products - Renombrar columnas
**Archivo**: `ops/migrations/2025-11-01_240_products_english_names/up.sql`

```sql
BEGIN;

-- Renombrar columnas español → inglés
ALTER TABLE products RENAME COLUMN descripcion TO description;

-- Nota: name, sku, price ya existen (migración anterior los creó)
-- Si aún existe "nombre", "codigo", "precio" → eliminarlos
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='products' AND column_name='nombre') THEN
        ALTER TABLE products DROP COLUMN nombre;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='products' AND column_name='codigo') THEN
        ALTER TABLE products DROP COLUMN codigo;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='products' AND column_name='precio') THEN
        ALTER TABLE products DROP COLUMN precio;
    END IF;
END $$;

-- Renombrar precio_compra → cost_price
ALTER TABLE products RENAME COLUMN precio_compra TO cost_price;

-- Renombrar activo → active (si no existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='products' AND column_name='activo') THEN
        ALTER TABLE products RENAME COLUMN activo TO active;
    END IF;
END $$;

COMMIT;
```

**Archivo**: `ops/migrations/2025-11-01_240_products_english_names/down.sql`
```sql
BEGIN;

ALTER TABLE products RENAME COLUMN description TO descripcion;
ALTER TABLE products RENAME COLUMN cost_price TO precio_compra;
ALTER TABLE products RENAME COLUMN active TO activo;

COMMIT;
```

### 1.2 Tenants - Renombrar columnas
**Archivo**: `ops/migrations/2025-11-01_241_tenants_english_names/up.sql`

```sql
BEGIN;

-- Renombrar columnas español → inglés
ALTER TABLE tenants RENAME COLUMN nombre TO name;
ALTER TABLE tenants RENAME COLUMN ruc TO tax_id;
ALTER TABLE tenants RENAME COLUMN telefono TO phone;
ALTER TABLE tenants RENAME COLUMN direccion TO address;
ALTER TABLE tenants RENAME COLUMN ciudad TO city;
ALTER TABLE tenants RENAME COLUMN provincia TO state;
ALTER TABLE tenants RENAME COLUMN cp TO postal_code;
ALTER TABLE tenants RENAME COLUMN pais TO country;
ALTER TABLE tenants RENAME COLUMN sitio_web TO website;
ALTER TABLE tenants RENAME COLUMN color_primario TO primary_color;
ALTER TABLE tenants RENAME COLUMN activo TO active;
ALTER TABLE tenants RENAME COLUMN motivo_desactivacion TO deactivation_reason;

COMMIT;
```

**Archivo**: `ops/migrations/2025-11-01_241_tenants_english_names/down.sql`
```sql
BEGIN;

ALTER TABLE tenants RENAME COLUMN name TO nombre;
ALTER TABLE tenants RENAME COLUMN tax_id TO ruc;
ALTER TABLE tenants RENAME COLUMN phone TO telefono;
ALTER TABLE tenants RENAME COLUMN address TO direccion;
ALTER TABLE tenants RENAME COLUMN city TO ciudad;
ALTER TABLE tenants RENAME COLUMN state TO provincia;
ALTER TABLE tenants RENAME COLUMN postal_code TO cp;
ALTER TABLE tenants RENAME COLUMN country TO pais;
ALTER TABLE tenants RENAME COLUMN website TO sitio_web;
ALTER TABLE tenants RENAME COLUMN primary_color TO color_primario;
ALTER TABLE tenants RENAME COLUMN active TO activo;
ALTER TABLE tenants RENAME COLUMN deactivation_reason TO motivo_desactivacion;

COMMIT;
```

### 1.3 Stock Items - Renombrar qty_on_hand → qty
**Archivo**: `ops/migrations/2025-11-01_242_stock_items_qty/up.sql`

```sql
BEGIN;

-- Renombrar qty_on_hand → qty
ALTER TABLE stock_items RENAME COLUMN qty_on_hand TO qty;

-- Renombrar ubicacion → location (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='stock_items' AND column_name='ubicacion') THEN
        ALTER TABLE stock_items RENAME COLUMN ubicacion TO location;
    END IF;
END $$;

COMMIT;
```

---

## Fase 2: Backend Models ⏱️ 1-2h

### 2.1 Product Model
**Archivo**: `apps/backend/app/models/core/products.py`

```python
class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)

    # Campos en INGLÉS
    sku: Mapped[str | None] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), default=21.00)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    stock: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(Text, default="unit")  # "unidad" → "unit"
    product_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # ELIMINAR: nombre, codigo, precio, precio_compra, descripcion, activo
```

### 2.2 Tenant Model
**Archivo**: `apps/backend/app/models/tenant.py`

```python
class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)

    # Campos en INGLÉS
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(100), unique=True)
    tax_id: Mapped[str | None] = mapped_column(String(30))
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(2), default='ES')
    website: Mapped[str | None] = mapped_column(String(255))
    base_currency: Mapped[str] = mapped_column(String(3), default='EUR')
    logo: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(String(7), default='#4f46e5')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    deactivation_reason: Mapped[str | None] = mapped_column(String(255))

    # ELIMINAR: nombre, ruc, telefono, direccion, ciudad, provincia, cp, pais, etc.
```

### 2.3 StockItem Model
**Archivo**: `apps/backend/app/models/inventory/stock.py`

```python
class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))

    # Campo en INGLÉS
    qty: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    location: Mapped[str | None] = mapped_column(String(50))
    lot: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[date | None] = mapped_column(Date)

    # ELIMINAR: qty_on_hand, ubicacion
```

---

## Fase 3: Backend Schemas (Pydantic) ⏱️ 1-2h

### 3.1 Product Schemas
**Archivo**: `apps/backend/app/schemas/products.py`

```python
class ProductBase(BaseModel):
    sku: str | None = None
    name: str
    description: str | None = None
    price: float | None = None
    cost_price: float | None = None
    tax_rate: float = 21.0
    category: str | None = None
    active: bool = True
    unit: str = "unit"
    product_metadata: dict | None = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    cost_price: float | None = None
    # ... etc
```

### 3.2 Tenant Schemas
**Archivo**: `apps/backend/app/schemas/tenants.py`

```python
class TenantBase(BaseModel):
    name: str
    slug: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    country_code: str = 'ES'
    # ... etc
```

---

## Fase 4: Backend Routers/Services ⏱️ 2-3h

### Archivos a modificar

**Buscar y reemplazar en TODOS los routers**:
```python
# ANTES → DESPUÉS
product.nombre → product.name
product.codigo → product.sku
product.precio → product.price
product.precio_compra → product.cost_price
product.descripcion → product.description
product.activo → product.active

tenant.nombre → tenant.name
tenant.ruc → tenant.tax_id
tenant.telefono → tenant.phone
# ... etc

stock_item.qty_on_hand → stock_item.qty
stock_item.ubicacion → stock_item.location
```

**Archivos principales**:
- `apps/backend/app/routers/products.py`
- `apps/backend/app/routers/tenants.py`
- `apps/backend/app/modules/productos/**/*.py`
- `apps/backend/app/modules/pos/**/*.py`
- `apps/backend/app/modules/copilot/**/*.py`

**SQL crudo** - Actualizar:
```python
# ANTES:
"SELECT nombre, precio FROM products WHERE ..."

# DESPUÉS:
"SELECT name, price FROM products WHERE ..."
```

---

## Fase 5: Frontend ⏱️ 2-4h

### 5.1 TypeScript Types
**Archivo**: `apps/tenant/src/modules/inventario/services.ts`

```typescript
export type Product = {
  id: string
  sku: string | null
  name: string
  description: string | null
  price: number | null
  cost_price: number | null
  tax_rate: number
  category: string | null
  active: boolean
  unit: string
  product_metadata: {
    reorder_point?: number
    max_stock?: number
  } | null
}

export type StockItem = {
  id: string
  product_id: string
  warehouse_id: string
  qty: number  // NO qty_on_hand
  location: string | null
  lot: string | null
  expires_at: string | null
  product?: Product
  warehouse?: {
    code: string
    name: string
  }
}
```

### 5.2 Componentes React
**Buscar y reemplazar globalmente**:
```typescript
// ANTES → DESPUÉS
item.product?.nombre → item.product?.name
item.product?.codigo → item.product?.sku
item.product?.precio → item.product?.price
item.product?.stock_minimo → item.product?.product_metadata?.reorder_point
item.product?.stock_maximo → item.product?.product_metadata?.max_stock

item.qty_on_hand → item.qty
item.ubicacion → item.location
```

**Archivos principales**:
- `apps/tenant/src/modules/inventario/StockList.tsx`
- `apps/tenant/src/modules/inventario/StockListFixed.tsx`
- `apps/tenant/src/modules/productos/**/*.tsx`
- `apps/admin/src/**/*.tsx`

### 5.3 Labels UI (i18n después)
```typescript
// Mantener labels en español para usuarios, pero datos en inglés
<label>Nombre del producto</label>  // UI
<input value={product.name} />       // Dato en inglés

// Después implementar i18n:
<label>{t('product.name')}</label>   // 'Nombre del producto' (ES) / 'Product Name' (EN)
<input value={product.name} />       // Siempre en inglés en BD
```

---

## Fase 6: Scripts y Tests ⏱️ 1-2h

### 6.1 Scripts
**Archivos**:
- `scripts/create_default_series.py`
- `scripts/init_pos_demo.py`
- `scripts/test_settings.py`

```python
# ANTES:
tenant.nombre, tenant.ruc

# DESPUÉS:
tenant.name, tenant.tax_id
```

### 6.2 Tests
**Buscar globalmente**:
```bash
grep -r "\.nombre" apps/backend/app/tests/ | grep -i product
grep -r "qty_on_hand" apps/backend/app/tests/
grep -r "stock_minimo" apps/backend/app/tests/
```

---

## Orden de Ejecución (TODO DE UNA VEZ)

### Día 1 - Base de Datos ⏱️ 2-3h
1. ✅ Crear 3 migraciones (products, tenants, stock_items)
2. ✅ Aplicar migraciones
3. ✅ Verificar esquema resultante

### Día 2 - Backend ⏱️ 4-6h
4. ✅ Actualizar Models (products, tenants, stock)
5. ✅ Actualizar Schemas (Pydantic)
6. ✅ Actualizar Routers (buscar/reemplazar global)
7. ✅ Actualizar SQL crudo
8. ✅ Actualizar Scripts
9. ✅ Reiniciar backend y probar endpoints

### Día 3 - Frontend ⏱️ 4-6h
10. ✅ Actualizar Types TypeScript
11. ✅ Actualizar Servicios
12. ✅ Actualizar Componentes React (buscar/reemplazar)
13. ✅ Rebuild frontend y probar UI

### Día 4 - Tests y Limpieza ⏱️ 2-3h
14. ✅ Actualizar Tests
15. ✅ Smoke test completo
16. ✅ Documentar en CHANGELOG

---

## Script de Búsqueda/Reemplazo

### Backend (Python)
```bash
# Buscar usos legacy
cd apps/backend
grep -r "\.nombre" . --include="*.py" | grep -v "__pycache__"
grep -r "\.codigo" . --include="*.py" | grep -v "__pycache__"
grep -r "\.precio\"" . --include="*.py" | grep -v "__pycache__"
grep -r "qty_on_hand" . --include="*.py"
grep -r "stock_minimo" . --include="*.py"

# Contar ocurrencias
grep -r "\.nombre" . --include="*.py" | wc -l
```

### Frontend (TypeScript)
```bash
# Buscar usos legacy
cd apps/tenant
grep -r "\.nombre" . --include="*.ts" --include="*.tsx"
grep -r "qty_on_hand" . --include="*.ts" --include="*.tsx"
grep -r "stock_minimo" . --include="*.ts" --include="*.tsx"
```

---

## Comandos de Verificación

### Antes de empezar
```bash
# Backup de BD
docker exec db pg_dump -U postgres gestiqclouddb_dev > backup_before_english.sql

# Backup de código
git add -A
git commit -m "checkpoint: before english modernization"
git branch backup-before-english
```

### Durante migración
```bash
# Verificar columnas products
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d products"

# Verificar columnas tenants
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d tenants"

# Verificar columnas stock_items
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\d stock_items"
```

### Después de completar
```bash
# Probar endpoints críticos
curl http://localhost:8082/api/v1/products
curl http://localhost:8082/api/v1/inventory/stock
curl http://localhost:8082/api/v1/tenants/me

# Ver logs
docker logs -f backend | grep -i error
```

---

## Rollback Plan

Si algo falla:
```bash
# 1. Rollback BD
docker exec -i db psql -U postgres gestiqclouddb_dev < backup_before_english.sql

# 2. Rollback código
git reset --hard backup-before-english

# 3. Reiniciar
docker compose down
docker compose up -d
```

---

## Criterios de Éxito

- [ ] BD: Solo campos en inglés (name, sku, price, qty, etc.)
- [ ] Backend Models: Sin campos español
- [ ] Backend Schemas: Sin campos español
- [ ] Frontend Types: Sin campos español
- [ ] UI: Labels en español, datos en inglés
- [ ] Tests: Todos pasan
- [ ] No errores "column does not exist"
- [ ] POS funciona (checkout, impresión)
- [ ] Dashboard inventario funciona

---

## Siguiente Paso INMEDIATO

**EJECUTAR**:
```bash
# 1. Crear branch de trabajo
git checkout -b feature/english-modernization

# 2. Backup BD
docker exec db pg_dump -U postgres gestiqclouddb_dev > backup_before_english_$(date +%Y%m%d).sql

# 3. Crear primera migración
mkdir -p ops/migrations/2025-11-01_240_products_english_names
```

¿Quieres que empiece creando las 3 migraciones SQL?
