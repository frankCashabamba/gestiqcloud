export const TENANT_AUTH = {
  login: '/api/v1/tenant/auth/login',
  refresh: '/api/v1/tenant/auth/refresh',
  csrf: '/api/v1/tenant/auth/csrf',
  logout: '/api/v1/tenant/auth/logout',
  setPassword: '/api/v1/tenant/auth/set-password',
  signup: '/api/v1/tenant/auth/signup',
}

export const TENANT_MODULES = {
  // add tenant endpoints if exposed publicly
}

export const TENANT_COMPANIES = {
  base: '/api/v1/company',
}

export const TENANT_CLIENTS = {
  base: '/api/v1/tenant/clients',
  byId: (id: number | string) => `/api/v1/tenant/clients/${id}`,
}

export const TENANT_SUPPLIERS = {
  base: '/api/v1/tenant/suppliers',
  byId: (id: number | string) => `/api/v1/tenant/suppliers/${id}`,
}

export const TENANT_SALES = {
  base: '/api/v1/tenant/sales_orders',
  byId: (id: number | string) => `/api/v1/tenant/sales_orders/${id}`,
}

export const TENANT_PURCHASES = {
  base: '/api/v1/tenant/purchases',
  byId: (id: number | string) => `/api/v1/tenant/purchases/${id}`,
}

export const TENANT_CASHBOX = {
  base: '/api/v1/tenant/finance/cashbox/movements',
}

export const TENANT_BANKS = {
  base: '/api/v1/tenant/finance/bank/movements',
  balances: '/api/v1/tenant/finance/bank/balances',
}

export const TENANT_ONBOARDING = {
  init: '/api/v1/tenant/onboarding/init',
}

export const TENANT_BILLING = {
  plans: '/api/v1/tenant/billing/plans',
  subscription: '/api/v1/tenant/billing/subscription',
  subscribe: '/api/v1/tenant/billing/subscribe',
  changePlan: '/api/v1/tenant/billing/change-plan',
  cancel: '/api/v1/tenant/billing/cancel',
  portal: '/api/v1/tenant/billing/portal',
}

export const TENANT_USERS = {
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
  seedOperational: '/api/v1/tenant/roles/seed-operational',
}

export const TENANT_SETTINGS = {
  general: '/api/v1/company/settings/general',
  branding: '/api/v1/company/settings/branding',
  brandingLogoUpload: '/api/v1/company/settings/branding/logo',
  fiscal: '/api/v1/company/settings/fiscal',
  schedules: '/api/v1/company/settings/schedules',
  limits: '/api/v1/company/settings/limits',
}

export const TENANT_INVOICING = {
  base: '/api/v1/tenant/invoicing',
  byId: (id: number | string) => `/api/v1/tenant/invoicing/${id}`,
}



export const TENANT_EXPENSES = {
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

export const TENANT_HR = {
  me: '/api/v1/tenant/hr/me',
  mePayroll: '/api/v1/tenant/hr/me/payroll',
  vacations: {
    base: '/api/v1/tenant/hr/vacations',
    byId: (id: number | string) => `/api/v1/tenant/hr/vacations/${id}`,
    approve: (id: number | string) => `/api/v1/tenant/hr/vacations/${id}/approve`,
    reject: (id: number | string) => `/api/v1/tenant/hr/vacations/${id}/reject`,
  },
  employees: {
    base: '/api/v1/tenant/hr/employees',
    byId: (id: number | string) => `/api/v1/tenant/hr/employees/${id}`,
  },
  timekeeping: {
    base: '/api/v1/tenant/hr/timekeeping',
    byId: (id: number | string) => `/api/v1/tenant/hr/timekeeping/${id}`,
  },
  payroll: {
    base: '/api/v1/tenant/hr/payroll',
    byId: (id: number | string) => `/api/v1/tenant/hr/payroll/${id}`,
    generate: '/api/v1/tenant/hr/payroll/generate',
    confirm: (id: number | string) => `/api/v1/tenant/hr/payroll/${id}/confirm`,
    markPaid: (id: number | string) => `/api/v1/tenant/hr/payroll/${id}/mark-paid`,
    delete: (id: number | string) => `/api/v1/tenant/hr/payroll/${id}`,
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
  costLines: (id: string) => `${RECIPES_BASE}/${id}/cost-lines`,
  costLineById: (id: string, lineId: string) => `${RECIPES_BASE}/${id}/cost-lines/${lineId}`,
  fullCost: (id: string) => `${RECIPES_BASE}/${id}/full-cost`,
  bulkFullCosts: `${RECIPES_BASE}/bulk-full-costs`,
}

const PRODUCTION_BASE = '/api/v1/tenant/production'
export const TENANT_COST_DRIVERS = {
  list: `${PRODUCTION_BASE}/cost-drivers`,
  byId: (id: string) => `${PRODUCTION_BASE}/cost-drivers/${id}`,
  applyAll: `${PRODUCTION_BASE}/cost-drivers/apply-all-recipes`,
}

export const TENANT_COST_DRIVER_UNIT_TYPES = {
  list: `${PRODUCTION_BASE}/cost-driver-unit-types`,
}
