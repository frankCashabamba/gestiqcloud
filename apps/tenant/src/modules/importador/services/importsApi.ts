import { apiFetch, API_URL } from '../../../lib/http'

export type ImportBatch = {
  id: string
  source_type: string
  origin: string
  status: string
  file_key?: string | null
  mapping_id?: string | null
  created_at: string
  attachments?: ImportAttachment[]
}

export type ImportItem = {
  id: string
  idx: number
  status: string
  errors?: { field?: string; msg?: string }[]
  raw?: Record<string, unknown>
  normalized?: Record<string, unknown>
  attachments?: ImportAttachment[]
}

export type ImportAttachment = {
  id: string
  item_id?: string | null
  batch_id: string
  kind: 'file' | 'photo'
  url: string
  created_at: string
  metadata?: Record<string, unknown> | null
}

export type OcrJobStatus = {
  job_id: string
  status: 'pending' | 'running' | 'done' | 'failed'
  result?: { archivo: string; documentos: any[] } | null
  error?: string | null
}

export type ImportMapping = {
  id: string
  name: string
  source_type: string
  version: number
  created_at: string
}

export type CreateBatchPayload = {
  source_type: string
  origin: string
  mapping_id?: string | null
  file_key?: string | null
  notes?: string | null
  metadata?: Record<string, unknown>
}

export type IngestBatchPayload = {
  items?: unknown[]
  file_key?: string | null
  dry_run?: boolean
  dedupe?: boolean
}

export async function createBatch(payload: CreateBatchPayload) {
  return apiFetch<ImportBatch>('/v1/imports/batches', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function ingestBatch(batchId: string, payload: IngestBatchPayload) {
  return apiFetch<{ accepted: number; rejected: number; errors?: unknown[] }>(
    `/v1/imports/batches/${batchId}/ingest`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export async function listMappings(authToken?: string) {
  return apiFetch<ImportMapping[]>('/v1/imports/mappings', { authToken })
}

export async function getOcrJob(jobId: string, authToken?: string) {
  const options = authToken ? { authToken } : {}
  return apiFetch<OcrJobStatus>(`/v1/imports/jobs/${jobId}`, options)
}

export async function listBatches(status?: string) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return apiFetch<ImportBatch[]>(`/v1/imports/batches${qs}`)
}

export async function getBatch(id: string) {
  return apiFetch<ImportBatch>(`/v1/imports/batches/${id}`)
}

/** Accepts optional filters (status, q). */
export async function listItems(
  batchId: string,
  opts?: { status?: string; q?: string }
) {
  const params = new URLSearchParams()
  if (opts?.status) params.set('status', opts.status)
  if (opts?.q) params.set('q', opts.q)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch<ImportItem[]>(`/v1/imports/batches/${batchId}/items${qs}`)
}

/**
 * Patch an item.
 * Overloads:
 *   - patchItem(batchId, itemId, patchObject)
 *   - patchItem(batchId, itemId, field, value)
 */
export async function patchItem(batchId: string, itemId: string, patch: Partial<ImportItem>): Promise<ImportItem>
export async function patchItem(batchId: string, itemId: string, field: string, value: unknown): Promise<ImportItem>
export async function patchItem(batchId: string, itemId: string, a: any, b?: any): Promise<ImportItem> {
  let body: string
  if (typeof a === 'string') {
    // Single-field edit; we assume normalized map update
    body = JSON.stringify({ normalized: { [a]: b } })
  } else {
    body = JSON.stringify(a ?? {})
  }
  return apiFetch<ImportItem>(`/v1/imports/batches/${batchId}/items/${itemId}`, {
    method: 'PATCH',
    body,
  })
}

export async function validateBatch(batchId: string) {
  return apiFetch<ImportItem[]>(`/v1/imports/batches/${batchId}/validate`, { method: 'POST' })
}

export async function promoteBatch(batchId: string) {
  return apiFetch<{ created: number; skipped: number; failed: number }>(
    `/v1/imports/batches/${batchId}/promote`,
    { method: 'POST' },
  )
}

export async function downloadErrorsCsv(batchId: string) {
  // Fetch raw CSV (apiFetch assumes JSON)
  const res = await fetch(`${API_URL}/v1/imports/batches/${batchId}/errors.csv`, {
    credentials: 'include',
  })
  if (!res.ok) throw new Error('No se pudo descargar errors.csv')
  return await res.text()
}

export async function uploadBatchPhotos(batchId: string, files: File[]) {
  const form = new FormData()
  files.forEach((file) => {
    form.append('photos', file)
  })
  const res = await fetch(`${API_URL}/v1/imports/batches/${batchId}/photos`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  })
  if (!res.ok) throw new Error('No se pudieron subir las fotos del lote')
  return (await res.json()) as { attachments: ImportAttachment[] }
}

export async function uploadItemPhotos(batchId: string, itemId: string, files: File[]) {
  const form = new FormData()
  files.forEach((file) => {
    form.append('photos', file)
  })
  const res = await fetch(`${API_URL}/v1/imports/batches/${batchId}/items/${itemId}/photos`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  })
  if (!res.ok) throw new Error('No se pudieron subir las fotos del item')
  return (await res.json()) as { attachments: ImportAttachment[] }
}


