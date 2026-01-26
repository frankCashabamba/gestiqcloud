## 2026-01-22_010_enforce_tenant_currency

Enforces that any `currency` stored in tenant-scoped tables matches the tenant currency configured in DB:

1) `company_settings.currency`
2) fallback `tenants.base_currency`

Behavior:
- If tenant currency is configured and `NEW.currency` is NULL/empty: it is auto-filled with the tenant currency.
- If `NEW.currency` is set and mismatches: the write fails (`currency_mismatch`).
- If tenant currency is not configured: the write fails if a currency is provided (`currency_not_configured`).

