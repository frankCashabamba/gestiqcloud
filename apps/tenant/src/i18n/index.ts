import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import es from './locales/es.json'

export const SUPPORTED_LANGS = ['en', 'es'] as const
export type SupportedLang = (typeof SUPPORTED_LANGS)[number]

export function normalizeLang(value?: string | null): SupportedLang {
  const raw = (value || '').trim().toLowerCase()
  const base = raw.split(/[-_]/)[0]
  if (base === 'es') return 'es'
  return 'en'
}

const resources = {
  en: { translation: en },
  es: { translation: es },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
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
