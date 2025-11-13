-- Revertir mejoras de check_low_stock()

BEGIN;

-- Restaurar función original (solo low_stock, sin detección de negativos)
CREATE OR REPLACE FUNCTION check_low_stock()
RETURNS void AS $$
BEGIN
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
    AND COALESCE(si.qty, 0) < COALESCE((p.product_metadata->>'reorder_point')::numeric, 0)
    AND NOT EXISTS (
      SELECT 1 FROM stock_alerts sa
      WHERE sa.tenant_id = si.tenant_id
        AND sa.product_id = si.product_id
        AND sa.warehouse_id = sa.warehouse_id
        AND sa.status IN ('active', 'acknowledged')
        AND sa.created_at > NOW() - INTERVAL '24 hours'
    );

  UPDATE stock_alerts sa
  SET status = 'resolved', resolved_at = NOW()
  WHERE sa.status IN ('active', 'acknowledged')
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
