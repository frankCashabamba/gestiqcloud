# Hardcoded Values Analysis (Reality-Checked)

**Date:** February 18, 2026
**Status:** Validated against repository state

## Summary
This document reflects the current code state after verification. Some previously reported issues were valid, but several statements in earlier drafts were outdated or overstated.

## Verified as Still Present

### Frontend
- Admin had mixed API fallback behavior across files (`/v1` and localhost absolute fallback) and was unified.
  - `apps/admin/src/constants/api.ts`
  - `apps/admin/src/services/api.ts`
- OCR keyword arrays are hardcoded.
  - `apps/tenant/src/modules/importer/utils/detectarTipoDocumento.ts`
- CRM statuses/stages/types are enum-based and fixed in code.
  - `apps/tenant/src/modules/crm/types.ts`
  - `apps/backend/app/modules/crm/domain/entities.py`
- UI/tenant defaults are centralized but still static constants.
  - `apps/tenant/src/constants/defaults.ts`
- Supported languages are hardcoded to `en` and `es`.
  - `apps/tenant/src/i18n/index.ts`

### Backend
- Payment and transaction enums remain hardcoded.
  - `apps/backend/app/models/core/payment.py`
  - `apps/backend/app/models/core/facturacion.py`
- Numbering service uses fixed literal document type set and prefixes.
  - `apps/backend/app/modules/shared/services/numbering.py`
- OpenAI and Telegram base URL structures are hardcoded.
  - `apps/backend/app/services/ai/providers/openai.py`
  - `apps/backend/app/workers/notifications.py`
- Redis config now requires explicit env vars in all environments (`REDIS_URL`/`REDIS_RESULT_URL` or `DEV_REDIS_URL`/`DEV_REDIS_RESULT_URL` in development).
  - `apps/backend/app/config/celery_config.py`
  - `apps/backend/app/modules/imports/application/celery_app.py`

## Verified as Updated
- Tenant Vite API target no longer has hardcoded localhost fallback (`VITE_API_URL`/`API_URL` required).
  - `apps/tenant/vite.config.ts`
- POS document ID type handling is now dynamic (document config + HR lookup API fallback source).
  - `apps/tenant/src/modules/pos/POSView.tsx`
  - `apps/tenant/src/hooks/useDocumentIDTypes.ts`
- HR lookup routes are mounted in the API router.
  - `apps/backend/app/platform/http/router.py`
- POS buyer/create-product toolbar text cleanup moved hardcoded Spanish literals to i18n-driven labels with English defaults.
  - `apps/tenant/src/modules/pos/POSView.tsx`
  - `apps/tenant/src/locales/en/pos.json`
  - `apps/tenant/src/locales/es/pos.json`

## Notes About Earlier Inaccuracies
- Prior reports claimed full hardcode removal in POS; this was not fully accurate.
- Some file/line references in earlier drafts did not match current implementation locations.
- Some “critical” items were actually development-only fallbacks and should be classified separately.

## Next Practical Steps
1. Done: unified admin API base fallback strategy into one source of truth.
2. Replace enum-driven business catalogs (payment methods, transaction types, CRM states) with tenant-configurable catalogs.
3. Move OCR keyword dictionaries to configurable data.
4. Done: removed implicit localhost fallbacks and enforced explicit dev/prod Redis/API config gates.
