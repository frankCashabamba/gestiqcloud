import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import es from './locales/es.json'
import posEn from '../locales/en/pos.json'
import posEs from '../locales/es/pos.json'
import commonEn from '../locales/en/common.json'
import commonEs from '../locales/es/common.json'
import importerEn from '../locales/en/importer.json'
import importerEs from '../locales/es/importer.json'

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
    pos: posEn,
    common: commonEn,
    importer: importerEn,
  },
  es: {
    translation: es,
    pos: posEs,
    common: commonEs,
    importer: importerEs,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    ns: ['translation', 'pos', 'common', 'importer'],
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
