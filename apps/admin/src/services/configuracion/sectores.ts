import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type ModuleConfig = {
  enabled?: boolean
  order?: number
  permissions?: string[]
  config?: Record<string, any> | null
}

export type BrandingConfig = {
  color_primario: string
  logo?: string | null
  plantilla_inicio: string
  dashboard_template: string
}

export type SectorTemplateConfig = {
  modules: Record<string, ModuleConfig>
  branding: BrandingConfig
  defaults: Record<string, any>
  pos: Record<string, any>
  inventory: Record<string, any>
}

export type Sector = {
  id: string
  name: string
  code?: string | null
  description?: string | null
  template_config: SectorTemplateConfig
  active?: boolean
  config_version?: number | null
}

export type SectorPayload = Omit<Sector, 'id'>

export const DEFAULT_TEMPLATE_CONFIG: SectorTemplateConfig = {
  modules: {},
  branding: {
    color_primario: '#4f46e5',
    logo: null,
    plantilla_inicio: 'default',
    dashboard_template: 'default',
  },
  defaults: {},
  pos: {},
  inventory: {},
}

export async function listSectores(): Promise<Sector[]> {
  const { data } = await api.get<Sector[]>(ADMIN_CONFIG.sectores.base)
  return data || []
}

export async function getSector(id: number | string): Promise<Sector> {
  const { data } = await api.get<Sector>(ADMIN_CONFIG.sectores.byId(id))
  return data
}

export async function createSector(payload: SectorPayload): Promise<Sector> {
  const { data } = await api.post<Sector>(ADMIN_CONFIG.sectores.base, payload)
  return data
}

export async function updateSector(id: number | string, payload: SectorPayload): Promise<Sector> {
  const { data } = await api.put<Sector>(ADMIN_CONFIG.sectores.byId(id), payload)
  return data
}

export async function removeSector(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.sectores.byId(id))
}
