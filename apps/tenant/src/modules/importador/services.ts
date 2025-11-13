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

export type DatosImportadosOut = DatosImportadosCreate & { id: number; tenant_id: number }


export async function procesarDocumento(file: File, authToken?: string): Promise<ProcesarDocumentoResult> {
    // OCR solo admite PDF/imagenes; bloquea Excel para evitar 422 del backend
    try {
        const name = (file?.name || '').toLowerCase()
        const type = (file?.type || '').toLowerCase()
        const isExcel = name.endsWith('.xlsx') || name.endsWith('.xls') || type.includes('spreadsheetml')
        if (isExcel) {
            throw new Error('Formato Excel (.xlsx/.xls) no soportado por OCR. Exporta a CSV o sube PDF/imagen.')
        }
    } catch { }
    const fd = new FormData()
    fd.append('file', file)
    const json = await apiFetch<any>('/api/v1/imports/procesar', {
        method: 'POST',
        body: fd,
        authToken,
    })

    const jobId: string | undefined = json?.job_id
    if (!jobId) {
        throw new Error('No se pudo encolar el procesamiento del documento.')
    }

    return { status: 'pending', jobId }
}

export async function pollOcrJob(jobId: string, authToken?: string): Promise<ProcesarDocumentoResult> {
    const status = await getOcrJob(jobId, authToken)

    if (status.status === 'failed') {
        throw new Error(status.error || 'El procesamiento del documento falló.')
    }

    if (status.status === 'done' && status.result) {
        return { status: 'done', jobId, payload: status.result }
    }

    return { status: 'pending', jobId }
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
            throw new Error(status.error || 'El procesamiento del documento falló.')
        }
        await sleep(JOB_POLL_INTERVAL_MS)
    }
    return lastStatus?.result ?? null
}

export async function guardarPendiente(payload: DatosImportadosCreate) {
    return apiFetch<DatosImportadosOut>('/api/v1/imports/guardar', { method: 'POST', body: JSON.stringify(payload) })
}

export async function listarPendientes() {
    return apiFetch<DatosImportadosOut[]>('/api/v1/imports/listar')
}

export async function hayPendientes() {
    return apiFetch<{ hayPendientes: boolean }>('/api/v1/imports/hay-pendientes')
}

export async function eliminarPendiente(id: number) {
    return apiFetch<{ ok: boolean }>(`/api/v1/imports/eliminar/${id}`, { method: 'DELETE' })
}

export async function enviarDocumento(id: number, authToken?: string) {
    return apiFetch(`/api/v1/imports/enviar/${id}`, { method: 'POST', authToken })
}

export async function actualizarPendiente(id: number, payload: Partial<DatosImportadosCreate>, authToken?: string) {
    return apiFetch<DatosImportadosOut>(`/api/v1/imports/actualizar/${id}`, { method: 'PUT', body: JSON.stringify(payload), authToken })
}

export async function guardarBatch(payload: DatosImportadosCreate[], authToken?: string) {
    return apiFetch<DatosImportadosOut[]>(`/api/v1/imports/guardar-batch`, { method: 'POST', body: JSON.stringify(payload), authToken })
}

export async function enviarBatch(ids: number[], authToken?: string) {
    return apiFetch<any>(`/api/v1/imports/enviar-batch`, { method: 'POST', body: JSON.stringify(ids), authToken })
}
