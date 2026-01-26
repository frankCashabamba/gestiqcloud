import { useCompanyConfig } from '../contexts/CompanyConfigContext'

/**
 * Minimal tenant helper hook derived from CompanyConfigContext.
 * Provides `tenant` object compatible with older hooks expecting sector_code.
 */
export function useTenant() {
  const { config } = useCompanyConfig()
  const tenant = config?.company
    ? {
        ...config.company,
        sector_code: config.sector?.plantilla,
      }
    : null

  return { tenant }
}
