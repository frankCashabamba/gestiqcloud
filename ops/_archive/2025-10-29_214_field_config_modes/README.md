Field-config modes per tenant+module

- Table: `tenant_module_settings(tenant_id UUID, module TEXT, form_mode TEXT DEFAULT 'mixed')`.
- Modes:
  - mixed: merge sector defaults + tenant overrides (tenant wins); new sector fields flow automatically.
  - tenant: use only tenant overrides; fallback to sector then base if empty.
  - sector: use only sector defaults; fallback to base if empty.
  - basic: use base hardcoded fields for the module.

