import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type CategoriaGasto = {
  id: number
  code: string
  name: string
  parent_code: string
  active: boolean
}

type CategoriaGastoPayload = Pick<CategoriaGasto, 'code' | 'name' | 'parent_code' | 'active'>

const normalizeCategoriaGasto = (input: Partial<CategoriaGasto>): CategoriaGasto => ({
  id: input.id ?? 0,
  code: input.code ?? '',
  name: input.name ?? '',
  parent_code: input.parent_code ?? '',
  active: input.active ?? true,
})

const buildPayload = (payload: CategoriaGastoPayload) => ({
  code: payload.code,
  name: payload.name,
  parent_code: payload.parent_code,
  active: payload.active,
})

export async function listCategoriasGasto(): Promise<CategoriaGasto[]> {
  const { data } = await api.get<Partial<CategoriaGasto>[]>(`${ADMIN_CONFIG.expenseCategories.base}`)
  return (data || []).map(normalizeCategoriaGasto)
}

export async function getCategoriaGasto(id: number | string): Promise<CategoriaGasto> {
  try {
    const { data } = await api.get<Partial<CategoriaGasto>>(ADMIN_CONFIG.expenseCategories.byId(id))
    return normalizeCategoriaGasto(data || {})
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 404 || status === 405) {
      const list = await listCategoriasGasto()
      const found = list.find((m) => String(m.id) === String(id))
      if (found) return found
    }
    throw err
  }
}

export async function createCategoriaGasto(payload: CategoriaGastoPayload): Promise<CategoriaGasto> {
  const { data } = await api.post<Partial<CategoriaGasto>>(`${ADMIN_CONFIG.expenseCategories.base}`, buildPayload(payload))
  return normalizeCategoriaGasto(data || payload)
}

export async function updateCategoriaGasto(id: number | string, payload: CategoriaGastoPayload): Promise<CategoriaGasto> {
  const { data } = await api.put<Partial<CategoriaGasto>>(ADMIN_CONFIG.expenseCategories.byId(id), buildPayload(payload))
  return normalizeCategoriaGasto(data || payload)
}

export async function removeCategoriaGasto(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.expenseCategories.byId(id))
}
