export type SettingsGeneral = { razon_social?: string; tax_id?: string; ruc?: string; address?: string; direccion?: string }
export type SettingsBranding = { colorPrimario?: string; logoUrl?: string }
export type SettingsFiscal = { regimen?: string; iva?: number }
export type SettingsHorarios = { apertura?: string; cierre?: string }
export type SettingsLimites = { usuariosMax?: number }

export type NotificationChannelType = 'email' | 'whatsapp' | 'telegram'

export type NotificationChannel = {
  id: string
  tenant_id?: string
  tipo: NotificationChannelType
  name: string
  description?: string | null
  config: Record<string, unknown>
  active: boolean
  use_for_alerts?: boolean
  use_for_invoices?: boolean
  use_for_marketing?: boolean
}

export type NotificationChannelCreate = {
  tipo: NotificationChannelType
  name: string
  config: Record<string, unknown>
  active?: boolean
  use_for_alerts?: boolean
  use_for_invoices?: boolean
  use_for_marketing?: boolean
}

export type NotificationChannelUpdate = {
  name?: string
  config?: Record<string, unknown>
  active?: boolean
}
