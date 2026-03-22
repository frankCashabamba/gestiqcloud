-- Agrega campos de anticipo (depósito) a crm_opportunities
-- Permite registrar el adelanto que paga el cliente al hacer un pedido especial
-- (panadería, taller, etc.)

ALTER TABLE crm_opportunities
  ADD COLUMN IF NOT EXISTS deposit_amount  NUMERIC(12, 2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS deposit_paid    BOOLEAN        NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);

COMMENT ON COLUMN crm_opportunities.deposit_amount  IS 'Monto del anticipo cobrado al confirmar el pedido';
COMMENT ON COLUMN crm_opportunities.deposit_paid    IS 'TRUE cuando el anticipo ya fue cobrado';
COMMENT ON COLUMN crm_opportunities.payment_method  IS 'Método de pago del anticipo: efectivo, transferencia, tarjeta, etc.';
