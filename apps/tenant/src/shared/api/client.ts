import { createSharedClient } from '@shared'
import { TENANT_AUTH } from '@shared/endpoints'

const api = createSharedClient({
  // El gateway sólo expone '/v1/*' en producción
  baseURL: '/v1',
  tokenKey: 'access_token_tenant',
  refreshPath: TENANT_AUTH.refresh,
  csrfPath: TENANT_AUTH.csrf,
  authExemptSuffixes: [TENANT_AUTH.login, TENANT_AUTH.refresh, TENANT_AUTH.logout],
})

export default api
