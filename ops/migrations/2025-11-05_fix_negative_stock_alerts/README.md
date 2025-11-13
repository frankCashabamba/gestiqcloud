# Migración: Detectar y Alertar Stock Negativo

**Fecha**: 2025-11-05
**Prioridad**: Alta

## Problema

La función `check_low_stock()` solo generaba alertas cuando el stock estaba por debajo del `reorder_point`, pero **NO alertaba cuando el stock era negativo**. Esto causaba que productos con stock negativo (e.g., -5.00) no generaran alertas visibles para los usuarios.

## Solución

Se mejoró la función `check_low_stock()` para:

1. **Detectar stock negativo**: Genera alertas tipo `out_of_stock` cuando `qty < 0`
2. **Priorizar alertas**: Stock negativo se alerta cada 12 horas (más frecuente que low_stock)
3. **Evitar duplicados**: Verifica que no exista alerta activa reciente antes de insertar
4. **Resolver automáticamente**: Marca alertas como resueltas cuando el stock se recupera

## Tipos de alertas

- **`out_of_stock`**: Stock negativo (qty < 0) - Criticidad ALTA
- **`low_stock`**: Stock bajo pero positivo (0 <= qty < reorder_point) - Criticidad MEDIA

## Aplicación

```bash
# Aplicar migración
psql -U user -d database -f ops/migrations/2025-11-05_fix_negative_stock_alerts/up.sql

# Revertir (si necesario)
psql -U user -d database -f ops/migrations/2025-11-05_fix_negative_stock_alerts/down.sql
```

## Validación

Después de aplicar, verifica:

```sql
-- Ver productos con stock negativo y sus alertas
SELECT
  p.code,
  p.name,
  si.qty,
  sa.alert_type,
  sa.status,
  sa.created_at
FROM stock_items si
JOIN products p ON p.id = si.product_id
LEFT JOIN stock_alerts sa ON sa.product_id = si.product_id
  AND sa.warehouse_id = si.warehouse_id
  AND sa.status = 'active'
WHERE si.qty < 0
ORDER BY si.qty ASC;
```

## Notas

- El worker `check_and_notify_low_stock()` ejecuta esta función cada hora vía Celery Beat
- Las alertas se muestran en el módulo de inventario (`/inventario`)
- Los usuarios pueden configurar notificaciones por email/Telegram
