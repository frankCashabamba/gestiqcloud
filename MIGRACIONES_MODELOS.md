# Mapeo de Migraciones por Modelos de BD

## 📊 Estructura de Migraciones (ops/migrations)

Las migraciones están organizadas por **dominio de negocio** con tablas completas (sin cambios de campos sueltos).

### Migración Baseline (Estado Inicial)
**`2025-11-01_000_baseline_modern`** ✅ ACTIVA
- **Core**: `tenants`, `product_categories`
- **Catalog**: `products`
- **Inventory**: `warehouses`, `stock_items`, `stock_moves`, `stock_alerts`
- **POS**: `pos_registers`, `pos_shifts`, `pos_receipts`, `pos_receipt_lines`, `pos_payments`

---

## 🗂️ Migraciones por Dominio

### 1. **Auth & Security**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-01_100_auth_tables` | Tablas de autenticación | ✅ |
| `2025-11-01_160_create_usuarios_usuarioempresa` | `usuarios`, `usuario_empresa` | ✅ |

### 2. **Core & Configuration**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-01_110_core_business_tables` | Core business entities | ✅ |
| `2025-11-01_120_config_tables` | Configuraciones | ✅ |
| `2025-11-01_170_reference_tables` | Tablas de referencia | ✅ |
| `2025-11-01_170_tenant_field_config` | Configuración de campos por tenant | ✅ |

### 3. **Catalogs**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-01_001_catalog_tables` | `modulos` (catálogos) | ✅ |
| `2025-11-01_171_ref_timezones_locales` | `timezones`, `locales` | ✅ |
| `2025-11-01_172_core_moneda_catalog` | `monedas` | ✅ |
| `2025-11-01_173_core_country_catalog` | `countries` | ✅ |
| `2025-11-04_240_ui_templates_catalog` | `ui_templates` | ✅ |

### 4. **POS & Sales**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-01_130_pos_extensions` | Extensiones POS | ✅ |
| `2025-11-06_500_pos_daily_counts` | `pos_daily_counts` | ✅ |
| `2025-11-19_901_pos_items_table` | `pos_items` | ✅ |
| `2025-11-19_902_pos_receipts_totals` | Totales en `pos_receipts` | ✅ |
| `2025-11-18_310_sales_system` | `sales`, `sales_items` | ✅ |

### 5. **Inventory & Stock**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-05_fix_negative_stock_alerts` | `stock_alerts` (fix) | ✅ |
| `2025-11-06_500_inventory_alerts` | `inventory_alerts` | ✅ |
| `2025-11-19_905_add_stock_moves_tentative` | `stock_moves.tentative` | ✅ |

### 6. **Procurement & Suppliers**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-18_300_suppliers_system` | `suppliers`, `supplier_contacts` | ✅ |
| `2025-11-18_320_purchases_system` | `purchases`, `purchase_items` | ✅ |

### 7. **Expenses**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-18_330_expenses_system` | `expenses`, `expense_items` | ✅ |

### 8. **E-Invoicing & Integration**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-01_140_einvoicing_tables` | Tablas de facturación electrónica | ✅ |
| `2025-11-01_150_modulos_to_english` | Renombrado módulos a inglés | ✅ |
| `2025-11-17_001_spanish_to_english_names` | Renombrado campos a inglés | ✅ |
| `2025-11-17_800_rolempresas_to_english` | `role_empresas` → inglés | ✅ |

### 9. **AI & Analytics**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-01_150_ai_incident_tables` | `ai_incidents`, tablas IA | ✅ |
| `2025-11-01_165_add_incident_assigned_fk` | FK para asignación incidentes | ✅ |

### 10. **HR & Payroll**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-03_180_hr_empleados` | `empleados`, tablas HR | ✅ |
| `2025-11-03_201_hr_nominas` | `nominas` | ✅ |

### 11. **Production & Manufacturing**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-03_050_create_recipes_tables` | `recipes`, `recipe_items` | ✅ |
| `2025-11-03_200_production_orders` | `production_orders` | ✅ |
| `2025-11-03_200_add_recipe_computed_columns` | Columnas computadas recetas | ✅ |
| `2025-11-03_201_add_unit_conversion` | `unit_conversions` | ✅ |

