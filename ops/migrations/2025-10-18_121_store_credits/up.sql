-- Migration: 2025-10-18_121_store_credits
-- Description: Sistema de vales/créditos de tienda para devoluciones

BEGIN;

-- Tabla de vales/créditos
CREATE TABLE IF NOT EXISTS store_credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  code TEXT UNIQUE NOT NULL,
  customer_id UUID,
  currency CHAR(3) NOT NULL,
  amount_initial NUMERIC(12,2) NOT NULL CHECK (amount_initial >= 0),
  amount_remaining NUMERIC(12,2) NOT NULL CHECK (amount_remaining >= 0),
  expires_at DATE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  CONSTRAINT chk_store_credit_status CHECK (status IN ('active', 'redeemed', 'expired', 'void')),
  CONSTRAINT chk_store_credit_amounts CHECK (amount_remaining <= amount_initial)
);

-- Índices para búsquedas rápidas
CREATE INDEX idx_store_credits_tenant_id ON store_credits(tenant_id);
CREATE INDEX idx_store_credits_code ON store_credits(code);
CREATE INDEX idx_store_credits_customer_id ON store_credits(customer_id) WHERE customer_id IS NOT NULL;
CREATE INDEX idx_store_credits_status ON store_credits(status) WHERE status = 'active';
CREATE INDEX idx_store_credits_expires_at ON store_credits(expires_at) WHERE expires_at IS NOT NULL;

-- Tabla de eventos de crédito (auditoría)
CREATE TABLE IF NOT EXISTS store_credit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  credit_id UUID NOT NULL REFERENCES store_credits(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  ref_doc_type TEXT,
  ref_doc_id UUID,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by UUID,
  
  CONSTRAINT chk_store_credit_event_type CHECK (type IN ('issue', 'redeem', 'expire', 'void', 'adjust'))
);

CREATE INDEX idx_store_credit_events_credit_id ON store_credit_events(credit_id);
CREATE INDEX idx_store_credit_events_ref_doc ON store_credit_events(ref_doc_type, ref_doc_id) 
WHERE ref_doc_id IS NOT NULL;

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_store_credit_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_store_credits_updated_at
  BEFORE UPDATE ON store_credits
  FOR EACH ROW
  EXECUTE FUNCTION update_store_credit_timestamp();

-- Función helper para generar código único
CREATE OR REPLACE FUNCTION generate_store_credit_code()
RETURNS TEXT AS $$
DECLARE
  code TEXT;
  exists BOOLEAN;
BEGIN
  LOOP
    -- Generar código: SC-XXXXXX (6 chars alfanuméricos)
    code := 'SC-' || upper(substring(md5(random()::text) from 1 for 6));
    
    -- Verificar si existe
    SELECT EXISTS(SELECT 1 FROM store_credits WHERE store_credits.code = code) INTO exists;
    EXIT WHEN NOT exists;
  END LOOP;
  
  RETURN code;
END;
$$ LANGUAGE plpgsql;

-- RLS policies
ALTER TABLE store_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE store_credit_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_store_credits ON store_credits
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation_store_credit_events ON store_credit_events
  USING (
    EXISTS (
      SELECT 1 FROM store_credits sc 
      WHERE sc.id = store_credit_events.credit_id 
        AND sc.tenant_id::text = current_setting('app.tenant_id', TRUE)
    )
  );

-- Comentarios
COMMENT ON TABLE store_credits IS 'Vales/créditos de tienda para devoluciones sin efectivo';
COMMENT ON COLUMN store_credits.code IS 'Código único del vale (ej: SC-A1B2C3)';
COMMENT ON COLUMN store_credits.status IS 'Estado: active, redeemed, expired, void';
COMMENT ON TABLE store_credit_events IS 'Historial de transacciones de vales';

COMMIT;
