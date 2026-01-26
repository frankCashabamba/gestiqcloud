/**
 * @deprecated Este archivo ha sido deprecado.
 *
 * El servicio de onboarding ha sido reemplazado por una implementación directa
 * que utiliza `tenantApi.post(TENANT_ONBOARDING.init, payload)` en Onboarding.tsx
 *
 * Usar:
 * - Frontend: apps/tenant/src/pages/Onboarding.tsx
 * - Endpoint: POST /api/v1/tenant/onboarding/init
 * - Backend: apps/backend/app/routers/onboarding_init.py
 */

// import type { AxiosInstance } from 'axios'

// export function createOnboardingService(api: AxiosInstance, basePath: string) {
//   return {
//     enviarConfiguracionInicial: async <T = any>(payload: any) => {
//       const { data } = await api.post<T>(basePath, payload)
//       return data
//     },
//   }
// }
