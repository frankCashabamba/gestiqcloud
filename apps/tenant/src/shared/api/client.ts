import { createSharedClient } from '@shared'
import { TENANT_AUTH } from '@shared/endpoints'

const api = createSharedClient({
  // Base vacía: los endpoints ya incluyen '/v1/*' para evitar duplicados
  baseURL: '',
  tokenKey: 'access_token_tenant',
  refreshPath: TENANT_AUTH.refresh,
  csrfPath: TENANT_AUTH.csrf,
  authExemptSuffixes: [TENANT_AUTH.login, TENANT_AUTH.refresh, TENANT_AUTH.logout],
})

export default api

