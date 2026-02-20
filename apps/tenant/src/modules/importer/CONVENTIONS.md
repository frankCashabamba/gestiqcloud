# Importer Conventions

## API paths
- Never hardcode `/api/v1/...` inside importer components/services.
- Use `IMPORTS` from `@endpoints/imports` as the single source of truth.
- Tenant routes must go through `IMPORTS.tenant.*`.
- Public analysis/classification/AI routes must go through `IMPORTS.public.*`.

## Progress tracking
- Canonical hook: `hooks/useImportProgress.ts`.
- Transport: HTTP polling to `GET /api/v1/tenant/imports/batches/{id}/status`.
- Do not reintroduce `useImportProgress.tsx` or parallel progress hooks with the same name.

## Services structure
- `services/importsApi.ts` is the canonical client for batch/item lifecycle.
- Feature-specific files (`analyzeApi.ts`, `classifyApi.ts`, `templates.ts`) must still consume `IMPORTS`.
- Avoid creating legacy `services.ts` files in importer.

## Docs sync checklist
When changing endpoints or transport:
1. Update `ARCHITECTURE.md`.
2. Update `MEJORAS_IMPLEMENTADAS.md`.
3. Update `README.md` index if source of truth changed.
