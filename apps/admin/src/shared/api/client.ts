import { normalizeBaseUrl } from '@shared/api/baseUrl'
import { createClient } from '@shared/http'
import { ADMIN_AUTH } from '@shared/endpoints'
import { env } from '../../env'

// Ensure baseURL targets the worker/API entry point without duplicating segments.
export const adminApiConfig = {
  baseURL: normalizeBaseUrl(env.apiUrl),
  tokenKey: 'access_token_admin',
  refreshPath: ADMIN_AUTH.refresh,
  csrfPath: ADMIN_AUTH.csrf,
  authExemptSuffixes: [
    ADMIN_AUTH.login,
    ADMIN_AUTH.refresh,
    ADMIN_AUTH.logout,
    '/v1/auth/login',
    '/v1/auth/refresh',
    '/v1/auth/logout',
  ],
}

const api = createClient(adminApiConfig)

export default api
