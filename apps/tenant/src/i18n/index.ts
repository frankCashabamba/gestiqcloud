import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

type BuiltInLang = 'en' | 'es'
const BUILTIN_LANGS: BuiltInLang[] = ['en', 'es']
const coreLocaleModules = import.meta.glob('./locales/*.json')
const namespaceLocaleModules = import.meta.glob('../locales/*/*.json')
const loadedLanguages = new Set<BuiltInLang>()
const inflightLoads = new Map<BuiltInLang, Promise<void>>()

const NS = [
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
  'reports',
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
  'dashboard',
] as const

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

async function loadCoreTranslation(lang: SupportedLang) {
  const path = `./locales/${lang}.json`
  const importer = coreLocaleModules[path]
  if (!importer) return
  const mod = await (importer as () => Promise<any>)()
  i18n.addResourceBundle(lang, 'translation', mod.default ?? mod, true, true)
}

async function loadNamedNamespaces(lang: SupportedLang) {
  const entries = Object.entries(namespaceLocaleModules).filter(([path]) =>
    path.includes(`../locales/${lang}/`),
  )

  await Promise.all(
    entries.map(async ([path, importer]) => {
      const fileName = path.split('/').pop() || ''
      const namespace = fileName.replace(/\.json$/, '')
      const mod = await (importer as () => Promise<any>)()
      i18n.addResourceBundle(lang, namespace, mod.default ?? mod, true, true)
    }),
  )
}

export async function ensureLanguageResources(lang: SupportedLang): Promise<void> {
  const normalized = normalizeLang(lang)
  if (loadedLanguages.has(normalized)) return

  const existing = inflightLoads.get(normalized)
  if (existing) return existing

  const promise = (async () => {
    await Promise.all([loadCoreTranslation(normalized), loadNamedNamespaces(normalized)])
    loadedLanguages.add(normalized)
    inflightLoads.delete(normalized)
  })().catch((error) => {
    inflightLoads.delete(normalized)
    throw error
  })

  inflightLoads.set(normalized, promise)
  return promise
}

export async function changeAppLanguage(lang: string): Promise<SupportedLang> {
  const normalized = normalizeLang(lang)
  await ensureLanguageResources(normalized)
  if (i18n.resolvedLanguage !== normalized) {
    await i18n.changeLanguage(normalized)
  }
  return normalized
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    ns: [...NS],
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
