import React, { PropsWithChildren } from 'react'
import { CompanyConfigProvider, useCompanyConfig } from './CompanyConfigContext'

/**
 * Compat wrapper kept for modules that still depend on CompanyContext.
 * It proxies data from CompanyConfigContext so legacy imports keep working.
 */
export function CompanyProvider({ children }: PropsWithChildren<{}>) {
  return <CompanyConfigProvider>{children}</CompanyConfigProvider>
}

export function useCompany() {
  const { sector, config, loading, reload } = useCompanyConfig()
  return { sector, config, loading, reload }
}

export default CompanyProvider
