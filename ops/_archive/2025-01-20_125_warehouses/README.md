# Migración: Warehouses (Almacenes)

## Descripción

Crea la tabla `warehouses` para soporte multi-almacén necesaria para el sistema POS y gestión de inventario.

## Tabla Creada

### warehouses

Almacenes o ubicaciones físicas de stock.

**Campos**:
- `id` (UUID): Primary key
- `tenant_id` (UUID): Foreign key a tenants
- `code` (TEXT): Código único por tenant (ej: ALM-001, CENTRAL)
- `name` (TEXT): Nombre descriptivo
- `address`, `city`, `country`: Ubicación física
- `is_default` (BOOLEAN): Almacén por defecto para POS
- `active` (BOOLEAN): Estado activo/inactivo
- `capacity_m3`: Capacidad en metros cúbicos (opcional)

## Constraint Único

`uq_warehouse_code_tenant` asegura que cada tenant tenga códigos únicos de almacén.

## RLS

Habilitado con política de aislamiento por `tenant_id`.

## Post-Migración

Después de aplicar esta migración, ejecutar:

```bash
python scripts/create_default_warehouses.py
```

O insertar manualmente almacenes por defecto:

```sql
INSERT INTO warehouses (tenant_id, code, name, is_default, active, country)
SELECT id, 'PRINCIPAL', 'Almacén Principal', TRUE, TRUE, country
FROM tenants
WHERE NOT EXISTS (SELECT 1 FROM warehouses w WHERE w.tenant_id = tenants.id);
```

## Dependencias

- Requiere tabla `tenants` existente
- Requerido por: `stock_alerts`, `stock_items`, `stock_moves`
