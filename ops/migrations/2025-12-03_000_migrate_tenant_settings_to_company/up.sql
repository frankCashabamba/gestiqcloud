-- Consolidate legacy tenant_settings into company_settings and remove the old table
BEGIN;

-- Backfill only if the legacy table exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'tenant_settings'
  ) THEN
    INSERT INTO company_settings (
      tenant_id,
      default_language,
      timezone,
      currency,
      company_logo,
      secondary_color,
      primary_color,
      allow_custom_roles,
      user_limit,
      working_days,
      business_hours,
      operation_type,
      company_name,
      tax_id,
      tax_regime,
      settings,
      pos_config,
      invoice_config,
      created_at,
      updated_at,
      language_id,
      currency_id
    )
    SELECT
      ts.tenant_id,
      COALESCE(ts.default_language, ts.locale, 'es'),
      COALESCE(ts.timezone, 'Europe/Madrid'),
      COALESCE(ts.currency, 'EUR'),
      ts.company_logo,
      COALESCE(ts.secondary_color, '#6c757d'),
      COALESCE(ts.primary_color, '#4f46e5'),
      COALESCE(ts.allow_custom_roles, TRUE),
      COALESCE(ts.user_limit, 10),
      COALESCE(ts.working_days, ARRAY['monday','tuesday','wednesday','thursday','friday']),
      COALESCE(ts.business_hours, jsonb_build_object('start','09:00','end','18:00')),
      COALESCE(ts.operation_type, 'sales'),
      ts.company_name,
      ts.tax_id,
      ts.tax_regime,
      ts.settings,
      ts.pos_config,
      ts.invoice_config,
      ts.created_at,
      ts.updated_at,
      ts.language_id,
      ts.currency_id
    FROM tenant_settings ts
    WHERE NOT EXISTS (
      SELECT 1 FROM company_settings cs WHERE cs.tenant_id = ts.tenant_id
    );

    -- Drop legacy table to prevent future writes
    DROP TABLE IF EXISTS tenant_settings CASCADE;
  END IF;
END $$;

COMMIT;
