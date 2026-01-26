import tenantApi from '../shared/api/client'

export async function resolveTenantPath(): Promise<string> {
  try {
    const { data } = await tenantApi.get('/api/v1/me/tenant')
    const slug = (data as any)?.empresa_slug
    if (slug) return `/${slug}`
  } catch {}
  return '/'
}
