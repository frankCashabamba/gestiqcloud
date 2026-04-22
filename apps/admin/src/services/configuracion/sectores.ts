import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type ModuleConfig = {
  enabled?: boolean
  order?: number
  permissions?: string[]
  config?: Record<string, any> | null
}

export type BrandingConfig = {
  primaryColor: string
  secondaryColor: string
  logo?: string | null
  startTemplate: string
  dashboardTemplate: string
}

export type SectorTemplateConfig = {
  features: Record<string, boolean>
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
  templateConfig: SectorTemplateConfig
  active?: boolean
  configVersion?: number | null
}

export type SectorPayload = Omit<Sector, 'id'>

export const DEFAULT_TEMPLATE_CONFIG: SectorTemplateConfig = {
  features: {},
  modules: {},
  branding: {
    primaryColor: '#4f46e5',
    secondaryColor: '#111827',
    logo: null,
    startTemplate: 'default',
    dashboardTemplate: 'default',
  },
  defaults: {},
  pos: {},
  inventory: {},
}

function normalizeBranding(input: any): BrandingConfig {
  return {
    primaryColor: String(input?.primaryColor ?? input?.color_primario ?? '#4f46e5'),
    secondaryColor: String(input?.secondaryColor ?? input?.color_secundario ?? '#111827'),
    logo: input?.logo ?? null,
    startTemplate: String(input?.startTemplate ?? input?.plantilla_inicio ?? input?.dashboard_template ?? 'default'),
    dashboardTemplate: String(input?.dashboardTemplate ?? input?.dashboard_template ?? input?.plantilla_inicio ?? 'default'),
  }
}

function toApiBranding(input: BrandingConfig) {
  return {
    color_primario: input.primaryColor,
    color_secundario: input.secondaryColor,
    logo: input.logo ?? null,
    plantilla_inicio: input.startTemplate,
    dashboard_template: input.dashboardTemplate,
  }
}

function normalizeTemplateConfig(input: any): SectorTemplateConfig {
  return {
    features: input?.features ?? {},
    modules: input?.modules ?? {},
    branding: normalizeBranding(input?.branding ?? {}),
    defaults: input?.defaults ?? {},
    pos: input?.pos ?? {},
    inventory: input?.inventory ?? {},
  }
}

function toApiTemplateConfig(input: SectorTemplateConfig) {
  return {
    features: input.features,
    modules: input.modules,
    branding: toApiBranding(input.branding),
    defaults: input.defaults,
    pos: input.pos,
    inventory: input.inventory,
  }
}

function normalizeSector(raw: any): Sector {
  return {
    id: String(raw?.id || ''),
    name: String(raw?.name || ''),
    code: raw?.code ?? null,
    description: raw?.description ?? null,
    templateConfig: normalizeTemplateConfig(raw?.templateConfig ?? raw?.template_config ?? {}),
    active: raw?.active ?? true,
    configVersion: raw?.configVersion ?? raw?.config_version ?? null,
  }
}

function toApiSectorPayload(payload: SectorPayload) {
  return {
    name: payload.name,
    code: payload.code,
    description: payload.description,
    template_config: toApiTemplateConfig(payload.templateConfig),
    active: payload.active,
  }
}

export async function listSectores(): Promise<Sector[]> {
  const { data } = await api.get<Sector[]>(ADMIN_CONFIG.sectors.base)
  return (data || []).map(normalizeSector)
}

export async function getSector(id: number | string): Promise<Sector> {
  const { data } = await api.get<Sector>(ADMIN_CONFIG.sectors.byId(id))
  return normalizeSector(data)
}

export async function createSector(payload: SectorPayload): Promise<Sector> {
  const { data } = await api.post<Sector>(ADMIN_CONFIG.sectors.base, toApiSectorPayload(payload))
  return normalizeSector(data)
}

export async function updateSector(id: number | string, payload: SectorPayload): Promise<Sector> {
  const { data } = await api.put<Sector>(ADMIN_CONFIG.sectors.byId(id), toApiSectorPayload(payload))
  return normalizeSector(data)
}

export async function removeSector(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.sectors.byId(id))
}
