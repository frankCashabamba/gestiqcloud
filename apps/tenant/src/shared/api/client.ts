import { createSharedClient } from '@shared'
import { TENANT_AUTH } from '@shared/endpoints'

export const tenantApiConfig = {
  baseURL: '/api',
  tokenKey: 'access_token_tenant',
  refreshPath: TENANT_AUTH.refresh,
  csrfPath: TENANT_AUTH.csrf,
  authExemptSuffixes: [TENANT_AUTH.login, TENANT_AUTH.refresh, TENANT_AUTH.logout],
}

const api = createSharedClient(tenantApiConfig)

export default api
