# Deuda: componentes/hooks que llaman la API directo (sin pasar por services)

Fecha: 2026-06-13

Tras centralizar el catálogo de rutas (`@shared/endpoints`), **toda la capa de datos del tenant está centralizada**: todos los `modules/*/services.ts`, `productsApi.ts`, `services/*.ts`, `services/api/*.ts`, `modules/*/api.ts` usan constantes del catálogo. **0 hardcodes `/api/v1` en la capa de servicios. Typecheck verde.**

Quedan **25 archivos de UI/hooks/contexts** que llaman `apiFetch`/`api` directamente con rutas hardcodeadas. Esto es un **anti-patrón aparte**: el fix correcto no es solo cambiar el string por una constante, sino **mover la llamada a un service** y que el componente consuma el service. Por eso se trata como deuda separada.

## Archivos afectados (por categoría)

### Contexts (3)
- `auth/AuthContext.tsx` (5 rutas) — auth/me
- `contexts/CompanyConfigContext.tsx` (2)
- `contexts/PermissionsContext.tsx` (1) — `/api/v1/me/tenant`

### Hooks (8) — mayormente catálogos sectoriales
- `hooks/useGlobalCatalogs.ts` (6), `hooks/useCompanySectorFullConfig.ts` (4), `hooks/useDashboardKPIs.ts` (3)
- `hooks/useSectorConfig.ts`, `useSectorPlaceholders.ts`, `useSectorValidationRules.ts`, `useCurrency.ts`, `useDocumentIDTypes.ts` (1-2 c/u)
- → Sugerencia: crear `TENANT_SECTORS.{config,placeholders,validations,fullConfig}` y `TENANT_CATALOGS.*`, o un `services/api/catalogs.ts`.

### Componentes de módulo (10)
- `modules/products/List.tsx` (3, printing), `modules/products/Form.tsx` (2, settings/recipes)
- `modules/settings/Avanzado.tsx` (6), `modules/settings/BranchesManager.tsx` (4)
- `modules/productions/OrderForm.tsx`, `RecetaDetail.tsx`, `RecetasList.tsx` (1-2 c/u)
- `modules/customers/Form.tsx`, `modules/finances/CashForm.tsx`, `modules/hr/NominaForm.tsx`, `modules/billing/components/ProductLineInput.tsx` (1 c/u)

### Pages / otros (4)
- `pages/Onboarding.tsx` (3), `plantillas/components/DashboardPro.tsx` (1), `lib/tenantNavigation.ts` (1)

## Recomendación
1. Para cada componente, mover la llamada `apiFetch(...)` a su `services.ts` del módulo (o a un service compartido para catálogos/sectores), usando una constante del catálogo.
2. Ampliar `@shared/endpoints` con los dominios que falten: `TENANT_SECTORS` (config/placeholders/validations/full-config), catálogos globales, `/api/v1/me/*`, branches, dashboard KPIs.
3. El componente solo importa funciones del service, nunca `apiFetch` ni rutas.

## App admin
La app admin quedó con **convención unificada** (baseURL host + `/api/v1` absoluto) en la fase anterior, pero su catálogo `ADMIN_*` no se completó al mismo nivel que el tenant. Pendiente equivalente si se desea el mismo grado de centralización.
