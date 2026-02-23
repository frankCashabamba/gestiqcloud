import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type TipoDocumento = {
  id: number
  code: string
  name: string
  description: string
  active: boolean
}

type TipoDocumentoPayload = Pick<TipoDocumento, 'code' | 'name' | 'description' | 'active'>

const normalizeTipoDocumento = (input: Partial<TipoDocumento>): TipoDocumento => ({
  id: input.id ?? 0,
  code: input.code ?? '',
  name: input.name ?? '',
  description: input.description ?? '',
  active: input.active ?? true,
})

const buildPayload = (payload: TipoDocumentoPayload) => ({
  code: payload.code,
  name: payload.name,
  description: payload.description,
  active: payload.active,
})

export async function listTiposDocumento(): Promise<TipoDocumento[]> {
  const { data } = await api.get<Partial<TipoDocumento>[]>(`${ADMIN_CONFIG.docTypes.base}`)
  return (data || []).map(normalizeTipoDocumento)
}

export async function getTipoDocumento(id: number | string): Promise<TipoDocumento> {
  try {
    const { data } = await api.get<Partial<TipoDocumento>>(ADMIN_CONFIG.docTypes.byId(id))
    return normalizeTipoDocumento(data || {})
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404 || status === 405) {
      const list = await listTiposDocumento()
      const found = list.find((m) => String(m.id) === String(id))
      if (found) return found
    }
    throw err
  }
}

export async function createTipoDocumento(payload: TipoDocumentoPayload): Promise<TipoDocumento> {
  const { data } = await api.post<Partial<TipoDocumento>>(`${ADMIN_CONFIG.docTypes.base}`, buildPayload(payload))
  return normalizeTipoDocumento(data || payload)
}

export async function updateTipoDocumento(id: number | string, payload: TipoDocumentoPayload): Promise<TipoDocumento> {
  const { data } = await api.put<Partial<TipoDocumento>>(ADMIN_CONFIG.docTypes.byId(id), buildPayload(payload))
  return normalizeTipoDocumento(data || payload)
}

export async function removeTipoDocumento(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.docTypes.byId(id))
}
