export const ADMIN_AUTH = {
  login: '/api/v1/admin/auth/login',
  refresh: '/api/v1/admin/auth/refresh',
  csrf: '/api/v1/admin/auth/csrf',
  logout: '/api/v1/admin/auth/logout',
}

export const ADMIN_MODULES = {
  public: '/api/v1/admin/modules/public',
  base: '/api/v1/admin/modules',
  byId: (id: number | string) => `/api/v1/admin/modules/${id}`,
  byIdForce: (id: number | string) => `/api/v1/admin/modules/${id}?force=true`,
  activate: (id: number | string) => `/api/v1/admin/modules/${id}/activate`,
  deactivate: (id: number | string) => `/api/v1/admin/modules/${id}/deactivate`,
  register: '/api/v1/admin/modules/register-modules',
}

export const ADMIN_COMPANIES = {
  base: '/api/v1/admin/companies',
  createFull: '/api/v1/admin/companies/full-json',
  deleteAll: '/api/v1/admin/companies/bulk/delete-all',
  purgeOrphans: '/api/v1/admin/companies/purge-orphans',
  byId: (id: number | string) => `/api/v1/admin/companies/${id}`,
}

export const ADMIN_COMPANY_MODULES = {
  base: (tenantId: number | string) => `/api/v1/admin/modules/company/${tenantId}`,
  upsert: (tenantId: number | string) => `/api/v1/admin/modules/company/${tenantId}/upsert`,
  remove: (tenantId: number | string, moduleId: number | string) => `/api/v1/admin/modules/company/${tenantId}/module/${moduleId}`,
}

export const ADMIN_CONFIG = {
  currencies: {
    base: '/api/v1/admin/config/currency',
    byId: (id: number | string) => `/api/v1/admin/config/currency/${id}`,
  },
  countries: {
    base: '/api/v1/admin/config/country',
    byId: (id: number | string) => `/api/v1/admin/config/country/${id}`,
  },
  timezones: {
    base: '/api/v1/admin/config/timezone',
    byId: (name: string) => `/api/v1/admin/config/timezone/${encodeURIComponent(name)}`,
  },
  locales: {
    base: '/api/v1/admin/config/locale',
    byId: (code: string) => `/api/v1/admin/config/locale/${encodeURIComponent(code)}`,
  },
  languages: {
    base: '/api/v1/admin/config/language',
    byId: (id: number | string) => `/api/v1/admin/config/language/${id}`,
  },
  sectors: {
    base: '/api/v1/admin/config/template-sector',
    byId: (id: number | string) => `/api/v1/admin/config/template-sector/${id}`,
  },
  businessType: {
    base: '/api/v1/admin/config/business-type',
    byId: (id: number | string) => `/api/v1/admin/config/business-type/${id}`,
  },
  businessCategory: {
    base: '/api/v1/admin/config/business-category',
    byId: (id: number | string) => `/api/v1/admin/config/business-category/${id}`,
  },
  weekdays: {
    base: '/api/v1/admin/config/weekday',
  },
  attentionSchedule: {
    base: '/api/v1/admin/config/attention-schedule',
    byId: (id: number | string) => `/api/v1/admin/config/attention-schedule/${id}`,
  },
  taxTypes: {
    base: '/api/v1/admin/config/tax-type',
    byId: (id: number | string) => `/api/v1/admin/config/tax-type/${id}`,
  },
  units: {
    base: '/api/v1/admin/config/unit',
    byId: (id: number | string) => `/api/v1/admin/config/unit/${id}`,
  },
  docTypes: {
    base: '/api/v1/admin/config/doc-type',
    byId: (id: number | string) => `/api/v1/admin/config/doc-type/${id}`,
  },
  expenseCategories: {
    base: '/api/v1/admin/config/expense-category',
    byId: (id: number | string) => `/api/v1/admin/config/expense-category/${id}`,
  },
  paymentTemplates: {
    base: '/api/v1/admin/config/payment-template',
    byId: (id: number | string) => `/api/v1/admin/config/payment-template/${id}`,
  },
  identificationTypes: {
    base: '/api/v1/admin/config/document-id-type',
    byId: (id: string) => `/api/v1/admin/config/document-id-type/${id}`,
  },
  payrollParams: {
    base: '/api/v1/admin/config/payroll-params',
    byCountryYear: (country: string, year: number) =>
      `/api/v1/admin/config/payroll-params/${country}/${year}`,
  },
  systemDefaults: {
    base: '/api/v1/admin/config/system-defaults',
    byKey: (key: string) => `/api/v1/admin/config/system-defaults/${key}`,
  },
}

export const ADMIN_USERS = {
  base: '/api/v1/admin/users',
  byId: (id: string) => `/api/v1/admin/users/${id}`,
  resendReset: (id: string) => `/api/v1/admin/users/${id}/resend-reset`,
  activate: (id: string) => `/api/v1/admin/users/${id}/activate`,
  deactivate: (id: string) => `/api/v1/admin/users/${id}/deactivate`,
  deactivateCompany: (id: string) => `/api/v1/admin/users/${id}/deactivate-company`,
  assignNewAdmin: (id: string) => `/api/v1/admin/users/${id}/assign-new-admin`,
  setPassword: (id: string) => `/api/v1/admin/users/${id}/set-password`,
}
