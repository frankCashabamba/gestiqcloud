import { createClient } from '@shared/http'
import { ADMIN_AUTH } from '@shared/endpoints'
import { env } from '../../env'

// Base profesional: usamos el gateway con rutas '/v1/*' sin añadir '/api'
const baseURL = env.apiUrl.replace(/\/+$/g, '')

const api = createClient({
  baseURL,
  tokenKey: 'access_token_admin',
  refreshPath: ADMIN_AUTH.refresh,
  csrfPath: ADMIN_AUTH.csrf,
  authExemptSuffixes: [ADMIN_AUTH.login, ADMIN_AUTH.refresh, ADMIN_AUTH.logout, '/v1/auth/login', '/v1/auth/refresh', '/v1/auth/logout'],
})

export default api
