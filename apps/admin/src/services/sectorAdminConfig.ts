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
      color_primario: string
      color_secundario?: string
      units?: Array<{ code: string; label: string }>
      format_rules?: Record<string, any>
      print_config?: Record<string, any>
      required_fields?: Record<string, string[]>
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
  last_modified: string | null
  modified_by: string | null
  config_version: number
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
  sector_code: string
}

export const sectorAdminConfigService = {
  /**
   * Obtener configuración actual de un sector
   */
  async getSectorConfig(sectorCode: string): Promise<SectorConfig> {
    const response = await apiClient.get(`/api/v1/admin/sectors/${sectorCode}/config`)
    return response.data
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
      config,
      reason
    })
    return response.data
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
      if (!config.branding.color_primario) {
        errors.push("Branding color_primario is required")
      } else if (!isValidHexColor(config.branding.color_primario)) {
        errors.push(`Invalid hex color: ${config.branding.color_primario}`)
      }
      if (!config.branding.color_secundario) {
        errors.push("Branding color_secundario is required")
      } else if (!isValidHexColor(config.branding.color_secundario)) {
        errors.push(`Invalid hex color: ${config.branding.color_secundario}`)
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
