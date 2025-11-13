import { apiFetch, API_URL } from '../../../lib/http'

/** Sprint 2: Parser disponible en el registry */
export type ParserInfo = {
  id: string
  doc_type: string
  description?: string
}

export type ParserRegistry = {
  parsers: Record<string, ParserInfo>
  count: number
}

export type ImportBatch = {
  id: string
  source_type: string
  origin: string
  status: string
  file_key?: string | null
  mapping_id?: string | null
  created_at: string
  attachments?: ImportAttachment[]
  /** Campos de clasificación (Fase A) */
  suggested_parser?: string | null
  classification_confidence?: number | null
  ai_enhanced?: boolean
  ai_provider?: string | null
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
  description?: string
  file_pattern?: string
  mapping?: Record<string,string>
  transforms?: Record<string, any>
  defaults?: Record<string, any>
}

export type CreateBatchPayload = {
  source_type: string
  origin: string
  mapping_id?: string | null
  file_key?: string | null
  notes?: string | null
  metadata?: Record<string, unknown>
  /** Campos de clasificación (Fase A) */
  suggested_parser?: string | null
  classification_confidence?: number | null
  ai_enhanced?: boolean
  ai_provider?: string | null
}

export type IngestBatchPayload = {
  rows: unknown[]
  mapping_id?: string | null
  transforms?: Record<string, unknown> | null
  defaults?: Record<string, unknown> | null
}

export async function createBatch(payload: CreateBatchPayload, authToken?: string) {
  return apiFetch<ImportBatch>('/api/v1/imports/batches', {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken,
  })
}

export async function ingestBatch(
  batchId: string,
  payload: IngestBatchPayload,
  authToken?: string,
  columnMappingId?: string | null
) {
  const url = columnMappingId
    ? `/api/v1/imports/batches/${batchId}/ingest?column_mapping_id=${columnMappingId}`
    : `/api/v1/imports/batches/${batchId}/ingest`

  return apiFetch<{ accepted: number; rejected: number; errors?: unknown[] }>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      authToken,
    },
  )
}

export async function listMappings(authToken?: string) {
  // Legacy path kept; prefer /column-mappings
  try {
    return await apiFetch<ImportMapping[]>('/api/v1/imports/column-mappings', { authToken })
  } catch {
    return apiFetch<ImportMapping[]>('/api/v1/imports/mappings', { authToken })
  }
}

export async function getOcrJob(jobId: string, authToken?: string) {
  const options = authToken ? { authToken } : {}
  return apiFetch<OcrJobStatus>(`/api/v1/imports/jobs/${jobId}`, options)
}

export async function listBatches(status?: string) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return apiFetch<ImportBatch[]>(`/api/v1/imports/batches${qs}`)
}

export async function getBatch(id: string) {
  return apiFetch<ImportBatch>(`/api/v1/imports/batches/${id}`)
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
  return apiFetch<ImportItem[]>(`/api/v1/imports/batches/${batchId}/items${qs}`)
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
  return apiFetch<ImportItem>(`/api/v1/imports/batches/${batchId}/items/${itemId}`, {
    method: 'PATCH',
    body,
  })
}

export async function validateBatch(batchId: string) {
  return apiFetch<ImportItem[]>(`/api/v1/imports/batches/${batchId}/validate`, { method: 'POST' })
}

export async function promoteBatch(batchId: string) {
  return apiFetch<{ created: number; skipped: number; failed: number }>(
    `/api/v1/imports/batches/${batchId}/promote`,
    { method: 'POST' },
  )
}

function getStoredToken(): string | null {
  try {
    const sess = sessionStorage.getItem('access_token_tenant')
    if (sess) return sess
  } catch {}
  try {
    return localStorage.getItem('authToken')
  } catch {
    return null
  }
}

export async function downloadErrorsCsv(batchId: string) {
  // Fetch raw CSV (apiFetch assumes JSON)
  const token = getStoredToken()
  const headers: HeadersInit = { }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}/api/v1/imports/batches/${batchId}/errors.csv`, {
    credentials: 'include',
    headers,
  })
  if (!res.ok) throw new Error('No se pudo descargar errors.csv')
  return await res.text()
}

export async function uploadBatchPhotos(batchId: string, files: File[]) {
  const form = new FormData()
  files.forEach((file) => {
    form.append('photos', file)
  })
  const token = getStoredToken()
  const headers: HeadersInit = { }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}/api/v1/imports/batches/${batchId}/photos`, {
    method: 'POST',
    body: form,
    credentials: 'include',
    headers,
  })
  if (!res.ok) throw new Error('No se pudieron subir las fotos del lote')
  return (await res.json()) as { attachments: ImportAttachment[] }
}

