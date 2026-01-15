export const TENANT_AUTH = {
  login: '/api/v1/tenant/auth/login',
  refresh: '/api/v1/tenant/auth/refresh',
  csrf: '/api/v1/tenant/auth/csrf',
  logout: '/api/v1/tenant/auth/logout',
  setPassword: '/api/v1/tenant/auth/set-password',
}

export const TENANT_MODULOS = {
  // añade endpoints de tenant si los expones públicamente
}

export const TENANT_EMPRESAS = {
  base: '/api/v1/empresa',
}

export const TENANT_CLIENTES = {
  base: '/api/v1/tenant/clientes',
  byId: (id: number | string) => `/api/v1/tenant/clientes/${id}`,
}

export const TENANT_PROVEEDORES = {
  base: '/api/v1/tenant/proveedores/',
  byId: (id: number | string) => `/api/v1/tenant/proveedores/${id}`,
}

export const TENANT_VENTAS = {
  base: '/api/v1/tenant/sales_orders',
  byId: (id: number | string) => `/api/v1/tenant/sales_orders/${id}`,
}

export const TENANT_COMPRAS = {
  base: '/api/v1/tenant/purchases',
  byId: (id: number | string) => `/api/v1/tenant/purchases/${id}`,
}

export const TENANT_CAJA = {
  base: '/api/v1/tenant/finance/caja/movimientos',
}

export const TENANT_BANCOS = {
  base: '/api/v1/tenant/finance/banco/movimientos',
  saldos: '/api/v1/tenant/finance/banco/saldos',
}

export const TENANT_ONBOARDING = {
  init: '/api/v1/tenant/onboarding/init',
}

export const TENANT_USUARIOS = {
  base: '/api/v1/tenant/users',
  byId: (id: number | string) => `/api/v1/tenant/users/${id}`,
  modules: '/api/v1/tenant/users/modules',
  roles: '/api/v1/tenant/users/roles',
  checkUsername: (username: string) => `/api/v1/users/check-username/${encodeURIComponent(username)}`,
  setPassword: (id: number | string) => `/api/v1/tenant/users/${id}/set-password`,
}

export const TENANT_ROLES = {
  base: '/api/v1/tenant/roles',
  byId: (id: number | string) => `/api/v1/tenant/roles/${id}`,
}

export const TENANT_SETTINGS = {
  general: '/api/v1/company/settings/general',
  branding: '/api/v1/company/settings/branding',
  fiscal: '/api/v1/company/settings/fiscal',
  horarios: '/api/v1/company/settings/horarios',
  limites: '/api/v1/company/settings/limites',
}

export const TENANT_FACTURACION = {
  base: '/api/v1/tenant/facturacion',
  byId: (id: number | string) => `/api/v1/tenant/facturacion/${id}`,
}



export const TENANT_GASTOS = {
  base: '/api/v1/tenant/expenses',
  byId: (id: number | string) => `/api/v1/tenant/expenses/${id}`,
}

export const TENANT_CRM = {
  base: '/api/v1/tenant/crm',
  dashboard: '/api/v1/tenant/crm/dashboard',
  leads: {
    base: '/api/v1/tenant/crm/leads',
    byId: (id: string) => `/api/v1/tenant/crm/leads/${id}`,
    convert: (id: string) => `/api/v1/tenant/crm/leads/${id}/convert`,
  },
  opportunities: {
    base: '/api/v1/tenant/crm/opportunities',
    byId: (id: string) => `/api/v1/tenant/crm/opportunities/${id}`,
  },
  activities: {
    base: '/api/v1/tenant/crm/activities',
    byId: (id: string) => `/api/v1/tenant/crm/activities/${id}`,
  },
}

export const TENANT_RRHH = {
  vacaciones: {
    base: '/api/v1/tenant/hr/vacaciones',
    byId: (id: number | string) => `/api/v1/tenant/hr/vacaciones/${id}`,
    approve: (id: number | string) => `/api/v1/tenant/hr/vacaciones/${id}/approve`,
    reject: (id: number | string) => `/api/v1/tenant/hr/vacaciones/${id}/reject`,
  },
  empleados: {
    base: '/api/v1/tenant/hr/empleados',
    byId: (id: number | string) => `/api/v1/tenant/hr/empleados/${id}`,
  },
}

const RECIPES_BASE = '/api/v1/tenant/production/recipes'
export const TENANT_RECIPES = {
  base: RECIPES_BASE,
  list: RECIPES_BASE,
  byId: (id: string) => `${RECIPES_BASE}/${id}`,
  costBreakdown: (id: string) => `${RECIPES_BASE}/${id}/cost-breakdown`,
  calculateProduction: (id: string) => `${RECIPES_BASE}/${id}/calculate-production`,
  compare: `${RECIPES_BASE}/compare`,
  addIngredient: (id: string) => `${RECIPES_BASE}/${id}/ingredients`,
  updateIngredient: (id: string, ingredientId: string) => `${RECIPES_BASE}/${id}/ingredients/${ingredientId}`,
  deleteIngredient: (id: string, ingredientId: string) => `${RECIPES_BASE}/${id}/ingredients/${ingredientId}`,
  profitability: (id: string) => `${RECIPES_BASE}/${id}/profitability`,
  purchaseOrder: (id: string) => `${RECIPES_BASE}/${id}/purchase-order`,
}