### 12. **Finance**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-03_202_finance_caja` | `cajas` (caja/efectivo) | ✅ |
| `2025-11-03_203_accounting` | Tablas contables | ✅ |

### 13. **Import & Data Integration**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-02_300_import_batches_system` | `import_batches`, `import_items` | ✅ |
| `2025-11-02_400_import_column_mappings` | `import_column_mappings` | ✅ |
| `2025-11-18_350_import_mappings_corrections` | Correcciones mappings | ✅ |
| `2025-11-19_903_add_parser_fields` | Campos parser importación | ✅ |
| `2025-11-21_010_import_items_idempotency_constraint` | Constraint idempotencia | ✅ |

### 14. **Products & Categories**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-02_231_product_categories_add_metadata` | Metadata categorías | ✅ |
| `2025-11-18_340_business_reference_tables` | Tablas de referencia negocio | ✅ |

### 15. **Missing Tables & Cleanup**
| Migración | Tablas | Estado |
|-----------|--------|--------|
| `2025-11-19_900_missing_tables` | Tablas faltantes | ✅ |

### 16. **Final Consolidation**
| Migración | Cambios | Estado |
|-----------|---------|--------|
| `2025-11-20_000_consolidated_final_schema` | Consolidación final y fixes | ✅ ACTIVA |
| `20250111_001_add_classification_fields` | Campos clasificación | ✅ |

---

## 🎯 Convenciones por Dominio

Cada migración sigue el patrón:
```
YYYY-MM-DD_NNN_description/
├── up.sql     (CREATE TABLE / ALTER TABLE enteras)
├── down.sql   (DROP TABLE / REVERT cambios)
└── README.md  (Documentación)
```

### ✅ **Buenas Prácticas Aplicadas**
- ✅ No hay campos sueltos (rename, add, drop individuales)
- ✅ Las migraciones crean/modifican **tablas completas**
- ✅ Todas tienen `up.sql` y `down.sql`
- ✅ Documentación clara en README.md
- ✅ Transacciones (BEGIN...COMMIT)
- ✅ Nombres 100% inglés desde baseline moderna

---

## 🔄 Dependencias de Migraciones

```
000_baseline_modern (Core: tenants, products, inventory, POS)
  ↓
100_auth_tables
  ↓
110_core_business_tables
  ↓
120_config_tables
  ↓
130_pos_extensions
  ↓
140_einvoicing_tables
  ↓
150_ai_incident_tables
  ↓
160_create_usuarios_usuarioempresa
  ↓
... (resto de migraciones específicas por dominio)
  ↓
2025-11-20_000_consolidated_final_schema (Final)
```

---

## 📝 Tablas Totales Cubiertas

### Modelos Base
- `tenants`, `product_categories`, `products`
- `warehouses`, `stock_items`, `stock_moves`, `stock_alerts`
- `pos_registers`, `pos_shifts`, `pos_receipts`, `pos_receipt_lines`, `pos_payments`

### Extensiones & Dominios
- **Auth**: `usuarios`, `usuario_empresa`, y tablas de autenticación
- **Catalog**: `modulos`, `monedas`, `countries`, `timezones`, `locales`, `ui_templates`
- **Sales**: `sales`, `sales_items`, `clients`
- **Procurement**: `suppliers`, `supplier_contacts`, `purchases`, `purchase_items`
- **Expenses**: `expenses`, `expense_items`
- **HR**: `empleados`, `nominas`
- **Production**: `recipes`, `recipe_items`, `production_orders`, `unit_conversions`
- **Finance**: `cajas`
- **Import**: `import_batches`, `import_items`, `import_column_mappings`
- **Reference**: `business_types`, `business_categories`, `company_categories`, `sector_templates`, `user_profiles`
- **AI**: `ai_incidents`

**Total estimado: 50+ tablas**

---

## ⚠️ PROBLEMA IDENTIFICADO: Cambios de Campos Sueltos

**NO ES PROFESIONAL** el enfoque actual. Hay múltiples migraciones que hacen cambios puntuales:

