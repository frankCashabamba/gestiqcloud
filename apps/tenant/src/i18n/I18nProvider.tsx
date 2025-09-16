import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

type Dict = Record<string, any>

type I18nContextType = {
  lang: string
  setLang: (lng: string) => void
  t: (key: string, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextType | null>(null)

// Load all JSON dictionaries for a language lazily
const localeModules = import.meta.glob('../locales/*/*.json')

function getNsAndKey(key: string): [string, string] {
  const i = key.indexOf(':')
  if (i === -1) return ['common', key]
  return [key.slice(0, i), key.slice(i + 1)]
}

export const I18nProvider: React.FC<{ defaultLang?: string; children: React.ReactNode }>= ({ defaultLang = 'es', children }) => {
  const [lang, setLang] = useState(defaultLang)
  const [dicts, setDicts] = useState<Record<string, Dict>>({})

  useEffect(() => {
    let cancelled = false
    async function loadAll() {
      // Load all namespaces for current lang
      const entries = Object.entries(localeModules)
        .filter(([path]) => path.includes(`/${lang}/`))
      const loaded: Record<string, Dict> = {}
      for (const [path, importer] of entries) {
        try {
          const mod: any = await (importer as any)()
          const ns = path.split('/').slice(-1)[0].replace('.json', '')
          loaded[ns] = mod?.default || mod
        } catch {}
      }
      if (!cancelled) setDicts(loaded)
      try { document.documentElement.lang = lang } catch {}
    }
    loadAll()
    return () => { cancelled = true }
  }, [lang])

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

  const value = useMemo<I18nContextType>(() => ({ lang, setLang, t }), [lang, t])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}

