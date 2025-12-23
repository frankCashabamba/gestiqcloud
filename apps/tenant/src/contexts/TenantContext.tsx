import React, { PropsWithChildren } from 'react'
import { TenantConfigProvider, useTenantConfig } from './TenantConfigContext'

/**
 * Compat wrapper kept for modules that still depend on TenantContext.
 * It proxies data from TenantConfigContext so legacy imports keep working.
 */
export function TenantProvider({ children }: PropsWithChildren<{}>) {
  return <TenantConfigProvider>{children}</TenantConfigProvider>
}

export function useTenant() {
  const { sector, config, loading, reload } = useTenantConfig()
  return { sector, config, loading, reload }
}

export default TenantProvider
