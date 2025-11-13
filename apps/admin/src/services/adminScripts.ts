import api from '../shared/api/client'

export async function runTenantScript(tenantId: string, script: string, args?: Record<string, any>): Promise<{ ok: boolean }> {
  const { data } = await api.post(`/api/v1/admin/tenants/${encodeURIComponent(tenantId)}/scripts/run`, { script, args })
  return data
}

export async function executeSQL(sql: string): Promise<{ ok: boolean; rowcount?: number; rows?: any[] }> {
  const { data } = await api.post('/api/v1/admin/sql/execute', { sql })
  return data
}
