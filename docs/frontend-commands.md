# Comandos frontend (Admin/Tenant)

## Admin
```bash
cd apps/admin
npm install           # primera vez
npm run typecheck
npm run build
npm run dev -- --host --port 8081
```

## Tenant (PWA)
```bash
cd apps/tenant
npm install
npm run typecheck
npm run build
npm run test          # Vitest si se habilita
npm run dev -- --host --port 8082
```

## Overrides de API en local
- Admin/Tenant: exporta `VITE_API_URL` con el ORIGIN del backend (ej. `http://localhost:8000` en local, `https://api.gestiqcloud.com` en prod) — NO incluyas `/api` ni `/v1`; las rutas ya usan el prefijo canónico `/api/v1/*`. Define también `VITE_ADMIN_ORIGIN`/`VITE_TENANT_ORIGIN` según host.
- Limpiar SW (tenant) si cambias basepath o API: Ctrl+F5 o borrar SW en DevTools.

## Validación recomendada antes de subir código

Ambas apps tienen scripts de lint, test y coverage en `package.json`.

Admin (`apps/admin`):
- `npm run typecheck`
- `npm run lint`
- `npm run test:run`
- `npm run build`
- `npm run check` (typecheck + lint)

Tenant (`apps/tenant`):
- `npm run typecheck`
- `npm run lint`
- `npm run test:run`
- `npm run check` (typecheck + lint + test:run)

Nota: en Tenant, `npm run check` ya encadena typecheck + lint + test. En Admin, `check` solo cubre typecheck + lint (correr `test:run` aparte).

## Troubleshooting rápido
- Errores de CORS/cookies: revisar `VITE_API_URL` y orígenes; en prod el Worker CF gestiona CORS/cookies.
- Assets desactualizados en tenant: limpiar SW o esperar prompt de actualización.
