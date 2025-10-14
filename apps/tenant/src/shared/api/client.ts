import { createSharedClient, normalizeBaseUrl } from '@shared'
import { TENANT_AUTH } from '@shared/endpoints'
import { env } from '../../env'

export const tenantApiConfig = {
  baseURL: normalizeBaseUrl(env.apiUrl),
  tokenKey: 'access_token_tenant',
  refreshPath: TENANT_AUTH.refresh,
  csrfPath: TENANT_AUTH.csrf,
  authExemptSuffixes: [TENANT_AUTH.login, TENANT_AUTH.refresh, TENANT_AUTH.logout],
}

const api = createSharedClient(tenantApiConfig)

export default api
