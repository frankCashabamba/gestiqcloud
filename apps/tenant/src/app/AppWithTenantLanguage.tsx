/**
 * Wrapper component que aplica automáticamente el idioma configurado en el tenant
 * Debe estar dentro de CompanyConfigProvider y después de AuthProvider
 */

import React, { ReactNode } from 'react'
import { useTenantLanguage } from '../i18n/useTenantLanguage'

interface AppWithTenantLanguageProps {
  children: ReactNode
}

export function AppWithTenantLanguage({ children }: AppWithTenantLanguageProps) {
  // Usar el hook para aplicar idioma del tenant automáticamente
  useTenantLanguage()

  return <>{children}</>
}
