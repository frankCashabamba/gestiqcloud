# Reality-Checked Status: POS Document ID Types

**Date:** February 18, 2026  
**Scope:** `apps/tenant/src/modules/pos/POSView.tsx` and HR lookup API wiring

## Current State (Verified)

### Implemented
- `useDocumentIDTypes` exists and fetches from `GET /api/v1/hr/document-id-types`.
  - File: `apps/tenant/src/hooks/useDocumentIDTypes.ts`
- The hook no longer hardcodes fallback ID types on API failure.
- POS uses dynamic ID type resolution:
  1. `documentConfig.id_types` / `documentConfig.idTypes` when present.
  2. HR lookup API data (`useDocumentIDTypes`) as fallback source.
- HR lookup router is mounted in the main API router.
  - File: `apps/backend/app/platform/http/router.py`
- HR lookup router prefix was normalized to avoid duplicated API prefixes.
  - File: `apps/backend/app/modules/hr/routes/lookups.py`
- Tenant Vite API target no longer uses implicit localhost fallback.
  - File: `apps/tenant/vite.config.ts`
- Backend Celery Redis setup requires explicit dev/prod env vars (no implicit localhost fallback).
  - Files:
    - `apps/backend/app/config/celery_config.py`
    - `apps/backend/app/modules/imports/application/celery_app.py`
- OpenAI and Telegram API base URLs are now configurable via env variables.
  - Files:
    - `apps/backend/app/services/ai/providers/openai.py`
    - `apps/backend/app/services/ai/factory.py`
    - `apps/backend/app/workers/notifications.py`
- i18n supported languages can be configured via `VITE_SUPPORTED_LANGS` (restricted to built-in `en,es` resources).
  - File: `apps/tenant/src/i18n/index.ts`
- AI connection layer is now deterministic and environment-compatible:
  - `AI_PROVIDER` explicitly controls primary provider when set (`ollama|ovhcloud|openai`).
  - `OLLAMA_BASE_URL` and `OLLAMA_URL` are both accepted.
  - `OVHCLOUD_BASE_URL` and `OVHCLOUD_API_URL` are both accepted.
  - AI providers are initialized during backend startup.
  - AI health is exposed at `GET /api/v1/health/ai`.
  - Files:
    - `apps/backend/app/services/ai/factory.py`
    - `apps/backend/app/services/ai/startup.py`
    - `apps/backend/app/main.py`
    - `apps/backend/app/routers/ai_health.py`
    - `apps/backend/app/platform/http/router.py`
    - `apps/backend/app/modules/imports/interface/http/tenant.py`

### i18n/Language Cleanup Implemented
- Spanish hardcoded UI strings in POS buyer/toolbar/create-product modal were replaced with i18n lookups and English defaults.
- New i18n keys were added in:
  - `apps/tenant/src/locales/en/pos.json`
  - `apps/tenant/src/locales/es/pos.json`

## What Is No Longer Accurate
- Claims that POS is fully DB-driven end-to-end are still too broad.
- Claims that all hardcoded values were removed from the full POS module are not true.

## Remaining Work (Known)
- There are still business/domain constants in other modules that are not tenant-configurable yet.
- Additional hardcoded values still exist across frontend/backend outside this specific POS ID-type path.

## Verified Files
- `apps/tenant/src/hooks/useDocumentIDTypes.ts`
- `apps/tenant/src/modules/pos/POSView.tsx`
- `apps/backend/app/modules/hr/routes/lookups.py`
- `apps/backend/app/platform/http/router.py`
- `apps/tenant/src/locales/en/pos.json`
- `apps/tenant/src/locales/es/pos.json`
