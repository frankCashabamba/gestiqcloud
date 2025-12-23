Migration to consolidate legacy `tenant_settings` into `company_settings`.

Steps:
- Backfill missing rows in `company_settings` from `tenant_settings` (if the legacy table exists).
- Drop the legacy table to avoid future drift.
- The down script recreates `tenant_settings` and copies data back from `company_settings` for rollback.
