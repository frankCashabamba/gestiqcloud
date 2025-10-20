import { API_URL } from '../../lib/http'
import { apiFetch } from '../../lib/http'

import { getOcrJob } from './services/importsApi'
import type { OcrJobStatus } from './services/importsApi'

const JOB_POLL_INTERVAL_MS = Number(import.meta.env.VITE_IMPORTS_JOB_POLL_INTERVAL ?? 1500)
const JOB_POLL_MAX_ATTEMPTS = Number(import.meta.env.VITE_IMPORTS_JOB_POLL_ATTEMPTS ?? 80)

type OcrJobResultPayload = { archivo: string; documentos: any[] }

export type ProcesarDocumentoResult =
  | { status: 'done'; jobId: string; payload: OcrJobResultPayload }
  | { status: 'pending'; jobId: string }

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export type DatosImportadosCreate = {
  tipo: string
  origen: 'excel' | 'ocr' | 'manual'
  datos: Record<string, any>
  estado?: string
  hash?: string | null
}

export type DatosImportadosOut = DatosImportadosCreate & { id: number; empresa_id: number }


export async function procesarDocumento(file: File, authToken?: string): Promise<ProcesarDocumentoResult> {
  // OCR solo admite PDF/imagenes; bloquea Excel para evitar 422 del backend
  try {
    const name = (file?.name || '').toLowerCase()
    const type = (file?.type || '').toLowerCase()
    const isExcel = name.endsWith('.xlsx') || name.endsWith('.xls') || type.includes('spreadsheetml')
    if (isExcel) {
      throw new Error('Formato Excel (.xlsx/.xls) no soportado por OCR. Exporta a CSV o sube PDF/imagen.')
    }
  } catch {}
  const url = `${API_URL}/v1/imports/procesar`
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(url, {
    method: 'POST',
    body: fd,
    headers: authToken ? { Authorization: `Bearer ${authToken}` } as any : undefined,
    credentials: 'include',
  })

  const raw = await res.text()
  let json: any = null
  if (raw) {
    try {
      json = JSON.parse(raw)
    } catch {
      if (!res.ok) {
        const fallback = res.status === 504
          ? 'El procesamiento tard? m?s de lo permitido (504). Intenta nuevamente o reduce el tama?o del archivo.'
          : `El servidor devolvi? una respuesta inesperada (${res.status}).`
        throw new Error(fallback)
      }
      throw new Error('El servidor devolvi? una respuesta que no es JSON v?lido.')
    }
  }

  if (!res.ok) {
    const msg = json?.detail || json?.message || (res.status === 504
      ? 'El procesamiento tard? m?s de lo permitido (504). Intenta nuevamente o reduce el tama?o del archivo.'
      : res.statusText)
    throw new Error(msg || 'Error procesando el documento.')
  }

  const jobId: string | undefined = json?.job_id
  if (!jobId) {
    throw new Error('No se pudo encolar el procesamiento del documento.')
  }

  const result = await waitForOcrJob(jobId, authToken)
  if (!result) {
    return { status: 'pending', jobId }
  }
  return { status: 'done', jobId, payload: result }
}

export async function pollOcrJob(jobId: string, authToken?: string): Promise<ProcesarDocumentoResult> {
  const result = await waitForOcrJob(jobId, authToken)
  if (!result) {
    return { status: 'pending', jobId }
  }
  return { status: 'done', jobId, payload: result }
}

async function waitForOcrJob(jobId: string, authToken?: string): Promise<OcrJobResultPayload | null> {
  let lastStatus: OcrJobStatus | null = null
  for (let attempt = 0; attempt < JOB_POLL_MAX_ATTEMPTS; attempt += 1) {
    const status = await getOcrJob(jobId, authToken)
    lastStatus = status
    if (status.status === 'done' && status.result) {
      return status.result
    }
    if (status.status === 'failed') {
      throw new Error(status.error || 'El procesamiento del documento fall?.')
    }
    await sleep(JOB_POLL_INTERVAL_MS)
  }
  return lastStatus?.result ?? null
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
