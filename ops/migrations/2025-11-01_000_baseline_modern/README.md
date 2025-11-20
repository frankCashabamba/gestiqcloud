# Migración Baseline Moderna - v2.0

**Fecha**: 2025-11-01
**Versión**: 2.0.0
**Tipo**: Baseline consolidada

## Descripción

Esta es la **migración baseline consolidada** que crea el esquema completo moderno de GestiQCloud desde cero.

Reemplaza todas las migraciones incrementales anteriores con una única migración que establece el estado actual del sistema.

## Características

- ✅ Schema 100% en inglés
- ✅ Nomenclatura moderna consistente
- ✅ RLS (Row Level Security) habilitado
- ✅ UUIDs como primary keys
- ✅ Sin campos legacy
- ✅ Función `check_low_stock()` actualizada

## Tablas Creadas

### Core
- `tenants` - Configuración multi-tenant
- `product_categories` - Categorías de productos

### Catalog
- `products` - Catálogo de productos

### Inventory
- `warehouses` - Almacenes
- `stock_items` - Items de stock
- `stock_moves` - Movimientos de stock
- `stock_alerts` - Alertas de stock

### POS
- `pos_registers` - Registradoras/Cajas
- `pos_shifts` - Turnos
- `pos_receipts` - Recibos/Tickets
- `pos_receipt_lines` - Líneas de recibo
- `pos_payments` - Pagos

## Prerequisitos

Esta migración asume que existen previamente:
- `auth_user` - Usuarios del sistema
- `modulos_modulo` - Módulos disponibles
- `modulos_empresamodulo` - Módulos por empresa
- `modulos_moduloasignado` - Asignación de módulos
- `schema_migrations` - Historial de migraciones

## Aplicar Migración

```bash
# Aplicar up
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-01_000_baseline_modern/up.sql

# Verificar
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

## Rollback

⚠️ **ADVERTENCIA**: El rollback eliminará TODAS las tablas creadas.

```bash
# Rollback (elimina todo excepto auth_user y modulos_*)
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/2025-11-01_000_baseline_modern/down.sql
```

## Cambios vs Legacy

### Nomenclatura

| Legacy (Español) | Moderno (Inglés) |
|------------------|------------------|
| `nombre` | `name` |
| `codigo` | `sku` |
| `precio` | `price` |
| `precio_compra` | `cost_price` |
| `descripcion` | `description` |
| `activo` | `active` |
| `qty_on_hand` | `qty` |
| `ubicacion` | `location` |
| `lote` | `lot` |

### Metadata

- `stock_minimo` → `product_metadata->>'reorder_point'`
- `stock_maximo` → `product_metadata->>'max_stock'`

## Historial

Esta baseline consolida 38+ migraciones incrementales previas:
- 2025-10-26_000 hasta 2025-11-01_250

Ver `/ops/migrations/_archive/` para migraciones históricas.

## Próximas Migraciones

Nuevas migraciones deben numerarse desde:
- `2025-11-01_001_*` en adelante

Y seguir el patrón:
```
ops/migrations/YYYY-MM-DD_NNN_description/
├── up.sql
├── down.sql
└── README.md
```

---

**Estado**: ✅ Activa
**Compatible con**: Backend v2.0, Frontend v2.0
**Aplicada en**: Desarrollo Local, Staging (pendiente), Producción (pendiente)
