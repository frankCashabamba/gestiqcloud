import { z } from 'zod'
import type { UiEnv } from '@ui/env'

const Schema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_BASE_PATH: z.string().min(1).default('/'),
  VITE_TENANT_ORIGIN: z.string().url(),
  VITE_ADMIN_ORIGIN: z.string().url(),
})

const parsed = Schema.safeParse(import.meta.env)
if (!parsed.success) {
  const fieldErrors = 'error' in parsed ? parsed.error.flatten().fieldErrors : {}
  console.error(fieldErrors)
  throw new Error('Invalid VITE_* environment variables for TENANT')
}

const e = parsed.data

export const env: UiEnv = {
  apiUrl: e.VITE_API_URL,
  basePath: e.VITE_BASE_PATH || '/',
  tenantOrigin: e.VITE_TENANT_ORIGIN,
  adminOrigin: e.VITE_ADMIN_ORIGIN,
  mode: (import.meta.env.MODE as UiEnv['mode']) ?? 'development',
  dev: import.meta.env.DEV,
  prod: import.meta.env.PROD,
}
