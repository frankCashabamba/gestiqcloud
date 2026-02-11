/**
 * Navigation Service
 * Centraliza rutas y helpers de navegación para el dashboard retail
 */

export type RetailRoute =
  | 'pos.new'
  | 'pos.cash-close'
  | 'ventas.promotions'
  | 'ventas.list'
  | 'clientes.new'
  | 'clientes.list'
  | 'inventario.list'
  | 'inventario.replenishment'
  | 'inventario.count-cycle'
  | 'reportes.analysis'
  | 'reportes.sales'

export interface NavigationConfig {
  route: RetailRoute
  empresa: string
  params?: Record<string, string | number>
}

/**
 * Mapeo de rutas retail
 */
const ROUTE_MAP: Record<RetailRoute, string> = {
  'pos.new': '/pos/new',
  'pos.cash-close': '/pos/cash-close',
  'ventas.promotions': '/ventas/promotions',
  'ventas.list': '/ventas',
  'clientes.new': '/clientes/new',
  'clientes.list': '/clientes',
  'inventario.list': '/inventario',
  'inventario.replenishment': '/inventario/replenishment',
  'inventario.count-cycle': '/inventario/count-cycle',
  'reportes.analysis': '/reportes/analysis',
  'reportes.sales': '/reportes/sales',
}

/**
 * Construye una ruta absoluta
 * @param config Configuración de navegación
 * @returns Ruta absoluta lista para usar con navigate()
 * @example
 * buildRoute({ route: 'pos.new', empresa: 'acme' })
 * // => '/acme/pos/new'
 */
export function buildRoute(config: NavigationConfig): string {
  const basePath = `/${config.empresa}`
  const routePath = ROUTE_MAP[config.route]

  if (!routePath) {
    console.warn(`Unknown route: ${config.route}`)
    return basePath
  }

  let fullPath = basePath + routePath

  // Agregar query params si existen
  if (config.params && Object.keys(config.params).length > 0) {
    const searchParams = new URLSearchParams()
    Object.entries(config.params).forEach(([key, value]) => {
      searchParams.append(key, String(value))
    })
    fullPath += `?${searchParams.toString()}`
  }

  return fullPath
}

/**
 * Tipos de modalidades para quick actions
 */
export type ActionMode = 'navigate' | 'modal' | 'dialog'

/**
 * Configuración para quick actions
 */
export interface QuickActionConfig {
  id: string
  label: string
  icon: string
  module: string
  mode: ActionMode
  route?: RetailRoute
  modalComponent?: string // Nombre del componente modal
}

/**
 * Quick actions definidas por sector
 */
export const RETAIL_QUICK_ACTIONS: QuickActionConfig[] = [
  {
    id: 'new-sale',
    label: 'New sale',
    icon: '+',
    module: 'pos',
    mode: 'navigate',
    route: 'pos.new',
  },
  {
    id: 'create-promotion',
    label: 'Create promotion',
    icon: '%',
    module: 'ventas',
    mode: 'modal',
    modalComponent: 'CreatePromotionModal',
  },
  {
    id: 'new-customer',
    label: 'New customer',
    icon: '@',
    module: 'clientes',
    mode: 'navigate',
    route: 'clientes.new',
  },
  // Nota: "Price update" y "Cycle count" eliminados (botones muertos)
  // Agregar cuando haya módulos específicos para estas funcionalidades
]

/**
 * Custom links para sidebar (módulo-específicos)
 */
export const RETAIL_CUSTOM_LINKS = (enabledModules: string[]) => {
  const links = [
    {
      module: 'inventario',
      label: 'Stock replenishment',
      route: 'inventario.replenishment' as RetailRoute,
      icon: 'S',
    },
    {
      module: 'ventas',
      label: 'Promotions',
      route: 'ventas.promotions' as RetailRoute,
      icon: 'P',
    },
    {
      module: 'reportes',
      label: 'Sales analysis',
      route: 'reportes.analysis' as RetailRoute,
      icon: 'A',
    },
  ]

  return links.filter((link) => enabledModules.includes(link.module))
}

/**
 * Valida si una ruta requiere un módulo específico
 * @param route Ruta a validar
 * @returns Slug del módulo requerido
 */
export function getRequiredModule(route: RetailRoute): string {
  const moduleMap: Record<RetailRoute, string> = {
    'pos.new': 'pos',
    'pos.cash-close': 'pos',
    'ventas.promotions': 'ventas',
    'ventas.list': 'ventas',
    'clientes.new': 'clientes',
    'clientes.list': 'clientes',
    'inventario.list': 'inventario',
    'inventario.replenishment': 'inventario',
    'inventario.count-cycle': 'inventario',
    'reportes.analysis': 'reportes',
    'reportes.sales': 'reportes',
  }

  return moduleMap[route] || 'unknown'
}

/**
 * Helpers para tooltips y mensajes de error
 */
export const MESSAGES = {
  REQUIRES_MODULE: (module: string) => `This action requires the ${module} module to be enabled.`,
  REQUIRES_PERMISSION: (permission: string) => `You don't have permission to ${permission}.`,
  STORE_CLOSED: 'The store is currently closed.',
  NO_ACTIVE_REGISTER: 'No active register found. Please open a cash register first.',
  ACTION_SUCCESS: (action: string) => `${action} completed successfully.`,
  ACTION_ERROR: (action: string) => `Error performing ${action}. Please try again.`,
}

/**
 * Log de auditoría para acciones en dashboard
 */
export interface DashboardAuditLog {
  action: string
  timestamp: string
  usuario?: string
  empresa?: string
  metadata?: Record<string, any>
}

export function logDashboardAction(log: Omit<DashboardAuditLog, 'timestamp'>) {
  const entry: DashboardAuditLog = {
    ...log,
    timestamp: new Date().toISOString(),
  }

  // En producción: enviar a backend
  console.debug('[Dashboard Audit]', entry)

  // Opcional: guardar en localStorage para debugging
  if (process.env.NODE_ENV === 'development') {
    const key = 'dashboard_audit_logs'
    const existing = JSON.parse(localStorage.getItem(key) || '[]')
    existing.push(entry)
    // Mantener últimas 50 acciones
    if (existing.length > 50) existing.shift()
    localStorage.setItem(key, JSON.stringify(existing))
  }
}
