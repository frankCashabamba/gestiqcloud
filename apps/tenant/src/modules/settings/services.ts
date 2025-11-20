import tenantApi from '../../shared/api/client'
import { TENANT_SETTINGS } from '@shared/endpoints'
import type { SettingsGeneral, SettingsBranding, SettingsFiscal, SettingsHorarios, SettingsLimites } from './types'

export async function getGeneral(): Promise<SettingsGeneral> {
  const { data } = await tenantApi.get<SettingsGeneral>(TENANT_SETTINGS.general)
  return data || {}
}
export async function saveGeneral(payload: SettingsGeneral) {
  await tenantApi.put(TENANT_SETTINGS.general, payload)
}

export async function getBranding(): Promise<SettingsBranding> {
  const { data } = await tenantApi.get<SettingsBranding>(TENANT_SETTINGS.branding)
  return data || {}
}
export async function saveBranding(payload: SettingsBranding) {
  await tenantApi.put(TENANT_SETTINGS.branding, payload)
}

export async function getFiscal(): Promise<SettingsFiscal> {
  const { data } = await tenantApi.get<SettingsFiscal>(TENANT_SETTINGS.fiscal)
  return data || {}
}
export async function saveFiscal(payload: SettingsFiscal) {
  await tenantApi.put(TENANT_SETTINGS.fiscal, payload)
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
