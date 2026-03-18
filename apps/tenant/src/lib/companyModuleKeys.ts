const MODULE_KEY_ALIASES: Record<string, string> = {
  ventas: 'sales',
  sales: 'sales',
  productos: 'products',
  products: 'products',
  clientes: 'customers',
  customers: 'customers',
  clients: 'customers',
  proveedores: 'suppliers',
  suppliers: 'suppliers',
  inventario: 'inventory',
  inventory: 'inventory',
  facturacion: 'invoicing',
  invoicing: 'invoicing',
  billing: 'invoicing',
  reportes: 'reports',
  reports: 'reports',
  configuracion: 'settings',
  settings: 'settings',
  usuarios: 'users',
  users: 'users',
  pos: 'pos',
  tpv: 'pos',
  contabilidad: 'accounting',
  accounting: 'accounting',
  compras: 'purchases',
  purchases: 'purchases',
  gastos: 'expenses',
  expenses: 'expenses',
  rrhh: 'hr',
  hr: 'hr',
  importador: 'imports',
  importer: 'imports',
  imports: 'imports',
  importaciones: 'imports',
  produccion: 'manufacturing',
  production: 'manufacturing',
  productions: 'manufacturing',
  manufacturing: 'manufacturing',
  finanzas: 'finance',
  finance: 'finance',
  finances: 'finance',
  webhooks: 'webhooks',
  reconciliation: 'reconciliation',
  conciliacion: 'reconciliation',
  conciliacionbancaria: 'reconciliation',
  templates: 'templates',
}

const MODULE_FOLDER_BY_KEY: Record<string, string> = {
  accounting: 'accounting',
  copilot: 'copilot',
  crm: 'crm',
  customers: 'customers',
  einvoicing: 'einvoicing',
  expenses: 'expenses',
  finance: 'finances',
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
  const normalized = normalizeCompanyModuleKey(value)
  return MODULE_KEY_ALIASES[normalized] || normalized
}

export function getCompanyModuleFolder(value: string): string {
  const canonical = canonicalizeCompanyModuleKey(value)
  return MODULE_FOLDER_BY_KEY[canonical] || canonical
}

export function hasCompanyModuleEnabled(enabledModules: string[], moduleKey: string): boolean {
  const requested = canonicalizeCompanyModuleKey(moduleKey)
  return enabledModules.some((enabled) => canonicalizeCompanyModuleKey(enabled) === requested)
}
