import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import es from './locales/es.json'
import commonEn from '../locales/en/common.json'
import commonEs from '../locales/es/common.json'
import importerEn from '../locales/en/importer.json'
import importerEs from '../locales/es/importer.json'
import crmEn from '../locales/en/crm.json'
import crmEs from '../locales/es/crm.json'
import customersEn from '../locales/en/customers.json'
import customersEs from '../locales/es/customers.json'
import expensesEn from '../locales/en/expenses.json'
import expensesEs from '../locales/es/expenses.json'
import financesEn from '../locales/en/finances.json'
import financesEs from '../locales/es/finances.json'
import inventoryEn from '../locales/en/inventory.json'
import inventoryEs from '../locales/es/inventory.json'
import permissionsEn from '../locales/en/permissions.json'
import permissionsEs from '../locales/es/permissions.json'
import posEn from '../locales/en/pos.json'
import posEs from '../locales/es/pos.json'
import productsEn from '../locales/en/products.json'
import productsEs from '../locales/es/products.json'
import reportesEn from '../locales/en/reportes.json'
import reportesEs from '../locales/es/reportes.json'
import settingsEn from '../locales/en/settings.json'
import settingsEs from '../locales/es/settings.json'
import suppliersEn from '../locales/en/suppliers.json'
import suppliersEs from '../locales/es/suppliers.json'
import costingEn from '../locales/en/costing.json'
import costingEs from '../locales/es/costing.json'
import hrEn from '../locales/en/hr.json'
import hrEs from '../locales/es/hr.json'
import copilotEn from '../locales/en/copilot.json'
import copilotEs from '../locales/es/copilot.json'
import einvoicingEn from '../locales/en/einvoicing.json'
import einvoicingEs from '../locales/es/einvoicing.json'
import notificationsEn from '../locales/en/notifications.json'
import notificationsEs from '../locales/es/notifications.json'
import reconciliationEn from '../locales/en/reconciliation.json'
import reconciliationEs from '../locales/es/reconciliation.json'
import purchasesEn from '../locales/en/purchases.json'
import purchasesEs from '../locales/es/purchases.json'
import usersEn from '../locales/en/users.json'
import usersEs from '../locales/es/users.json'
import templatesEn from '../locales/en/templates.json'
import templatesEs from '../locales/es/templates.json'
import productionsEn from '../locales/en/productions.json'
import productionsEs from '../locales/es/productions.json'

type BuiltInLang = 'en' | 'es'
const BUILTIN_LANGS: BuiltInLang[] = ['en', 'es']

function parseSupportedLangs(raw?: string | null): BuiltInLang[] {
  if (!raw) return BUILTIN_LANGS
  const parsed = raw
    .split(',')
    .map((v) => v.trim().toLowerCase())
    .filter((v): v is BuiltInLang => v === 'en' || v === 'es')
  return parsed.length > 0 ? parsed : BUILTIN_LANGS
}

export const SUPPORTED_LANGS = parseSupportedLangs((import.meta as any)?.env?.VITE_SUPPORTED_LANGS)
export type SupportedLang = BuiltInLang

export function normalizeLang(value?: string | null): SupportedLang {
  const raw = (value || '').trim().toLowerCase()
  const base = raw.split(/[-_]/)[0]
  if (base === 'es') return 'es'
  return 'en'
}

const resources = {
  en: {
    translation: en,
    common: commonEn,
    crm: crmEn,
    customers: customersEn,
    expenses: expensesEn,
    finances: financesEn,
    importer: importerEn,
    inventory: inventoryEn,
    permissions: permissionsEn,
    pos: posEn,
    products: productsEn,
    reportes: reportesEn,
    settings: settingsEn,
    suppliers: suppliersEn,
    costing: costingEn,
    hr: hrEn,
    copilot: copilotEn,
    einvoicing: einvoicingEn,
    notifications: notificationsEn,
    reconciliation: reconciliationEn,
    purchases: purchasesEn,
    users: usersEn,
    templates: templatesEn,
    productions: productionsEn,
  },
  es: {
    translation: es,
    common: commonEs,
    crm: crmEs,
    customers: customersEs,
    expenses: expensesEs,
    finances: financesEs,
    importer: importerEs,
    inventory: inventoryEs,
    permissions: permissionsEs,
    pos: posEs,
    products: productsEs,
    reportes: reportesEs,
    settings: settingsEs,
    suppliers: suppliersEs,
    costing: costingEs,
    hr: hrEs,
    copilot: copilotEs,
    einvoicing: einvoicingEs,
    notifications: notificationsEs,
    reconciliation: reconciliationEs,
    purchases: purchasesEs,
    users: usersEs,
    templates: templatesEs,
    productions: productionsEs,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    ns: [
      'translation',
      'common',
      'crm',
      'customers',
      'expenses',
      'finances',
      'importer',
      'inventory',
      'permissions',
      'pos',
      'products',
      'reportes',
      'settings',
      'suppliers',
      'costing',
      'hr',
      'copilot',
      'einvoicing',
      'notifications',
      'reconciliation',
      'purchases',
      'users',
      'templates',
      'productions',
    ],
    defaultNS: 'translation',
    fallbackNS: ['common'],
    supportedLngs: [...SUPPORTED_LANGS],
    nonExplicitSupportedLngs: true,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  })

export default i18n
