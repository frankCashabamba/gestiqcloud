import api from '../../shared/api/client'

// === CAJA ===
export async function listCajas(params?: {
  page?: number
  pageSize?: number
  registerId?: string
  [key: string]: any
}) {
  const response = await api.get('/api/v1/finance/cash-registers', { params })
  return response.data
}

export async function createCaja(data: any) {
  const response = await api.post('/api/v1/finance/cash-registers', data)
  return response.data
}

export async function getCaja(id: string) {
  const response = await api.get(`/api/v1/finance/cash-registers/${id}`)
  return response.data
}

export async function getSaldoCaja(id: string) {
  const response = await api.get(`/api/v1/finance/cash-registers/${id}/balance`)
  return response.data
}

export async function cerrarCaja(id: string, data: any) {
  const response = await api.post(`/api/v1/finance/cash-registers/${id}/close`, data)
  return response.data
}

// === BANCO ===
export async function listCuentasBanco(params?: {
  page?: number
  pageSize?: number
  [key: string]: any
}) {
  const response = await api.get('/api/v1/finance/bank-accounts', { params })
  return response.data
}

export async function createCuentaBanco(data: any) {
  const response = await api.post('/api/v1/finance/bank-accounts', data)
  return response.data
}

export async function getCuentaBanco(id: string) {
  const response = await api.get(`/api/v1/finance/bank-accounts/${id}`)
  return response.data
}

export async function conciliarBanco(id: string, data: any) {
  const response = await api.post(`/api/v1/finance/bank-accounts/${id}/reconcile`, data)
  return response.data
}

export async function getSaldosBanco(params?: {
  date?: string
}) {
  const response = await api.get('/api/v1/finance/bank-accounts/balances', { params })
  return response.data
}
