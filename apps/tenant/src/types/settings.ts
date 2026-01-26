export interface CompanySettings {
  id: string
  tenant_id: string
  general: GeneralSettings
  fiscal: FiscalSettings
  modules: ModuleSettings
  notifications: NotificationSettings
  created_at: string
  updated_at: string
}

export interface GeneralSettings {
  nombre_empresa: string
  nombre_comercial?: string
  logo_url?: string
  idioma: 'es' | 'en'
  timezone: string
  moneda: string | null
  formato_fecha: string
  formato_hora: string
}

export interface FiscalSettings {
  pais: 'ES' | 'EC'
  tipo_documento: 'NIF' | 'CIF' | 'RUC'
  numero_documento: string
  direccion_fiscal: string
  city: string
  provincia?: string
  codigo_postal: string
  regimen_fiscal?: string
  iva_incluido: boolean
  tasa_iva_default: number
}

export interface ModuleSettings {
  pos_enabled: boolean
  inventory_enabled: boolean
  invoicing_enabled: boolean
  crm_enabled: boolean
  accounting_enabled: boolean
  ventas_enabled: boolean
  compras_enabled: boolean
  gastos_enabled: boolean
  finanzas_enabled: boolean
  rrhh_enabled: boolean
}

export interface NotificationSettings {
  email_enabled: boolean
  email_from?: string
  sms_enabled: boolean
  push_enabled: boolean
  notify_low_stock: boolean
  notify_new_orders: boolean
  notify_invoice_due: boolean
}

export interface ModuleInfo {
  id: string
  name: string
  displayName: string
  description: string
  icon: string
  enabled: boolean
  route: string
  permissions: string[]
  dependencies?: string[]
}

export interface CompanySettingsUpdate {
  general?: Partial<GeneralSettings>
  fiscal?: Partial<FiscalSettings>
  modules?: Partial<ModuleSettings>
  notifications?: Partial<NotificationSettings>
}

export interface UserPreferences {
  id: string
  user_id: string
  tenant_id: string
  theme: 'light' | 'dark' | 'auto'
  sidebar_collapsed: boolean
  language: 'es' | 'en'
  dashboard_widgets: string[]
  notifications_enabled: boolean
  email_notifications: boolean
  created_at: string
  updated_at: string
}

export interface UserPreferencesUpdate extends Partial<Omit<UserPreferences, 'id' | 'user_id' | 'tenant_id' | 'created_at' | 'updated_at'>> {}

export interface SystemInfo {
  version: string
  environment: 'development' | 'staging' | 'production'
  features: Record<string, boolean>
  limits: {
    max_users: number
    max_products: number
    max_storage_mb: number
  }
}
