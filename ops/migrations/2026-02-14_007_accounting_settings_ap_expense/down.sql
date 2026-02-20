-- Best-effort rollback for AP/VAT-input/default-expense accounts.

ALTER TABLE public.tenant_accounting_settings
    DROP CONSTRAINT IF EXISTS tenant_accounting_settings_default_expense_account_id_fkey,
    DROP CONSTRAINT IF EXISTS tenant_accounting_settings_vat_input_account_id_fkey,
    DROP CONSTRAINT IF EXISTS tenant_accounting_settings_ap_account_id_fkey;

ALTER TABLE public.tenant_accounting_settings
    DROP COLUMN IF EXISTS default_expense_account_id,
    DROP COLUMN IF EXISTS vat_input_account_id,
    DROP COLUMN IF EXISTS ap_account_id;
