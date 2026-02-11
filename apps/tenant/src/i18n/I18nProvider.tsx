import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import i18n, { normalizeLang } from './index'

type Dict = Record<string, any>

type I18nContextType = {
  lang: string
  setLang: (lng: string) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextType | null>(null)

// Load JSON dictionaries lazily
const localeModules = import.meta.glob('../locales/*/*.json')
const plantillaModules = import.meta.glob('../plantillas/locales/*.json')

function getNsAndKey(key: string): [string, string] {
  const i = key.indexOf(':')
  if (i === -1) return ['common', key]
  return [key.slice(0, i), key.slice(i + 1)]
}

export const I18nProvider: React.FC<{ defaultLang?: string; children: React.ReactNode }>= ({ defaultLang = 'en', children }) => {
  const [lang, setLangState] = useState(() => normalizeLang(i18n.resolvedLanguage || i18n.language || defaultLang))
  const [dicts, setDicts] = useState<Record<string, Dict>>({})

  useEffect(() => {
    const handler = (lng: string) => setLangState(normalizeLang(lng))
    i18n.on('languageChanged', handler)
    return () => {
      i18n.off('languageChanged', handler)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadAll() {
      const loaded: Record<string, Dict> = {}

      // Namespaces bajo /i18n/locales/{lang}/ns.json  => ns
      const entries = Object.entries(localeModules).filter(([path]) => path.includes(`/${lang}/`))
      for (const [path, importer] of entries) {
        try {
          const mod: any = await (importer as any)()
          const ns = path.split('/').slice(-1)[0].replace('.json', '')
          loaded[ns] = mod?.default?.[ns] ?? mod?.default ?? mod
        } catch {}
      }

      // Plantillas: archivos tipo retail-dashboard.es.json => ns retailDashboard, lang es
      for (const [path, importer] of Object.entries(plantillaModules)) {
        const filename = path.split('/').slice(-1)[0] // retail-dashboard.es.json
        const parts = filename.split('.')
        if (parts.length < 3) continue
        const [, langCode] = [parts.slice(0, -2).join('.'), parts.slice(-2, -1)[0]]
        if (normalizeLang(langCode) !== lang) continue
        const nsRaw = parts.slice(0, -2).join('.')
        const ns = nsRaw.replace(/-([a-z])/g, (_, c) => c.toUpperCase())
        try {
          const mod: any = await (importer as any)()
          loaded[ns] = mod?.default?.[ns] ?? mod?.default ?? mod
        } catch {}
      }

      if (!cancelled) setDicts(loaded)
      try { document.documentElement.lang = lang } catch {}
    }
    loadAll()
    return () => { cancelled = true }
  }, [lang])

  const setLang = useCallback((lng: string) => {
    const normalized = normalizeLang(lng)
    i18n.changeLanguage(normalized)
  }, [])

  const t = useCallback((key: string, vars?: Record<string, string | number>) => {
    const [ns, k] = getNsAndKey(key)
    const d = dicts[ns] || {}
    const raw = k.split('.').reduce<any>((acc, part) => (acc ? acc[part] : undefined), d)
    let str = typeof raw === 'string' ? raw : key
    if (vars) {
      for (const [vk, vv] of Object.entries(vars)) {
        str = str.replace(new RegExp(`{{\\s*${vk}\\s*}}`, 'g'), String(vv))
      }
    }
    return str
  }, [dicts])

  const value = useMemo<I18nContextType>(() => ({ lang, setLang, t }), [lang, setLang, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
