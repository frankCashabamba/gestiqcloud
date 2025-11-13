import api from '../../shared/api/client'

// === CAJA ===
export async function listCajas(params?: {
  page?: number
  pageSize?: number
  registerId?: string
  [key: string]: any
}) {
  const response = await api.get('/api/v1/finanzas/cajas', { params })
  return response.data
}

export async function createCaja(data: any) {
  const response = await api.post('/api/v1/finanzas/cajas', data)
  return response.data
}

export async function getCaja(id: string) {
  const response = await api.get(`/api/v1/finanzas/cajas/${id}`)
  return response.data
}

export async function getSaldoCaja(id: string) {
  const response = await api.get(`/api/v1/finanzas/cajas/${id}/saldo`)
  return response.data
}

export async function cerrarCaja(id: string, data: any) {
  const response = await api.post(`/api/v1/finanzas/cajas/${id}/cerrar`, data)
  return response.data
}

// === BANCO ===
export async function listCuentasBanco(params?: {
  page?: number
  pageSize?: number
  [key: string]: any
}) {
  const response = await api.get('/api/v1/finanzas/cuentas-banco', { params })
  return response.data
}

export async function createCuentaBanco(data: any) {
  const response = await api.post('/api/v1/finanzas/cuentas-banco', data)
  return response.data
}

export async function getCuentaBanco(id: string) {
  const response = await api.get(`/api/v1/finanzas/cuentas-banco/${id}`)
  return response.data
}

export async function conciliarBanco(id: string, data: any) {
  const response = await api.post(`/api/v1/finanzas/cuentas-banco/${id}/conciliar`, data)
  return response.data
}

export async function getSaldosBanco(params?: {
  date?: string
}) {
  const response = await api.get('/api/v1/finanzas/cuentas-banco/saldos', { params })
  return response.data
}
