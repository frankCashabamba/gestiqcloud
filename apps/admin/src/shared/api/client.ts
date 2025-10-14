import { createClient } from '@shared/http'
import { ADMIN_AUTH } from '@shared/endpoints'
import { env } from '../../env'

// Ensure baseURL targets the worker/API entry point without duplicating segments.
function normalizeBaseUrl(raw: string) {
  const trimmed = (raw || '').trim()
  if (!trimmed) return '/api'

  const noTrailingSlash = trimmed.replace(/\/+$/g, '')

  // Resolve pathname to detect if the provided URL already carries /api or /v1.
  let pathname = noTrailingSlash
  try {
    pathname = new URL(noTrailingSlash, 'http://gestiqcloud.local').pathname.replace(/\/+$/g, '')
  } catch {
    // Relative paths ("/v1") fall back to the raw value for suffix detection.
    pathname = noTrailingSlash.replace(/^[^/]+:\/\//, '')
  }

  const endsWithApi = /\/api$/i.test(pathname)
  const endsWithV1 = /\/v1$/i.test(pathname)

  if (endsWithApi || endsWithV1) {
    return noTrailingSlash
  }

  return `${noTrailingSlash}/api`
}

const baseWithApi = normalizeBaseUrl(env.apiUrl)

const api = createClient({
  baseURL: baseWithApi,
  tokenKey: 'access_token_admin',
  refreshPath: ADMIN_AUTH.refresh,
  csrfPath: ADMIN_AUTH.csrf,
  authExemptSuffixes: [ADMIN_AUTH.login, ADMIN_AUTH.refresh, ADMIN_AUTH.logout, '/v1/auth/login', '/v1/auth/refresh', '/v1/auth/logout'],
})

export default api
