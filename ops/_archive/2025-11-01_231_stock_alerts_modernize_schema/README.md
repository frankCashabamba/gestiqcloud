# 2025-11-01_231_stock_alerts_modernize_schema

Moderniza la tabla `stock_alerts` al esquema actual (EN) y actualiza la función `check_low_stock()`.

Cambios clave:
- Añade columnas modernas: `alert_type`, `threshold_config`, `current_qty`, `threshold_qty`, `status`.
- Migra datos desde columnas legacy si existen: `nivel_actual`, `nivel_minimo`, `estado`.
- Elimina columnas legacy: `nivel_actual`, `nivel_minimo`, `estado`, `diferencia`.
- Reemplaza `check_low_stock()` para insertar usando las columnas modernas.
- Crea índices en `(tenant_id, status)` y `product_id`.

