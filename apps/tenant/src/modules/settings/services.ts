import tenantApi from '../../shared/api/client'
import { TENANT_SETTINGS } from '@shared/endpoints'
import type { SettingsGeneral, SettingsBranding, SettingsFiscal, SettingsHorarios, SettingsLimites } from './types'

export async function getGeneral(): Promise<SettingsGeneral> {
  const { data } = await tenantApi.get<any>(TENANT_SETTINGS.general)
  return {
    razon_social: data?.company_name || data?.razon_social || data?.name || '',
    tax_id: data?.tax_id || data?.ruc || '',
    address: data?.address || data?.direccion || '',
  }
}
export async function saveGeneral(payload: SettingsGeneral) {
  await tenantApi.put(TENANT_SETTINGS.general, {
    company_name: payload.razon_social,
    tax_id: payload.tax_id || payload.ruc,
    address: payload.address || payload.direccion,
  })
}

export async function getBranding(): Promise<SettingsBranding> {
  const { data } = await tenantApi.get<SettingsBranding>(TENANT_SETTINGS.branding)
  return data || {}
}
export async function saveBranding(payload: SettingsBranding) {
  await tenantApi.put(TENANT_SETTINGS.branding, payload)
}

export async function getFiscal(): Promise<SettingsFiscal> {
  const { data } = await tenantApi.get<any>(TENANT_SETTINGS.fiscal)
  return {
    regimen: data?.tax_regime || data?.regimen || '',
    iva: typeof data?.iva === 'number' ? data.iva : 0,
  }
}
export async function saveFiscal(payload: SettingsFiscal) {
  await tenantApi.put(TENANT_SETTINGS.fiscal, {
    tax_regime: payload.regimen,
    iva: payload.iva,
  })
}

export async function getHorarios(): Promise<SettingsHorarios> {
  const { data } = await tenantApi.get<SettingsHorarios>(TENANT_SETTINGS.horarios)
  return data || {}
}
export async function saveHorarios(payload: SettingsHorarios) {
  await tenantApi.put(TENANT_SETTINGS.horarios, payload)
}

export async function getLimites(): Promise<SettingsLimites> {
  const { data } = await tenantApi.get<SettingsLimites>(TENANT_SETTINGS.limites)
  return data || {}
}
export async function saveLimites(payload: SettingsLimites) {
  await tenantApi.put(TENANT_SETTINGS.limites, payload)
}
