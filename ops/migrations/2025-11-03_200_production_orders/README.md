# Migration: Production Orders

**Fecha:** 2025-11-03  
**Versión:** 200  
**Autor:** GestiQCloud Team

## Descripción

Sistema completo de órdenes de producción con:
- Planificación basada en recetas
- Consumo automático de ingredientes (stock)
- Generación de productos terminados
- Registro de mermas y desperdicios
- Trazabilidad con lotes

## Tablas Creadas

### `production_orders`
Órden de producción principal con estados, cantidades y auditoría completa.

**Campos clave:**
- `numero`: Numeración secuencial (OP-YYYY-NNNN)
- `recipe_id`: Receta base
- `qty_planned` / `qty_produced`: Cantidades
- `waste_qty`: Mermas registradas
- `batch_number`: Lote generado (LOT-YYYYMM-NNNN)
- `status`: DRAFT → SCHEDULED → IN_PROGRESS → COMPLETED

### `production_order_lines`
Ingredientes consumidos en la orden.

**Relación:**
- 1 order → N lines
- Cada línea → 1 stock_move (consumo)

## Estados del Flujo

```
DRAFT → SCHEDULED → IN_PROGRESS → COMPLETED
  ↓                      ↓
CANCELLED ←─────────────┘
```

## Constraints y Validaciones

1. **Cantidades positivas**: qty_planned > 0
2. **Fechas coherentes**: completed_at >= started_at
3. **Estado completo**: Si COMPLETED, debe tener started_at y completed_at
4. **Consumo máximo**: qty_consumed ≤ qty_required * 1.2 (20% tolerancia)

## Índices

- `idx_production_orders_tenant` - Filtro por tenant (RLS)
- `idx_production_orders_status` - Filtro por estado
- `idx_production_orders_recipe` - Consultas por receta
- `idx_production_orders_created` - Ordenamiento por fecha DESC

## RLS (Row Level Security)

✅ Ambas tablas protegidas por tenant_id  
✅ Políticas de lectura/escritura por tenant  
✅ Líneas heredan seguridad de orden padre

## Testing

```sql
-- Verificar tablas creadas
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'production_%';

-- Verificar tipo ENUM
SELECT enumlabel FROM pg_enum 
WHERE enumtypid = 'production_order_status'::regtype;

-- Verificar RLS
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename LIKE 'production_%';
```

## Rollback

Para revertir esta migración:

```bash
psql -U postgres -d gestiqclouddb_dev -f down.sql
```

## Notas

- Compatible con sectores: Panadería, Restaurante
- Integra automáticamente con `stock_moves` y `stock_items`
- Genera numeración secuencial automática
- Soporta múltiples almacenes via `warehouse_id`
