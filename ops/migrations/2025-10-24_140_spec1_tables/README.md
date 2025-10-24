# Migration 2025-10-24_140: SPEC-1 Tables

## Descripción
Implementa todas las tablas faltantes del SPEC-1 (Digitalización de registro de ventas y compras).

## Tablas creadas
1. **uom** - Unidades de medida (KG, L, UN, etc.)
2. **uom_conversion** - Conversiones entre unidades (1 KG = 1000 G)
3. **daily_inventory** - Inventario diario por producto
4. **purchase** - Compras a proveedores
5. **milk_record** - Registro de leche
6. **sale_header/line** - Documentos de venta simplificados
7. **production_order** - Órdenes de producción
8. **import_log** - Trazabilidad de importaciones

## Features
- RLS habilitado en todas las tablas
- Triggers automáticos para cálculos (ajuste, total)
- Seeds UoM básicas incluidas
- Índices optimizados por tenant y fecha

## Relacionado
- SPEC-1: spec_1_digitalizacion_de_registro_de_ventas_y_compras_gestiqcloud.md
- Implementa: líneas 257-343 (tablas), 560-581 (UoM), 569-571 (sale/production)