- ❌ `2025-11-02_231_product_categories_add_metadata`: Solo ADD COLUMN metadata
- ❌ `2025-11-19_905_add_stock_moves_tentative`: Solo ADD COLUMN tentative
- ❌ `2025-11-20_000_consolidated_final_schema`: 8 ALTER TABLE con cambios dispersos

### Problema:
```
business_types
  ├─ Creada en: 2025-11-18_340_business_reference_tables
  ├─ Modificada: 2025-11-20_000 (ADD tenant_id, code, RENAME active→is_active)
  ├─ Modificada: 2025-11-XX (posibles cambios futuros?)
  └─ ❌ La tabla está dispersa en múltiples migraciones
```

### Solución: CONSOLIDAR

**Crear 2-3 migraciones que hagan CREATE/ALTER COMPLETAS**:
- `2025-11-21_000_consolidate_schema_v1` - CREATE todas las tablas CORRECTAS
- `2025-11-21_001_consolidate_schema_v2` - ALTER tables con las columnas FINALES
- `2025-11-21_002_rename_legacy_columns` - Batch rename de campos legacy → moderno
- Luego: ELIMINAR todas las migraciones pequeñas anteriores (archivadas en `_archive/`)

---

## 🚀 Aplicar Nueva Migración

Si necesitas agregar una tabla completa nueva:

```bash
# 1. Crear carpeta
mkdir ops/migrations/2025-11-XX_NNN_new_system

# 2. Crear archivos
touch ops/migrations/2025-11-XX_NNN_new_system/{up.sql,down.sql,README.md}

# 3. En up.sql: CREATE TABLE COMPLETA con TODAS las columnas, índices, FKs, constraints
#    NO hacer: ADD COLUMN IF NOT EXISTS para cada campo
#    SÍ hacer: CREATE TABLE con definición completa desde el inicio

# 4. En down.sql: DROP TABLE IF EXISTS
# 5. Documentar en README.md qué tabla/modelo cubre

# 6. Aplicar
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-XX_NNN_new_system/up.sql
```

### ✅ Ejemplo Correcto:
```sql
-- up.sql
BEGIN;

CREATE TABLE IF NOT EXISTS my_new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_my_new_table_tenant ON my_new_table(tenant_id);
CREATE INDEX idx_my_new_table_code ON my_new_table(code);

COMMIT;
```

### ❌ Evitar:
```sql
-- NO hacer esto (spread across migrations)
ALTER TABLE my_table ADD COLUMN name VARCHAR(255);
ALTER TABLE my_table ADD COLUMN code VARCHAR(50);
ALTER TABLE my_table ADD COLUMN is_active BOOLEAN;
```

---

## 🛠️ SOLUCIÓN: Script para Generar Migración Limpia

He creado scripts que **generan una migración profesional** desde los modelos SQLAlchemy:

### Archivos Creados

1. **`scripts/generate_schema_sql.py`** - Script principal
   - Introspecciona todos los modelos
   - Genera `up.sql` y `down.sql`
   - Crea indexes automáticos

2. **`QUICK_START_MIGRATIONS.md`** - Guía rápida
   - Paso a paso para ejecutar script
   - Verificación y troubleshooting

3. **`GENERATE_MIGRATIONS.md`** - Guía detallada
   - Documentación completa
   - Diferentes opciones

### Uso Rápido

```bash
# 1. Desde raíz del proyecto
cd C:\Users\pc_cashabamba\Documents\GitHub\proyecto

# 2. Generar migración
python scripts/generate_schema_sql.py --date 2025-11-21 --number 000

# 3. Aplicar
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-21_000_complete_consolidated_schema/up.sql

# 4. Verificar
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

### Resultado

```
ops/migrations/
└── 2025-11-21_000_complete_consolidated_schema/
    ├── up.sql      ← CREATE todas las tablas
    ├── down.sql    ← DROP todas las tablas
    └── README.md   ← Documentación automática
```

---

**Última actualización**: 2025-11-20
**Baseline actual**: v2.0.0
**ESTADO**: ✅ Solución disponible en `scripts/generate_schema_sql.py`
