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
