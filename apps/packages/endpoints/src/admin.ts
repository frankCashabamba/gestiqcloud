export const ADMIN_AUTH = {
  login: '/v1/admin/auth/login',
  refresh: '/v1/admin/auth/refresh',
  csrf: '/v1/admin/auth/csrf',
  logout: '/v1/admin/auth/logout',
}

export const ADMIN_MODULES = {
  public: '/v1/admin/modules/public',
  base: '/v1/admin/modules',
  byId: (id: number | string) => `/v1/admin/modules/${id}`,
  byIdForce: (id: number | string) => `/v1/admin/modules/${id}?force=true`,
  activate: (id: number | string) => `/v1/admin/modules/${id}/activate`,
  deactivate: (id: number | string) => `/v1/admin/modules/${id}/deactivate`,
  register: '/v1/admin/modules/register-modules',
}

export const ADMIN_COMPANIES = {
  base: '/v1/admin/companies',
  createFull: '/v1/admin/companies/full-json',
  deleteAll: '/v1/admin/companies/bulk/delete-all',
  purgeOrphans: '/v1/admin/companies/purge-orphans',
  byId: (id: number | string) => `/v1/admin/companies/${id}`,
}

export const ADMIN_COMPANY_MODULES = {
  base: (tenantId: number | string) => `/v1/admin/modules/company/${tenantId}`,
  upsert: (tenantId: number | string) => `/v1/admin/modules/company/${tenantId}/upsert`,
  remove: (tenantId: number | string, moduleId: number | string) => `/v1/admin/modules/company/${tenantId}/module/${moduleId}`,
}

export const ADMIN_CONFIG = {
  currencies: {
    base: '/v1/admin/config/currency',
    byId: (id: number | string) => `/v1/admin/config/currency/${id}`,
  },
  countries: {
    base: '/v1/admin/config/country',
    byId: (id: number | string) => `/v1/admin/config/country/${id}`,
  },
  timezones: {
    base: '/v1/admin/config/timezone',
    byId: (name: string) => `/v1/admin/config/timezone/${encodeURIComponent(name)}`,
  },
  locales: {
    base: '/v1/admin/config/locale',
    byId: (code: string) => `/v1/admin/config/locale/${encodeURIComponent(code)}`,
  },
  languages: {
    base: '/v1/admin/config/language',
    byId: (id: number | string) => `/v1/admin/config/language/${id}`,
  },
  settingsDefaults: {
    base: '/v1/admin/config/settings-defaults',
    byId: (id: number | string) => `/v1/admin/config/settings-defaults/${id}`,
  },
  sectors: {
    base: '/v1/admin/config/template-sector',
    byId: (id: number | string) => `/v1/admin/config/template-sector/${id}`,
  },
  businessType: {
    base: '/v1/admin/config/business-type',
    byId: (id: number | string) => `/v1/admin/config/business-type/${id}`,
  },
  businessCategory: {
    base: '/v1/admin/config/business-category',
    byId: (id: number | string) => `/v1/admin/config/business-category/${id}`,
  },
  weekdays: {
    base: '/v1/admin/config/weekday',
  },
  attentionSchedule: {
    base: '/v1/admin/config/attention-schedule',
    byId: (id: number | string) => `/v1/admin/config/attention-schedule/${id}`,
  },
  taxTypes: {
    base: '/v1/admin/config/tax-type',
    byId: (id: number | string) => `/v1/admin/config/tax-type/${id}`,
  },
  units: {
    base: '/v1/admin/config/unit',
    byId: (id: number | string) => `/v1/admin/config/unit/${id}`,
  },
  docTypes: {
    base: '/v1/admin/config/doc-type',
    byId: (id: number | string) => `/v1/admin/config/doc-type/${id}`,
  },
  expenseCategories: {
    base: '/v1/admin/config/expense-category',
    byId: (id: number | string) => `/v1/admin/config/expense-category/${id}`,
  },
  paymentTemplates: {
    base: '/v1/admin/config/payment-template',
    byId: (id: number | string) => `/v1/admin/config/payment-template/${id}`,
  },
  identificationTypes: {
    base: '/v1/admin/config/document-id-type',
    byId: (id: string) => `/v1/admin/config/document-id-type/${id}`,
  },
}

export const ADMIN_USERS = {
  base: '/v1/admin/users',
  byId: (id: string) => `/v1/admin/users/${id}`,
  resendReset: (id: string) => `/v1/admin/users/${id}/resend-reset`,
  activate: (id: string) => `/v1/admin/users/${id}/activate`,
  deactivate: (id: string) => `/v1/admin/users/${id}/deactivate`,
  deactivateCompany: (id: string) => `/v1/admin/users/${id}/deactivate-company`,
  assignNewAdmin: (id: string) => `/v1/admin/users/${id}/assign-new-admin`,
  setPassword: (id: string) => `/v1/admin/users/${id}/set-password`,
}
