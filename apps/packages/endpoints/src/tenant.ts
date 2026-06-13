export const TENANT_AUTH = {
  login: '/api/v1/tenant/auth/login',
  refresh: '/api/v1/tenant/auth/refresh',
  csrf: '/api/v1/tenant/auth/csrf',
  logout: '/api/v1/tenant/auth/logout',
  setPassword: '/api/v1/tenant/auth/set-password',
  signup: '/api/v1/tenant/auth/signup',
}

export const TENANT_MODULES = {
  list: '/api/v1/modules',
  byCompany: (empresaSlug: string) => `/api/v1/modules/company/${encodeURIComponent(empresaSlug)}`,
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

export const TENANT_PROMOTIONS = {
  base: '/api/v1/tenant/promotions',
  byId: (id: string) => `/api/v1/tenant/promotions/${id}`,
  validate: '/api/v1/tenant/promotions/validate',
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
  availablePermissions: '/api/v1/tenant/roles/available-permissions',
}

export const TENANT_SETTINGS = {
  base: '/api/v1/company/settings',
  theme: '/api/v1/company/settings/theme',
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

export const TENANT_ANALYTICS = {
  kpis: '/api/v1/tenant/dashboard/kpis',
  kpisBySector: (sector: string) => `/api/v1/tenant/dashboard/kpis/${encodeURIComponent(sector)}`,
}

export const TENANT_AI = {
  ask: '/api/v1/tenant/ai/ask',
  act: '/api/v1/tenant/ai/act',
  catalog: '/api/v1/tenant/ai/catalog',
  chatStream: '/api/v1/tenant/ai/chat/stream',
  feedback: '/api/v1/tenant/ai/feedback',
  conversations: '/api/v1/tenant/ai/conversations',
  suggestions: '/api/v1/tenant/ai/suggestions',
  metrics: '/api/v1/tenant/ai/metrics',
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
  optimize: (id: string) => `${RECIPES_BASE}/${id}/optimize`,
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

export const TENANT_PRODUCTION_ORDERS = {
  base: `${PRODUCTION_BASE}/orders`,
  byId: (id: string) => `${PRODUCTION_BASE}/orders/${id}`,
  start: (id: string) => `${PRODUCTION_BASE}/orders/${id}/start`,
  complete: (id: string) => `${PRODUCTION_BASE}/orders/${id}/complete`,
  cancel: (id: string) => `${PRODUCTION_BASE}/orders/${id}/cancel`,
  costs: (id: string) => `${PRODUCTION_BASE}/orders/${id}/costs`,
}

export const TENANT_PRODUCTION_PLANNING = {
  suggestions: `${PRODUCTION_BASE}/planning/suggestions`,
}

const ACCOUNTING_BASE = '/api/v1/tenant/accounting'
export const TENANT_ACCOUNTING = {
  chartOfAccounts: {
    base: `${ACCOUNTING_BASE}/chart-of-accounts`,
    byId: (id: string) => `${ACCOUNTING_BASE}/chart-of-accounts/${id}`,
    seed: `${ACCOUNTING_BASE}/chart-of-accounts/seed`,
    ledger: (id: string) => `${ACCOUNTING_BASE}/chart-of-accounts/${id}/ledger`,
  },
  transactions: `${ACCOUNTING_BASE}/transactions`,
  journalEntries: {
    base: `${ACCOUNTING_BASE}/journal-entries`,
    byId: (id: string) => `${ACCOUNTING_BASE}/journal-entries/${id}`,
    cancel: (id: string) => `${ACCOUNTING_BASE}/journal-entries/${id}/cancel`,
    post: (id: string) => `${ACCOUNTING_BASE}/journal-entries/${id}/post`,
  },
  reports: {
    profitLoss: `${ACCOUNTING_BASE}/reports/profit-loss`,
    balanceSheet: `${ACCOUNTING_BASE}/reports/balance-sheet`,
  },
  pos: {
    settings: `${ACCOUNTING_BASE}/pos/settings`,
    paymentMethods: `${ACCOUNTING_BASE}/pos/payment-methods`,
    paymentMethodById: (id: string) => `${ACCOUNTING_BASE}/pos/payment-methods/${id}`,
  },
}

const POS_BASE = '/api/v1/tenant/pos'
export const TENANT_POS = {
  base: POS_BASE,
  dailyCounts: `${POS_BASE}/daily_counts`,
  registers: `${POS_BASE}/registers`,
  registerById: (id: number | string) => `${POS_BASE}/registers/${id}`,
  shifts: `${POS_BASE}/shifts`,
  shiftSummary: (shiftId: number | string) => `${POS_BASE}/shifts/${shiftId}/summary`,
  closeShift: (shiftId: number | string) => `${POS_BASE}/shifts/${shiftId}/close`,
  currentShift: (registerId: number | string) => `${POS_BASE}/shifts/current/${registerId}`,
  receipts: `${POS_BASE}/receipts`,
  receiptById: (id: number | string) => `${POS_BASE}/receipts/${id}`,
  receiptCalculateTotals: `${POS_BASE}/receipts/calculate_totals`,
  receiptCheckout: (id: number | string) => `${POS_BASE}/receipts/${id}/checkout`,
  receiptToInvoice: (id: number | string) => `${POS_BASE}/receipts/${id}/to_invoice`,
  receiptRefund: (id: number | string) => `${POS_BASE}/receipts/${id}/refund`,
  receiptPrint: (id: number | string) => `${POS_BASE}/receipts/${id}/print`,
  receiptBackfillDocuments: (id: number | string) => `${POS_BASE}/receipts/${id}/backfill_documents`,
  storeCredits: `${POS_BASE}/store_credits`,
  storeCreditByCode: (code: string) => `${POS_BASE}/store_credits/code/${encodeURIComponent(code)}`,
  redeemStoreCredit: `${POS_BASE}/store_credits/redeem`,
  shiftAccounting: (shiftId: string) => `${POS_BASE}/shifts/${shiftId}/accounting`,
}

const REPORTS_BASE = '/api/v1/tenant/reports'
export const TENANT_REPORTS = {
  base: REPORTS_BASE,
  export: `${REPORTS_BASE}/export`,
  financial: `${REPORTS_BASE}/financial`,
  generate: `${REPORTS_BASE}/generate`,
  inventory: `${REPORTS_BASE}/inventory`,
  sales: `${REPORTS_BASE}/sales`,
  profit: `${REPORTS_BASE}/profit`,
  productMargins: `${REPORTS_BASE}/product-margins`,
  recalculate: `${REPORTS_BASE}/recalculate`,
}

const WEBHOOKS_BASE = '/api/v1/tenant/webhooks'
export const TENANT_WEBHOOKS = {
  base: WEBHOOKS_BASE,
  byId: (id: string) => `${WEBHOOKS_BASE}/${id}`,
  test: (id: string) => `${WEBHOOKS_BASE}/${id}/test`,
}

const NOTIFICATIONS_BASE = '/api/v1/tenant/notifications'
export const TENANT_NOTIFICATIONS = {
  base: NOTIFICATIONS_BASE,
  markRead: `${NOTIFICATIONS_BASE}/mark-read`,
  unreadCount: `${NOTIFICATIONS_BASE}/unread-count`,
  archive: (id: string) => `${NOTIFICATIONS_BASE}/${id}/archive`,
}

const EINVOICING_BASE = '/api/v1/tenant/einvoicing'
export const TENANT_EINVOICING = {
  sendSii: `${EINVOICING_BASE}/send-sii`,
  retry: (id: string) => `${EINVOICING_BASE}/einvoice/${id}/retry`,
  status: (id: string) => `${EINVOICING_BASE}/einvoice/${id}/status`,
  facturaeExport: (id: number | string) => `${EINVOICING_BASE}/facturae/${id}/export`,
}

// E-invoicing genérico (sin /tenant): envío y consulta de estado por factura.
export const EINVOICING = {
  send: '/api/v1/einvoicing/send',
  status: (invoiceId: string) => `/api/v1/einvoicing/status/${invoiceId}`,
}

export const TENANT_INVENTORY = {
  base: '/api/v1/tenant/inventory',
}

export const TENANT_RECONCILIATION = {
  base: '/api/v1/tenant/reconciliation',
}

const RESTAURANT_BASE = '/api/v1/tenant/restaurant'
export const TENANT_RESTAURANT = {
  base: RESTAURANT_BASE,
  orders: `${RESTAURANT_BASE}/orders`,
}

export const TENANT_TEMPLATES = {
  uiConfig: '/api/v1/tenant/templates/ui-config',
}

export const TENANT_DOCUMENTS = {
  base: '/api/v1/tenant/documents',
  sales: '/api/v1/tenant/documents/sales',
  byId: (id: number | string) => `/api/v1/tenant/documents/${id}`,
  render: (id: number | string) => `/api/v1/tenant/documents/${id}/render`,
  print: (id: number | string) => `/api/v1/tenant/documents/${id}/print`,
  salesDraft: '/api/v1/tenant/documents/sales/draft',
  salesIssue: '/api/v1/tenant/documents/sales/issue',
}

const PRODUCTS_BASE = '/api/v1/tenant/products'
export const TENANT_PRINTING = {
  base: '/api/v1/tenant/printing',
}

export const TENANT_MFA = {
  base: '/api/v1/tenant/auth/mfa',
}

export const TENANT_QUOTES = {
  base: '/api/v1/tenant/quotes',
}

const BUSINESS_CATEGORIES_BASE = '/api/v1/business-categories'
export const TENANT_BUSINESS_CATEGORIES = {
  base: BUSINESS_CATEGORIES_BASE,
  byCode: (code: string) => `${BUSINESS_CATEGORIES_BASE}/${code}`,
}

export const TENANT_SECTORS = {
  units: (code: string) => `/api/v1/sectors/${encodeURIComponent(code)}/units`,
}

// Módulos del catálogo (config consolidada por tenant)
export const SETTINGS_MODULES = '/api/v1/settings/modules'

// Telegram bot (integración de notificaciones)
export const TENANT_TELEGRAM = {
  generateSecret: '/api/v1/telegram/generate-secret',
  registerWebhook: '/api/v1/telegram/register-webhook',
}

// Canales de notificación de incidencias (admin) consumidos desde settings tenant
const INCIDENT_CHANNELS_BASE = '/api/v1/admin/incidents/notifications/channels'
export const ADMIN_INCIDENT_CHANNELS = {
  base: INCIDENT_CHANNELS_BASE,
  byId: (id: string) => `${INCIDENT_CHANNELS_BASE}/${id}`,
}

export const TENANT_PRODUCTS = {
  products: {
    list: PRODUCTS_BASE,
    get: (id: string) => `${PRODUCTS_BASE}/${id}`,
    create: PRODUCTS_BASE,
    update: (id: string) => `${PRODUCTS_BASE}/${id}`,
    delete: (id: string) => `${PRODUCTS_BASE}/${id}`,
    search: (q: string) => `${PRODUCTS_BASE}/search?q=${encodeURIComponent(q)}`,
    purge: `${PRODUCTS_BASE}/purge`,
    bulkActive: `${PRODUCTS_BASE}/bulk/active`,
    bulkCategory: `${PRODUCTS_BASE}/bulk/category`,
    bulkGenerateSkus: `${PRODUCTS_BASE}/bulk/generate-skus`,
    similarDuplicates: `${PRODUCTS_BASE}/duplicates/similar`,
    mergeDuplicates: `${PRODUCTS_BASE}/duplicates/merge`,
  },
  rawMaterials: `${PRODUCTS_BASE}/raw-materials`,
  variants: `${PRODUCTS_BASE}/variants`,
  categories: {
    list: `${PRODUCTS_BASE}/product-categories`,
    create: `${PRODUCTS_BASE}/product-categories`,
    delete: (id: string) => `${PRODUCTS_BASE}/product-categories/${id}`,
  },
}
