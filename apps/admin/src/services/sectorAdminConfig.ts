/**
 * Service para editar configuración de sectores en admin
 * FASE 6: Admin UI sin redeploy
 */

import { apiClient } from "./api"

export interface SectorConfig {
  code: string
  name: string
  config: {
    branding: {
      icon: string
      displayName: string
      primaryColor: string
      secondaryColor?: string
      units?: Array<{ code: string; label: string }>
      formatRules?: Record<string, any>
      printConfig?: Record<string, any>
      requiredFields?: Record<string, string[]>
    }
    features?: Record<string, boolean>
    defaults?: {
      categories?: string[]
      tax_rate?: number
      currency?: string
      locale?: string
      timezone?: string
      price_includes_tax?: boolean
    }
    fields?: Record<string, any>
    placeholders?: Record<string, any>
    modules?: Record<string, any>
    pos?: Record<string, any>
    inventory?: Record<string, any>
    endpoints?: Record<string, string>
  }
  lastModified: string | null
  modifiedBy: string | null
  configVersion: number
}

export interface UpdateSectorConfigRequest {
  config: SectorConfig["config"]
  reason?: string
}

export interface UpdateResponse {
  success: boolean
  message: string
  timestamp: string
  version: number
  sectorCode: string
}

function normalizeBranding(input: any) {
  return {
    icon: String(input?.icon || ''),
    displayName: String(input?.displayName ?? input?.display_name ?? ''),
    primaryColor: String(input?.primaryColor ?? input?.color_primario ?? ''),
    secondaryColor: input?.secondaryColor ?? input?.color_secundario ?? undefined,
    units: Array.isArray(input?.units)
      ? input.units.map((unit: any) => ({
          code: String(unit?.code || ''),
          label: String(unit?.label || ''),
        }))
      : undefined,
    formatRules: input?.formatRules ?? input?.format_rules ?? undefined,
    printConfig: input?.printConfig ?? input?.print_config ?? undefined,
    requiredFields: input?.requiredFields ?? input?.required_fields ?? undefined,
  }
}

function toApiBranding(input: SectorConfig["config"]["branding"]) {
  return {
    icon: input.icon,
    display_name: input.displayName,
    color_primario: input.primaryColor,
    color_secundario: input.secondaryColor,
    units: input.units,
    format_rules: input.formatRules,
    print_config: input.printConfig,
    required_fields: input.requiredFields,
  }
}

function normalizeConfig(input: any): SectorConfig["config"] {
  return {
    branding: normalizeBranding(input?.branding || {}),
    features: input?.features ?? undefined,
    defaults: input?.defaults ?? undefined,
    fields: input?.fields ?? undefined,
    placeholders: input?.placeholders ?? undefined,
    modules: input?.modules ?? undefined,
    pos: input?.pos ?? undefined,
    inventory: input?.inventory ?? undefined,
    endpoints: input?.endpoints ?? undefined,
  }
}

function toApiConfig(config: SectorConfig["config"]) {
  return {
    branding: toApiBranding(config.branding),
    features: config.features,
    defaults: config.defaults,
    fields: config.fields,
    placeholders: config.placeholders,
    modules: config.modules,
    pos: config.pos,
    inventory: config.inventory,
    endpoints: config.endpoints,
  }
}

function normalizeSectorConfigResponse(raw: any): SectorConfig {
  return {
    code: String(raw?.code || ''),
    name: String(raw?.name || ''),
    config: normalizeConfig(raw?.config || raw?.template_config || {}),
    lastModified: raw?.lastModified ?? raw?.last_modified ?? null,
    modifiedBy: raw?.modifiedBy ?? raw?.modified_by ?? null,
    configVersion: Number(raw?.configVersion ?? raw?.config_version ?? 0),
  }
}

function toApiUpdateResponse(raw: any): UpdateResponse {
  return {
    success: Boolean(raw?.success),
    message: String(raw?.message || ''),
    timestamp: String(raw?.timestamp || ''),
    version: Number(raw?.version ?? 0),
    sectorCode: String(raw?.sectorCode ?? raw?.sector_code ?? ''),
  }
}

export const sectorAdminConfigService = {
  /**
   * Obtener configuración actual de un sector
   */
  async getSectorConfig(sectorCode: string): Promise<SectorConfig> {
    const response = await apiClient.get(`/api/v1/admin/sectors/${sectorCode}/config`)
    return normalizeSectorConfigResponse(response.data)
  },

  /**
   * Actualizar configuración de un sector
   * Cambios instantáneos sin redeploy
   */
  async updateSectorConfig(
    sectorCode: string,
    config: SectorConfig["config"],
    reason?: string
  ): Promise<UpdateResponse> {
    const response = await apiClient.put(`/api/v1/admin/sectors/${sectorCode}/config`, {
      config: toApiConfig(config),
      reason
    })
    return toApiUpdateResponse(response.data)
  },

  /**
   * Listar todos los sectores disponibles
   */
  async listSectors(): Promise<Array<{ code: string; name: string }>> {
    const response = await apiClient.get("/api/v1/sectors")
    return response.data.data || []
  },

  /**
   * Validar configuración antes de guardar
   */
  validateConfig(config: SectorConfig["config"]): string[] {
    const errors: string[] = []

    // Validar branding
    if (!config.branding) {
      errors.push("Branding configuration is required")
    } else {
      if (!config.branding.icon) {
        errors.push("Branding icon is required")
      }
      if (!config.branding.displayName) {
        errors.push("Branding displayName is required")
      }
      if (!config.branding.primaryColor) {
        errors.push("Branding primaryColor is required")
      } else if (!isValidHexColor(config.branding.primaryColor)) {
        errors.push(`Invalid hex color: ${config.branding.primaryColor}`)
      }
      if (!config.branding.secondaryColor) {
        errors.push("Branding secondaryColor is required")
      } else if (!isValidHexColor(config.branding.secondaryColor)) {
        errors.push(`Invalid hex color: ${config.branding.secondaryColor}`)
      }
    }

    // Validar defaults
    if (config.defaults?.tax_rate !== undefined) {
      if (config.defaults.tax_rate < 0 || config.defaults.tax_rate > 1) {
        errors.push("Tax rate must be between 0 and 1")
      }
    }

    return errors
  }
}

function isValidHexColor(color: string): boolean {
  if (!color.startsWith("#")) return false
  if (color.length !== 7) return false
  try {
    parseInt(color.slice(1), 16)
    return true
  } catch {
    return false
  }
}
