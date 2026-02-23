import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type MetodoPagoPlantilla = {
  id: number
  code: string
  name: string
  description: string
  active: boolean
}

type MetodoPagoPlantillaPayload = Pick<MetodoPagoPlantilla, 'code' | 'name' | 'description' | 'active'>

const normalizeMetodoPagoPlantilla = (input: Partial<MetodoPagoPlantilla>): MetodoPagoPlantilla => ({
  id: input.id ?? 0,
  code: input.code ?? '',
  name: input.name ?? '',
  description: input.description ?? '',
  active: input.active ?? true,
})

const buildPayload = (payload: MetodoPagoPlantillaPayload) => ({
  code: payload.code,
  name: payload.name,
  description: payload.description,
  active: payload.active,
})

export async function listMetodosPago(): Promise<MetodoPagoPlantilla[]> {
  const { data } = await api.get<Partial<MetodoPagoPlantilla>[]>(`${ADMIN_CONFIG.paymentTemplates.base}`)
  return (data || []).map(normalizeMetodoPagoPlantilla)
}

export async function getMetodoPago(id: number | string): Promise<MetodoPagoPlantilla> {
  try {
    const { data } = await api.get<Partial<MetodoPagoPlantilla>>(ADMIN_CONFIG.paymentTemplates.byId(id))
    return normalizeMetodoPagoPlantilla(data || {})
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404 || status === 405) {
      const list = await listMetodosPago()
      const found = list.find((m) => String(m.id) === String(id))
      if (found) return found
    }
    throw err
  }
}

export async function createMetodoPago(payload: MetodoPagoPlantillaPayload): Promise<MetodoPagoPlantilla> {
  const { data } = await api.post<Partial<MetodoPagoPlantilla>>(`${ADMIN_CONFIG.paymentTemplates.base}`, buildPayload(payload))
  return normalizeMetodoPagoPlantilla(data || payload)
}

export async function updateMetodoPago(id: number | string, payload: MetodoPagoPlantillaPayload): Promise<MetodoPagoPlantilla> {
  const { data } = await api.put<Partial<MetodoPagoPlantilla>>(ADMIN_CONFIG.paymentTemplates.byId(id), buildPayload(payload))
  return normalizeMetodoPagoPlantilla(data || payload)
}

export async function removeMetodoPago(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.paymentTemplates.byId(id))
}
