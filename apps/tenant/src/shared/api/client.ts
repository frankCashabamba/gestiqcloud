import { createSharedClient } from '@shared'
import { TENANT_AUTH } from '@shared/endpoints'
import { env } from '../../env'
import { TOKEN_KEY } from '../../constants/storage'
import { resolveRuntimeApiBase } from '../../lib/runtimeApi'

const normalizedBase = resolveRuntimeApiBase(env.apiUrl).replace(/\/+$/g, '')
// Quita sufijos /api o /api/v1 para evitar duplicar el prefijo en las rutas TENANT_AUTH.*
const baseWithoutApiSuffix = normalizedBase.replace(/\/api(?:\/v1)?$/i, '')

const api = createSharedClient({
  // Usa el host del backend provisto por la app y evita duplicar el prefijo /api
  baseURL: baseWithoutApiSuffix,
  tokenKey: TOKEN_KEY,
  refreshPath: TENANT_AUTH.refresh,
  csrfPath: TENANT_AUTH.csrf,
  authExemptSuffixes: [TENANT_AUTH.login, TENANT_AUTH.refresh, TENANT_AUTH.logout],
})

export default api
