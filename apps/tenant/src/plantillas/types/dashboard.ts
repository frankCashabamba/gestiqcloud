/**
 * Tipos para Dashboard Retail
 */

export interface KPIMetric {
  label: string
  value: number | string
  delta: string // Ej: "+8.1%", "-2.3%"
  trend?: 'up' | 'down' | 'neutral'
  hint?: string
}

export interface KPIData {
  ventas_dia?: {
    total?: number
    tickets?: number
    ticket_medio?: number
  }
  stock_rotacion?: {
    productos_alta_rotacion?: number
    productos_baja_rotacion?: number
    reposicion_necesaria?: number
  }
  comparativa_semana?: {
    actual?: number
    anterior?: number
    variacion?: number
  }
}

export interface Alert {
  id: string
  title: string
  description: string
  tag: string
  severity: 'alta' | 'media' | 'baja'
  timestamp: Date
  dismissible?: boolean
  action?: {
    label: string
    href: string
  }
}

export interface StockCriticoItem {
  sku: string
  producto: string
  sucursal: string
  stock: number
  minimo: number
  estado: 'crítico' | 'bajo' | 'normal'
}

export interface QuickAction {
  id: string
  label: string
  icon: string
  disabled: boolean
  action: () => void
  requiresModule: string | null
  requiresPermission?: string
}

export interface CustomLink {
  label: string
  href: string
  icon: string
}

export interface DashboardState {
  loading: boolean
  kpis: KPIData
  alerts: Alert[]
  stockCritico: StockCriticoItem[]
  openShift: any | null
  activeRegister: any | null
}

export interface DashboardContextType {
  state: DashboardState
  actions: {
    refreshKPIs: () => Promise<void>
    dismissAlert: (id: string) => void
    navigateTo: (route: string) => void
  }
}

/**
 * Configuración por sector
 */
export type SectorType = 'retail' | 'panaderia' | 'taller'

export interface SectorConfig {
  name: string
  icon: string
  defaultKPIs: string[]
  defaultAlerts: string[]
  enabledModules: string[]
  customActions?: QuickAction[]
}

export const SECTOR_CONFIGS: Record<SectorType, SectorConfig> = {
  retail: {
    name: 'Retail ERP',
    icon: 'R',
    defaultKPIs: ['ventas_dia', 'stock_rotacion', 'comparativa_semana'],
    defaultAlerts: ['stock_critico', 'compras_atrasadas', 'cartera_vencida', 'margen_negativo'],
    enabledModules: ['dashboard', 'pos', 'ventas', 'inventario', 'clientes', 'facturas'],
  },
  panaderia: {
    name: 'Panadería Pro',
    icon: 'P',
    defaultKPIs: ['ventas_dia', 'produccion', 'stock_materias'],
    defaultAlerts: ['vencimiento_productos', 'stock_critico', 'falta_materiales'],
    enabledModules: ['dashboard', 'pos', 'inventario', 'produccion'],
  },
  taller: {
    name: 'Taller Pro',
    icon: 'T',
    defaultKPIs: ['ordenes_pendientes', 'ingresos', 'repuestos'],
    defaultAlerts: ['ordenes_retrasadas', 'repuestos_faltantes'],
    enabledModules: ['dashboard', 'ordenes', 'inventario', 'clientes'],
  },
}

/**
 * Estados posibles para una acción del dashboard
 */
export type ActionState = 'idle' | 'loading' | 'success' | 'error'

export interface ActionStatus {
  state: ActionState
  message?: string
  error?: Error
}
