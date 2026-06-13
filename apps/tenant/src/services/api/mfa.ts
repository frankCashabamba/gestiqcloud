import api from '../../shared/api/client'
import { TENANT_MFA } from '@shared/endpoints'

const BASE = TENANT_MFA.base

export interface MFAStatus {
  mfa_enabled: boolean
}

export interface MFASetupResponse {
  totp_uri: string
  recovery_codes: string[]
}

export interface MFAVerifyPayload {
  code: string
}

export async function getMFAStatus(): Promise<MFAStatus> {
  const { data } = await api.get<MFAStatus>(`${BASE}/status`)
  return data
}

export async function setupMFA(): Promise<MFASetupResponse> {
  const { data } = await api.post<MFASetupResponse>(`${BASE}/setup`)
  return data
}

export async function verifyMFA(payload: MFAVerifyPayload): Promise<void> {
  await api.post(`${BASE}/verify`, payload)
}

export async function disableMFA(): Promise<void> {
  await api.delete(`${BASE}/disable`)
}
