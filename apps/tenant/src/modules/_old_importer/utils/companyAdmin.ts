export function isCompanyAdmin(profile: any, token?: string | null): boolean {
  if (
    Boolean(profile?.es_admin_empresa) ||
    Boolean(profile?.is_company_admin) ||
    Boolean(profile?.is_admin_company) ||
    Boolean(profile?.is_admin_empresa)
  ) {
    return true
  }

  if (!token) return false
  try {
    const [, payload] = token.split('.')
    if (!payload) return false
    const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as Record<string, any>
    return Boolean(
      json?.is_admin_company ||
      json?.is_company_admin ||
      json?.es_admin_empresa ||
      json?.is_admin_empresa,
    )
  } catch {
    return false
  }
}
