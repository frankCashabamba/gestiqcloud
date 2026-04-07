const MODULE_FOLDER_BY_KEY: Record<string, string> = {
  accounting: 'accounting',
  copilot: 'copilot',
  crm: 'crm',
  customers: 'customers',
  einvoicing: 'einvoicing',
  expenses: 'expenses',
  finance: 'finances',
  historical: 'historical',
  hr: 'hr',
  imports: 'importador',
  inventory: 'inventory',
  invoicing: 'billing',
  manufacturing: 'productions',
  notifications: 'notifications',
  pos: 'pos',
  products: 'products',
  purchases: 'purchases',
  reconciliation: 'reconciliation',
  reports: 'reports',
  sales: 'sales',
  settings: 'settings',
  suppliers: 'suppliers',
  templates: 'templates',
  users: 'users',
  webhooks: 'webhooks',
}

export function normalizeCompanyModuleKey(value: string): string {
  return (value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '')
}

export function canonicalizeCompanyModuleKey(value: string): string {
  return normalizeCompanyModuleKey(value)
}

export function getCompanyModuleFolder(value: string): string {
  const canonical = canonicalizeCompanyModuleKey(value)
  return MODULE_FOLDER_BY_KEY[canonical] || canonical
}

export function hasCompanyModuleEnabled(enabledModules: string[], moduleKey: string): boolean {
  const requested = canonicalizeCompanyModuleKey(moduleKey)
  return enabledModules.some((enabled) => canonicalizeCompanyModuleKey(enabled) === requested)
}
