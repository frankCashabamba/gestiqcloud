/**
 * Hook para obtener el idioma configurado en la empresa (tenant)
 * y aplicarlo a i18n automáticamente
 */

import { useEffect } from 'react'
import { useCompanyConfig } from '../contexts/CompanyConfigContext'
import { normalizeLang } from './index'
import i18n from './index'
import type { SupportedLang } from './index'

export function useTenantLanguage(): SupportedLang {
  const { config, loading } = useCompanyConfig()

  // Obtener idioma de la configuración del tenant
  const tenantLocale = config?.settings?.locale

  useEffect(() => {
    if (loading || !tenantLocale) return

    const normalized = normalizeLang(tenantLocale)

    // Solo cambiar si es diferente al idioma actual
    if (i18n.language !== normalized) {
      i18n.changeLanguage(normalized).catch(err => {
        console.warn(`Failed to change language to ${normalized}:`, err)
      })
    }
  }, [tenantLocale, loading])

  // Return current language or fallback
  return (normalizeLang(i18n.resolvedLanguage || i18n.language) || 'en') as SupportedLang
}
