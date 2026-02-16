-- Add AP/VAT-input/default-expense accounts to tenant_accounting_settings.
-- Equivalent to Alembic: apps/backend/alembic/versions/011_accounting_settings_ap_expense.py

ALTER TABLE public.tenant_accounting_settings
    ADD COLUMN IF NOT EXISTS ap_account_id UUID NULL,
    ADD COLUMN IF NOT EXISTS vat_input_account_id UUID NULL,
    ADD COLUMN IF NOT EXISTS default_expense_account_id UUID NULL;

-- Add FK constraints (idempotent via pg_constraint checks).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenant_accounting_settings_ap_account_id_fkey'
    ) THEN
        ALTER TABLE public.tenant_accounting_settings
            ADD CONSTRAINT tenant_accounting_settings_ap_account_id_fkey
            FOREIGN KEY (ap_account_id)
            REFERENCES public.chart_of_accounts(id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenant_accounting_settings_vat_input_account_id_fkey'
    ) THEN
        ALTER TABLE public.tenant_accounting_settings
            ADD CONSTRAINT tenant_accounting_settings_vat_input_account_id_fkey
            FOREIGN KEY (vat_input_account_id)
            REFERENCES public.chart_of_accounts(id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenant_accounting_settings_default_expense_account_id_fkey'
    ) THEN
        ALTER TABLE public.tenant_accounting_settings
            ADD CONSTRAINT tenant_accounting_settings_default_expense_account_id_fkey
            FOREIGN KEY (default_expense_account_id)
            REFERENCES public.chart_of_accounts(id)
            ON DELETE CASCADE;
    END IF;
END $$;

