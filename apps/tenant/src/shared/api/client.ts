import { createClient } from '@shared/http'
import { TENANT_AUTH } from '@shared/endpoints'

const api = createClient({
  baseURL: '/api',
  tokenKey: 'access_token_tenant',
  refreshPath: TENANT_AUTH.refresh,
  csrfPath: TENANT_AUTH.csrf,
  authExemptSuffixes: [TENANT_AUTH.login, TENANT_AUTH.refresh, TENANT_AUTH.logout],
})

export default api
