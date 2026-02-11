import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import es from './locales/es.json'
import posEn from '../locales/en/pos.json'
import posEs from '../locales/es/pos.json'
import commonEn from '../locales/en/common.json'
import commonEs from '../locales/es/common.json'

export const SUPPORTED_LANGS = ['en', 'es'] as const
export type SupportedLang = (typeof SUPPORTED_LANGS)[number]

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
  },
  es: {
    translation: es,
    pos: posEs,
    common: commonEs,
  },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    ns: ['translation', 'pos', 'common'],
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
