import { ADMIN_AUTH } from '@shared/endpoints'
import { createClient } from '@shared/http'

import { env } from '../../env'

// baseURL es el ORIGIN del backend (p.ej. https://api.gestiqcloud.com en prod,
// http://localhost:8000 en dev). Las rutas van con prefijo canónico '/api/v1/*'
// (el Cloudflare Worker enruta '/api/*' al backend). NO debe incluir '/api' aquí.
const baseURL = env.apiUrl.replace(/\/+$/g, '')

const api = createClient({
  baseURL,
  tokenKey: 'access_token_admin',
  refreshPath: ADMIN_AUTH.refresh,
  csrfPath: ADMIN_AUTH.csrf,
  authExemptSuffixes: [ADMIN_AUTH.login, ADMIN_AUTH.refresh, ADMIN_AUTH.logout],
})

export default api
