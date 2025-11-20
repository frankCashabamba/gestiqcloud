// src/services/stats.ts
import api from '../shared/api/client'

export interface AdminStats {
  tenants_activos: number
  tenants_total: number
  usuarios_total: number
  usuarios_activos: number
  modulos_activos: number
  modulos_total: number
  migraciones_aplicadas: number
  migraciones_pendientes: number
  tenants_por_dia: Array<{ fecha: string; count: number }>
  ultimos_tenants: Array<{
    id: string
    name: string
    created_at: string
  }>
}

export async function getAdminStats(): Promise<AdminStats> {
  const response = await api.get('/v1/admin/stats')
  return response.data
}
