import tenantApi from '../shared/api/client'

export async function resolveTenantPath(): Promise<string> {
  try {
    const { data } = await tenantApi.get('/api/v1/me/tenant')
    const d = data as any
    if (!d?.onboarding_complete) return '/onboarding'
    const slug = d?.empresa_slug
    if (slug) return `/${slug}`
  } catch {}
  return '/'
}
