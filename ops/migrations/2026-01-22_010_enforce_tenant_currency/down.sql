-- Remove tenant currency enforcement

DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_pos_receipts ON pos_receipts;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_sales_orders ON sales_orders;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_store_credits ON store_credits;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_bank_accounts ON bank_accounts;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_bank_transactions ON bank_transactions;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_cash_closings ON public.cash_closings;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_cash_movements ON public.cash_movements;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_documents ON documents;
DROP TRIGGER IF EXISTS trg_enforce_tenant_currency_crm_opportunities ON crm_opportunities;

DROP FUNCTION IF EXISTS public.enforce_tenant_currency();
