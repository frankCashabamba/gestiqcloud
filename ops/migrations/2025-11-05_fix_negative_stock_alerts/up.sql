-- Mejora de check_low_stock() para detectar stock negativo
-- Fecha: 2025-11-05
-- Descripción: Agrega alertas de stock negativo

BEGIN;

CREATE OR REPLACE FUNCTION check_low_stock()
RETURNS void AS $$
BEGIN
  -- 1. Alertas de STOCK NEGATIVO (prioridad alta)
  INSERT INTO stock_alerts (
    tenant_id, product_id, warehouse_id,
    alert_type, current_qty, threshold_qty, status
  )
  SELECT DISTINCT ON (si.tenant_id, si.product_id, si.warehouse_id)
    si.tenant_id,
    si.product_id,
    si.warehouse_id,
    'out_of_stock',  -- Usamos out_of_stock para stock negativo
    COALESCE(si.qty, 0)::INTEGER,
    0 AS threshold_qty,
    'active'
  FROM stock_items si
  WHERE
    COALESCE(si.qty, 0) < 0  -- Stock negativo
    AND NOT EXISTS (
      SELECT 1 FROM stock_alerts sa
      WHERE sa.tenant_id = si.tenant_id
        AND sa.product_id = si.product_id
        AND sa.warehouse_id = si.warehouse_id
        AND sa.alert_type = 'out_of_stock'
        AND sa.status IN ('active', 'acknowledged')
        AND sa.created_at > NOW() - INTERVAL '12 hours'  -- Alertar cada 12h si sigue negativo
    );

  -- 2. Alertas de STOCK BAJO (cuando está por debajo del reorder point pero no negativo)
  INSERT INTO stock_alerts (
    tenant_id, product_id, warehouse_id,
    alert_type, current_qty, threshold_qty, status
  )
  SELECT DISTINCT ON (si.tenant_id, si.product_id, si.warehouse_id)
    si.tenant_id,
    si.product_id,
    si.warehouse_id,
    'low_stock',
    COALESCE(si.qty, 0)::INTEGER,
    COALESCE((p.product_metadata->>'reorder_point')::integer, 0) AS threshold_qty,
    'active'
  FROM stock_items si
  JOIN products p ON p.id = si.product_id
  WHERE
    COALESCE((p.product_metadata->>'reorder_point')::numeric, 0) > 0
    AND COALESCE(si.qty, 0) >= 0  -- No negativo
    AND COALESCE(si.qty, 0) < COALESCE((p.product_metadata->>'reorder_point')::numeric, 0)
    AND NOT EXISTS (
      SELECT 1 FROM stock_alerts sa
      WHERE sa.tenant_id = si.tenant_id
        AND sa.product_id = si.product_id
        AND sa.warehouse_id = si.warehouse_id
        AND sa.alert_type = 'low_stock'
        AND sa.status IN ('active', 'acknowledged')
        AND sa.created_at > NOW() - INTERVAL '24 hours'
    );

  -- 3. Resolver alertas cuando el stock se recupera
  -- Resolver alertas de stock negativo cuando qty >= 0
  UPDATE stock_alerts sa
  SET status = 'resolved', resolved_at = NOW()
  WHERE sa.alert_type = 'out_of_stock'
    AND sa.status IN ('active', 'acknowledged')
    AND EXISTS (
      SELECT 1 FROM stock_items si
      WHERE si.product_id = sa.product_id
        AND si.warehouse_id = sa.warehouse_id
        AND COALESCE(si.qty, 0) >= 0
    );

  -- Resolver alertas de low_stock cuando qty >= reorder_point
  UPDATE stock_alerts sa
  SET status = 'resolved', resolved_at = NOW()
  WHERE sa.alert_type = 'low_stock'
    AND sa.status IN ('active', 'acknowledged')
    AND EXISTS (
      SELECT 1 FROM stock_items si
      JOIN products p ON p.id = si.product_id
      WHERE si.product_id = sa.product_id
        AND si.warehouse_id = sa.warehouse_id
        AND COALESCE(si.qty, 0) >= COALESCE((p.product_metadata->>'reorder_point')::numeric, 0)
        AND COALESCE((p.product_metadata->>'reorder_point')::numeric, 0) > 0
    );
END;
$$ LANGUAGE plpgsql;

COMMIT;
