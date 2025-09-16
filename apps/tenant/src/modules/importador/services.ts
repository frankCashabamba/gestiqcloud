import { API_URL } from '../../lib/http'
import { apiFetch } from '../../lib/http'

export type DatosImportadosCreate = {
  tipo: string
  origen: 'excel' | 'ocr' | 'manual'
  datos: Record<string, any>
  estado?: string
  hash?: string | null
}

export type DatosImportadosOut = DatosImportadosCreate & { id: number; empresa_id: number }

export async function procesarDocumento(file: File, authToken?: string) {
  const url = `${API_URL}/v1/imports/procesar`
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(url, {
    method: 'POST',
    body: fd,
    headers: authToken ? { Authorization: `Bearer ${authToken}` } as any : undefined,
    credentials: 'include',
  })
  const txt = await res.text()
  const json = txt ? JSON.parse(txt) : null
  if (!res.ok) {
    const msg = (json && (json.detail || json.message)) || res.statusText
    throw new Error(msg)
  }
  return json as { archivo: string; documentos: any[] }
}

export async function guardarPendiente(payload: DatosImportadosCreate, authToken?: string) {
  return apiFetch<DatosImportadosOut>('/v1/imports/guardar', { method: 'POST', body: JSON.stringify(payload), authToken })
}

export async function listarPendientes(authToken?: string) {
  return apiFetch<DatosImportadosOut[]>('/v1/imports/listar', { authToken })
}

export async function hayPendientes(authToken?: string) {
  return apiFetch<{ hayPendientes: boolean }>('/v1/imports/hay-pendientes', { authToken })
}

export async function eliminarPendiente(id: number, authToken?: string) {
  return apiFetch<{ ok: boolean }>(`/v1/imports/eliminar/${id}`, { method: 'DELETE', authToken })
}

export async function enviarDocumento(id: number, authToken?: string) {
  return apiFetch(`/v1/imports/enviar/${id}`, { method: 'POST', authToken })
}

export async function actualizarPendiente(id: number, payload: Partial<DatosImportadosCreate>, authToken?: string) {
  return apiFetch<DatosImportadosOut>(`/v1/imports/actualizar/${id}`, { method: 'PUT', body: JSON.stringify(payload), authToken })
}

export async function guardarBatch(payload: DatosImportadosCreate[], authToken?: string) {
  return apiFetch<DatosImportadosOut[]>(`/v1/imports/guardar-batch`, { method: 'POST', body: JSON.stringify(payload), authToken })
}

export async function enviarBatch(ids: number[], authToken?: string) {
  return apiFetch<any>(`/v1/imports/enviar-batch`, { method: 'POST', body: JSON.stringify(ids), authToken })
}
