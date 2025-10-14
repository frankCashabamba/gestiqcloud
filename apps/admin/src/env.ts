import { z } from 'zod'
import type { UiEnv } from '@ui/env'

// Accept absolute URL or leading-slash path (e.g., '/v1') for same-origin via gateway
const UrlOrPath = z.string().refine((v) => {
  if (!v) return false
  if (v.startsWith('/')) return true
  try { new URL(v); return true } catch { return false }
}, { message: 'VITE_API_URL must be an absolute URL or a leading-slash path' })

const Schema = z.object({
  VITE_API_URL: UrlOrPath,
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

export const env: UiEnv = {
  apiUrl: e.VITE_API_URL,
  basePath: e.VITE_BASE_PATH || '/',
  tenantOrigin: e.VITE_TENANT_ORIGIN,
  adminOrigin: e.VITE_ADMIN_ORIGIN,
  mode: (import.meta.env.MODE as UiEnv['mode']) ?? 'development',
  dev: import.meta.env.DEV,
  prod: import.meta.env.PROD,
}
