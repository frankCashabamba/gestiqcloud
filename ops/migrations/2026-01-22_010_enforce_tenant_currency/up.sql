-- Enforce tenant currency at DB level (Postgres)

CREATE OR REPLACE FUNCTION public.enforce_tenant_currency()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected text;
BEGIN
  -- Only enforce when we can scope to a tenant
  IF NEW.tenant_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT NULLIF(upper(trim(cs.currency)), '') INTO expected
  FROM company_settings cs
  WHERE cs.tenant_id = NEW.tenant_id
  LIMIT 1;

  IF expected IS NULL THEN
    SELECT NULLIF(upper(trim(t.base_currency)), '') INTO expected
    FROM tenants t
    WHERE t.id = NEW.tenant_id
    LIMIT 1;
  END IF;

  -- Validate configured currency format (ISO 4217)
  IF expected IS NOT NULL AND expected !~ '^[A-Z]{3}$' THEN
    expected := NULL;
  END IF;

  -- No currency configured in DB: do not allow inventing one
  IF expected IS NULL THEN
    IF NEW.currency IS NULL OR trim(NEW.currency) = '' THEN
      RETURN NEW;
    END IF;
    RAISE EXCEPTION 'currency_not_configured' USING ERRCODE = '23514';
  END IF;

  -- Auto-fill missing currency with tenant currency
  IF NEW.currency IS NULL OR trim(NEW.currency) = '' THEN
    NEW.currency = expected;
    RETURN NEW;
  END IF;

  -- Validate provided currency format (ISO 4217)
  IF upper(trim(NEW.currency)) !~ '^[A-Z]{3}$' THEN
    RAISE EXCEPTION 'invalid_currency' USING ERRCODE = '23514';
  END IF;

  -- Strict match
  IF upper(trim(NEW.currency)) <> expected THEN
    RAISE EXCEPTION 'currency_mismatch (expected %, got %)', expected, NEW.currency USING ERRCODE = '23514';
  END IF;

  -- Normalize stored value
  NEW.currency = expected;
  RETURN NEW;
END;
$$;

-- Triggers on main tenant-scoped currency tables
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_pos_receipts ON pos_receipts;
CREATE TRIGGER trg_enforce_tenant_currency_pos_receipts
BEFORE INSERT OR UPDATE OF currency, tenant_id ON pos_receipts
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_sales_orders ON sales_orders;
CREATE TRIGGER trg_enforce_tenant_currency_sales_orders
BEFORE INSERT OR UPDATE OF currency, tenant_id ON sales_orders
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_store_credits ON store_credits;
CREATE TRIGGER trg_enforce_tenant_currency_store_credits
BEFORE INSERT OR UPDATE OF currency, tenant_id ON store_credits
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_bank_accounts ON bank_accounts;
CREATE TRIGGER trg_enforce_tenant_currency_bank_accounts
BEFORE INSERT OR UPDATE OF currency, tenant_id ON bank_accounts
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_bank_transactions ON bank_transactions;
CREATE TRIGGER trg_enforce_tenant_currency_bank_transactions
BEFORE INSERT OR UPDATE OF currency, tenant_id ON bank_transactions
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_cash_closings ON public.cash_closings;
CREATE TRIGGER trg_enforce_tenant_currency_cash_closings
BEFORE INSERT OR UPDATE OF currency, tenant_id ON public.cash_closings
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_cash_movements ON public.cash_movements;
CREATE TRIGGER trg_enforce_tenant_currency_cash_movements
BEFORE INSERT OR UPDATE OF currency, tenant_id ON public.cash_movements
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_documents ON documents;
CREATE TRIGGER trg_enforce_tenant_currency_documents
BEFORE INSERT OR UPDATE OF currency, tenant_id ON documents
FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency();

-- CRM tables live in later migrations but trigger creation is safe when the table exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'crm_opportunities'
  ) THEN
    EXECUTE 'DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_crm_opportunities ON crm_opportunities';
    EXECUTE 'CREATE TRIGGER trg_enforce_tenant_currency_crm_opportunities
             BEFORE INSERT OR UPDATE OF currency, tenant_id ON crm_opportunities
             FOR EACH ROW EXECUTE FUNCTION public.enforce_tenant_currency()';
  END IF;
END $$;
