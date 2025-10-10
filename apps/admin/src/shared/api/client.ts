import { createClient } from '@shared/http'
import { ADMIN_AUTH } from '@shared/endpoints'
import { env } from '../../env'

// Ensure baseURL includes /api path once
const baseNoSlash = env.apiUrl.replace(/\/+$/g, '')
const baseWithApi = /\/api$/i.test(baseNoSlash) ? baseNoSlash : `${baseNoSlash}/api`

const api = createClient({
  baseURL: baseWithApi,
  tokenKey: 'access_token_admin',
  refreshPath: ADMIN_AUTH.refresh,
  csrfPath: ADMIN_AUTH.csrf,
  authExemptSuffixes: [ADMIN_AUTH.login, ADMIN_AUTH.refresh, ADMIN_AUTH.logout, '/v1/auth/login', '/v1/auth/refresh', '/v1/auth/logout'],
})

export default api
