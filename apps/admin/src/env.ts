import { z } from 'zod'
import type { UiEnv } from '@ui/env'

// Parse raw envs with permissive types; validate API URL manually for broader compatibility
const Schema = z.object({
  VITE_API_URL: z.string(),
  VITE_BASE_PATH: z.string().min(1).default('/'),
  VITE_TENANT_ORIGIN: z.string().url(),
  VITE_ADMIN_ORIGIN: z.string().url(),
})

const parsed = Schema.safeParse(import.meta.env)
if (!parsed.success) {
  console.error(parsed.error.flatten().fieldErrors)
  throw new Error('Invalid VITE_* environment variables for ADMIN')
}

const e = parsed.data

function isAbsUrlOrPath(v: string): boolean {
  if (!v) return false
  if (v.startsWith('/')) return true
  try { new URL(v); return true } catch { return false }
}
if (!isAbsUrlOrPath(e.VITE_API_URL)) {
  console.error({ VITE_API_URL: ['Invalid: must be absolute URL or path starting with /'] })
  throw new Error('Invalid VITE_* environment variables for ADMIN')
}

export const env: UiEnv = {
  apiUrl: e.VITE_API_URL,
  basePath: e.VITE_BASE_PATH || '/',
  tenantOrigin: e.VITE_TENANT_ORIGIN,
  adminOrigin: e.VITE_ADMIN_ORIGIN,
  mode: (import.meta.env.MODE as UiEnv['mode']) ?? 'development',
  dev: import.meta.env.DEV,
  prod: import.meta.env.PROD,
}
