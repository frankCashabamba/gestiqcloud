# 📚 Guía: Cómo Crear Migraciones de Base de Datos

**Importante:** No hardcodees valores en las migraciones. Todo debe ser configurable o venir de la base de datos.

---

## ✅ Patrón Correcto (Sin Hardcodeos)

### Estructura de Carpeta

```
ops/migrations/
└── YYYY-MM-DD_NNN_descripcion_migracion/
    ├── up.sql      (Script para aplicar cambios)
    └── down.sql    (Script para revertir cambios)
```

### Ejemplo 1: Agregar Columna (Simple)

**Carpeta:** `2026-01-19_000_add_users_phone_number`

**up.sql:**
```sql
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
```

**down.sql:**
```sql
ALTER TABLE users
  DROP COLUMN IF EXISTS phone_number;
```

---

### Ejemplo 2: Crear Nueva Tabla (SIN Valores Hardcodeados)

**Carpeta:** `2026-01-19_001_create_discount_rules_table`

**up.sql:**
```sql
-- Migration: Create discount_rules table
-- Description: Store dynamic discount rules (no hardcoded defaults)
-- Author: Team

CREATE TABLE IF NOT EXISTS discount_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Rule type (stored as string, configurable)
    rule_type VARCHAR(50) NOT NULL,  -- 'percentage', 'fixed_amount', 'buy_x_get_y'

    -- Values (nullable, depends on rule_type)
    discount_value DECIMAL(10, 2),   -- Either percentage or fixed amount
    min_quantity INTEGER,             -- Minimum quantity to apply discount
    min_amount DECIMAL(10, 2),        -- Minimum purchase amount

    -- Metadata
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_discount_rules_tenant_id ON discount_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_discount_rules_is_active ON discount_rules(is_active);
```

**down.sql:**
```sql
DROP TABLE IF EXISTS discount_rules CASCADE;
```

---

### Ejemplo 3: Alteraciones Complejas

**Carpeta:** `2026-01-19_002_add_audit_columns`

**up.sql:**
```sql
-- Add audit columns to multiple tables
BEGIN;

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_products_deleted_at ON products(deleted_at);
CREATE INDEX IF NOT EXISTS idx_orders_deleted_at ON orders(deleted_at);

COMMIT;
```

**down.sql:**
```sql
BEGIN;

DROP INDEX IF EXISTS idx_products_deleted_at;
DROP INDEX IF EXISTS idx_orders_deleted_at;

ALTER TABLE products
    DROP COLUMN IF EXISTS created_by,
    DROP COLUMN IF EXISTS updated_by,
    DROP COLUMN IF EXISTS deleted_at;

ALTER TABLE orders
    DROP COLUMN IF EXISTS created_by,
    DROP COLUMN IF EXISTS updated_by,
    DROP COLUMN IF EXISTS deleted_at;

COMMIT;
```

---

## ⚠️ ANTI-PATRÓN: Hardcodeos en Migraciones

### ❌ MAL: Insertar Valores Hardcodeados

```sql
-- ❌ INCORRECTO
INSERT INTO status_types (id, code, name)
VALUES
  ('001', 'draft', 'Borrador'),
  ('002', 'pending', 'Pendiente'),
  ('003', 'approved', 'Aprobado');
```

**Problemas:**
- ❌ Valores fijos, imposible cambiar sin modificar código
- ❌ Si necesitas agregar más estados, requiere nueva migración
- ❌ Difícil de mantener en múltiples ambientes

### ✅ BIEN: Usar Configuración de Aplicación

```python
# apps/backend/app/constants/statuses.py
class OrderStatus(str, Enum):
    DRAFT = 'draft'
    PENDING = 'pending'
    APPROVED = 'approved'

# apps/backend/scripts/seed_statuses.py
def seed_order_statuses():
    """Carga estados desde el enum (reutilizable)"""
    for status in OrderStatus:
        StatusType.get_or_create(
            code=status.value,
            defaults={'name': status.value.title()}
        )
```

---

## 📋 Checklist para Crear Migraciones

Antes de crear una migración, responde estas preguntas:

### Configuración de Carpeta
- [ ] Nombre sigue formato: `YYYY-MM-DD_NNN_descripcion`
  - Ejemplo: `2026-01-19_000_create_users_table`
- [ ] Contiene `up.sql` y `down.sql`
- [ ] Ambos archivos tienen comentarios descriptivos

### Contenido de up.sql
- [ ] Usa `IF NOT EXISTS` en CREATE/ALTER
- [ ] Incluye comentarios de descripción
- [ ] Crea índices necesarios
- [ ] Respeta constraints existentes (FK, UNIQUE)
- [ ] ⚠️ NO hardcodea valores (INSERT con valores específicos)
- [ ] Usa `DEFAULT` para valores iniciales seguros
- [ ] Usa `BEGIN/COMMIT` para transacciones complejas

