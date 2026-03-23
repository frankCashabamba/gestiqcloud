-- Agrega campos de trazabilidad de guardado a imp_documento
-- Permite bloquear re-guardado duplicado de gastos, facturas y productos
ALTER TABLE imp_documento
  ADD COLUMN IF NOT EXISTS saved_as      VARCHAR(30)   NULL,
  ADD COLUMN IF NOT EXISTS saved_record_id UUID         NULL,
  ADD COLUMN IF NOT EXISTS saved_at      TIMESTAMPTZ   NULL;

COMMENT ON COLUMN imp_documento.saved_as         IS 'expense | supplier_invoice | products';
COMMENT ON COLUMN imp_documento.saved_record_id  IS 'ID del registro creado (gasto, compra, etc.)';
COMMENT ON COLUMN imp_documento.saved_at         IS 'Timestamp del primer guardado exitoso';