export async function uploadItemPhotos(batchId: string, itemId: string, files: File[]) {
  const form = new FormData()
  files.forEach((file) => {
    form.append('photos', file)
  })
  const token = getStoredToken()
  const headers: HeadersInit = { }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}/api/v1/imports/batches/${batchId}/items/${itemId}/photos`, {
    method: 'POST',
    body: form,
    credentials: 'include',
    headers,
  })
  if (!res.ok) throw new Error('No se pudieron subir las fotos del item')
  return (await res.json()) as { attachments: ImportAttachment[] }
}

// Column mappings CRUD (modern endpoints)
export async function createColumnMapping(payload: { name: string; mapping: any; description?: string; file_pattern?: string }, authToken?: string) {
  return apiFetch<ImportMapping>('/api/v1/imports/column-mappings', { method: 'POST', body: JSON.stringify(payload), authToken })
}

export async function suggestMapping(file: File, authToken?: string) {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch<{ headers: string[]; mapping: any; transforms: any; defaults: any; confidence: Record<string, number> }>(
    '/api/v1/imports/mappings/suggest',
    { method: 'POST', body: fd, authToken },
  )
}

export async function setBatchMapping(batchId: string, mappingId: string, authToken?: string) {
  return apiFetch('/api/v1/imports/batches/' + batchId + '/set-mapping', { method: 'POST', body: JSON.stringify({ mapping_id: mappingId }), authToken })
}

export async function resetBatch(batchId: string, opts?: { clearItems?: boolean; newStatus?: string; mappingId?: string }, authToken?: string) {
  const u = new URL('/api/v1/imports/batches/' + batchId + '/reset', location.origin)
  u.searchParams.set('clear_items', String(opts?.clearItems ?? true))
  u.searchParams.set('new_status', opts?.newStatus ?? 'PENDING')
  if (opts?.mappingId) u.searchParams.set('mapping_id', opts.mappingId)
  return apiFetch(u.pathname + u.search, { method: 'POST', authToken })
}

// --------- Large Excel via local chunked upload ---------

type InitChunkUploadResp = {
  provider: 'local'
  upload_id: string
  part_size: number
  max_part_size: number
}

export async function initChunkUpload(
  filename: string,
  contentType: string,
  size: number,
  authToken?: string,
  partSizeBytes?: number,
) {
  return apiFetch<InitChunkUploadResp>('/api/v1/imports/uploads/chunk/init', {
    method: 'POST',
    body: JSON.stringify({ filename, content_type: contentType, size, part_size: partSizeBytes }),
    authToken,
  })
}

export async function uploadChunkPart(
  uploadId: string,
  partNumber: number,
  blob: Blob,
  authToken?: string,
) {
  return apiFetch<{ ok: boolean; bytes: number }>(
    `/api/v1/imports/uploads/chunk/${uploadId}/${partNumber}`,
    {
      method: 'PUT',
      // Ensure correct content-type for raw binary
      headers: { 'Content-Type': 'application/octet-stream' },
      body: blob as any,
      authToken,
    },
  )
}

export async function completeChunkUpload(uploadId: string, expectedParts: number, expectedSize: number, authToken?: string) {
  return apiFetch<{ file_key: string; bytes: number }>(
    `/api/v1/imports/uploads/chunk/${uploadId}/complete`,
    {
      method: 'POST',
      body: JSON.stringify({ expected_parts: expectedParts, expected_size: expectedSize }),
      authToken,
    },
  )
}

export async function createBatchFromUpload(fileKey: string, sourceType = 'products', mappingId?: string | null, authToken?: string, originalFilename?: string | null) {
  return apiFetch<ImportBatch>(`/api/v1/imports/batches/from-upload`, {
    method: 'POST',
    body: JSON.stringify({ file_key: fileKey, source_type: sourceType, mapping_id: mappingId || undefined, original_filename: originalFilename || undefined }),
    authToken,
  })
}

export async function startExcelImport(batchId: string, authToken?: string) {
  return apiFetch<{ task_id: string; status: string }>(`/api/v1/imports/batches/${batchId}/start-excel-import`, {
    method: 'POST',
    authToken,
  })
}

export async function uploadExcelViaChunks(
  file: File,
  opts?: { sourceType?: string; mappingId?: string | null; onProgress?: (pct: number) => void; authToken?: string; desiredPartSizeBytes?: number },
) {
  const sourceType = opts?.sourceType ?? 'products'
  const mappingId = opts?.mappingId ?? null
  const authToken = opts?.authToken
  const init = await initChunkUpload(
    file.name,
    file.type || 'application/octet-stream',
    file.size,
    authToken,
    opts?.desiredPartSizeBytes,
  )
  const partSize = init.part_size || 8 * 1024 * 1024
  const totalParts = Math.ceil(file.size / partSize)
  let uploaded = 0
  for (let i = 0; i < totalParts; i += 1) {
    const start = i * partSize
    const end = Math.min(start + partSize, file.size)
    const blob = file.slice(start, end)
    await uploadChunkPart(init.upload_id, i + 1, blob, authToken)
    uploaded = end
    if (opts?.onProgress) {
      const pct = Math.min(100, Math.round((uploaded / file.size) * 100))
      opts.onProgress(pct)
    }
  }
  const completed = await completeChunkUpload(init.upload_id, totalParts, file.size, authToken)
  const batch = await createBatchFromUpload(completed.file_key, sourceType, mappingId, authToken, (completed as any).original_filename || file.name)
  const { task_id } = await startExcelImport(batch.id, authToken)
  return { batchId: batch.id, fileKey: completed.file_key, taskId: task_id }
}

// Sprint 2: Obtener registry de parsers disponibles
export async function getParserRegistry(authToken?: string) {
  return apiFetch<ParserRegistry>('/api/v1/imports/parsers/registry', {
    method: 'GET',
    authToken,
  })
}