### Contenido de down.sql
- [ ] Es lo opuesto a up.sql
- [ ] Usa `DROP IF EXISTS`
- [ ] Limpia índices también
- [ ] Es seguro ejecutar sin errores

### Si Necesitas Valores Iniciales
- [ ] Crea un script Python reutilizable (en `scripts/` o `app/commands/`)
- [ ] Carga valores desde enum o config
- [ ] Puede ejecutarse múltiples veces sin errores (idempotent)
- [ ] Documentación sobre cómo ejecutar el script

---

## 📁 Estructura de Carpeta Correcta

```
gestiqcloud/
├── ops/migrations/
│   ├── 2026-01-19_000_add_users_phone_number/
│   │   ├── up.sql
│   │   └── down.sql
│   │
│   ├── 2026-01-19_001_create_discount_rules_table/
│   │   ├── up.sql
│   │   └── down.sql
│   │
│   └── 2026-01-19_002_add_audit_columns/
│       ├── up.sql
│       └── down.sql
│
├── apps/backend/app/commands/
│   ├── seed_statuses.py     ← Cargar estados desde enum
│   ├── seed_categories.py   ← Cargar categorías desde config
│   └── seed_countries.py    ← Cargar países desde tabla de referencia
│
└── apps/backend/app/constants/
    ├── statuses.py          ← Enums de estados
    ├── currencies.py        ← Enums de monedas
    └── countries.py         ← Lista de países
```

---

## 🔧 Comandos Útiles

### Ejecutar una migración
```bash
cd apps/backend

# Apply all tracked migrations
python ops/scripts/migrate_all_migrations_idempotent.py

# Apply up to a specific version
# Run the corresponding SQL migration directory manually if needed

# Revert a migration
# Execute the matching down.sql or restore from backup

# View current state
# Inspect the _migrations table
```

### Crear Script de Seed (Reutilizable)

**Ejemplo: `apps/backend/app/commands/seed_reference_data.py`**

```python
"""
Script para cargar datos de referencia.
Reutilizable, puede ejecutarse múltiples veces sin errores.
"""

from app.models import Country, Currency
from app.constants import COUNTRIES, CURRENCIES

def seed_countries():
    """Cargar países desde lista centralizada"""
    for code, name in COUNTRIES.items():
        Country.get_or_create(
            code=code,
            defaults={'name': name}
        )
    print(f"✓ {len(COUNTRIES)} países cargados")

def seed_currencies():
    """Cargar monedas desde enum centralizado"""
    for currency in CURRENCIES:
        Currency.get_or_create(
            code=currency.code,
            defaults={'name': currency.name, 'symbol': currency.symbol}
        )
    print(f"✓ {len(CURRENCIES)} monedas cargadas")

if __name__ == '__main__':
    seed_countries()
    seed_currencies()
    print("✓ Datos de referencia cargados")
```

### Ejecutar seed script
```bash
cd apps/backend
python -m app.commands.seed_reference_data
```

---

## 🚀 Mejores Prácticas

### 1. Usa DEFAULT en lugar de hardcodeos
```sql
-- ✅ BIEN: Default seguro
CREATE TABLE orders (
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ❌ MAL: Hardcodeado
INSERT INTO orders (status, created_at)
VALUES ('draft', NOW());  -- ← Hardcodeado en migración
```

### 2. Centraliza Enums y Constantes
```python
# ✅ BIEN: Centralizado
class OrderStatus(str, Enum):
    DRAFT = 'draft'
    PENDING = 'pending'

# ❌ MAL: Distribuido
# Valores 'draft' y 'pending' en múltiples archivos
```

### 3. Haz Scripts Reutilizables e Idempotentes
```python
# ✅ BIEN: Puede ejecutarse múltiples veces
def seed_categories():
    for name in CATEGORIES:
        Category.get_or_create(name=name)  # ← Solo crea si no existe

# ❌ MAL: Falla si ejecuta 2 veces
INSERT INTO categories (name) VALUES ('Electronics');  # ← Error de PK
```

### 4. Documenta la Migración
```sql
-- Migration: 2026-01-19_001_create_discount_rules
-- Description: New table for dynamic discount management
-- Seed data: Use app.commands.seed_discount_defaults
-- Rollback: Safe, just drops the table
-- Author: Team
-- Date: 2026-01-19
```

---

## 📚 Referencias

**Archivos de migración existentes bien hechos:**
- `ops/migrations/2026-01-18_000_add_clients_is_wholesale/` - Simple column add
- `ops/migrations/2026-01-17_000_printer_label_columns/` - Multiple columns
- `ops/migrations/2026-01-15_000_audit_events/` - Complex table creation

**Evita como modelo:**
- ❌ Migraciones con INSERT VALUES hardcodeados
- ❌ Valores fijos en DEFAULT que deberían ser configurables
- ❌ Migraciones que no pueden revertirse (sin down.sql)

---

**Última actualización:** 15 Enero 2026
**Versión:** 1.0
