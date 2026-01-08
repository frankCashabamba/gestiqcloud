import { apiFetch, API_URL, HttpError } from '../../../lib/http'
import { IMPORTS } from '@endpoints/imports'
import {
  ParserRegistry,
  ImportBatch,
  ImportItem,
  ImportMapping,
  ImportAttachment,
  CreateBatchPayload,
  OcrJobStatus,
  InitChunkUploadResp,
  ConfirmBatchRequest,
  ConfirmBatchResponse,
  ConfirmationStatus,
} from '@api-types/imports'

export type {
  ParserRegistry,
  ImportBatch,
  ImportItem,
  ImportMapping,
  ImportAttachment,
  OcrJobStatus,
  InitChunkUploadResp,
  ConfirmBatchRequest,
  ConfirmBatchResponse,
  ConfirmationStatus,
}

export type IngestBatchPayload = {
  rows: unknown[]
  mapping_id?: string | null
  transforms?: Record<string, unknown> | null
  defaults?: Record<string, unknown> | null
}

export async function createBatch(payload: CreateBatchPayload, authToken?: string) {
  return apiFetch<ImportBatch>(IMPORTS.batches.base, {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken,
  })
}

export type IngestItemResult = {
  id: string
  idx?: number
  status?: string
  errors?: unknown[]
}

export type IngestBatchResult = {
  accepted: number
  rejected: number
  errors?: unknown[]
  items?: IngestItemResult[]
}

export async function ingestBatch(
  batchId: string,
  payload: IngestBatchPayload,
  authToken?: string,
  columnMappingId?: string | null
): Promise<IngestBatchResult> {
  const url = IMPORTS.batches.ingest(batchId, columnMappingId ?? undefined)

  // Backend returns list of items, we transform to accepted/rejected counts
  const items = await apiFetch<IngestItemResult[]>(
    url,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      authToken,
    },
  )

  // Transform list response to expected format
  const accepted = items.filter(i => i.status !== 'ERROR' && i.status !== 'ERROR_VALIDATION').length
  const rejected = items.filter(i => i.status === 'ERROR' || i.status === 'ERROR_VALIDATION').length
  const errors = items.filter(i => i.errors?.length).map(i => i.errors)

  return { accepted, rejected, errors: errors.flat(), items }
}

export async function listMappings(authToken?: string) {
  // Legacy path kept; prefer /column-mappings
  try {
    return await apiFetch<ImportMapping[]>(IMPORTS.mappings.list, { authToken })
  } catch {
    return apiFetch<ImportMapping[]>(IMPORTS.mappings.legacyList, { authToken })
  }
}

export async function getOcrJob(jobId: string, authToken?: string) {
  const options = authToken ? { authToken } : {}
  return apiFetch<OcrJobStatus>(IMPORTS.ocrJob(jobId), options)
}

// OCR helpers (modernized from legacy services)
type OcrJobResultPayload = { archivo: string; documentos: any[] }

export type ProcesarDocumentoResult =
  | { status: 'done'; jobId: string; payload: OcrJobResultPayload }
  | { status: 'pending'; jobId: string }

export async function processDocument(file: File, authToken?: string): Promise<ProcesarDocumentoResult> {
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

  try {
    const json = await apiFetch<any>(IMPORTS.processDocument, {
      method: 'POST',
      body: fd,
      authToken,
    })

    const jobId: string | undefined = json?.job_id
    if (!jobId) {
      throw new Error('No se pudo encolar el procesamiento del documento.')
    }

    return { status: 'pending', jobId }
  } catch (err: any) {
    if (err instanceof HttpError) {
      // Mensajes claros según status común en OCR
      if (err.status === 401) {
        throw new Error('Sesión expirada o sin permisos. Inicia sesión para usar el OCR.')
      }
      if (err.status === 413) {
        throw new Error('Archivo demasiado grande para OCR (supera el límite configurado).')
      }
      if (err.status === 415 || err.status === 422) {
        throw new Error('Formato no soportado para OCR. Usa PDF/imagen o el flujo de Excel/CSV.')
      }
    }
    throw err
  }
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

export async function listBatches(status?: string, tenantId?: string) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (tenantId) params.set('tenant_id', tenantId)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch<ImportBatch[]>(`${IMPORTS.batches.base}${qs}`)
}

export async function listBatchesByCompany(tenantId: string, authToken?: string) {
  const qs = new URLSearchParams({ tenant_id: tenantId }).toString()
  return apiFetch<{ items: ImportBatch[] } | ImportBatch[]>(`${IMPORTS.batches.base}?${qs}`, { authToken })
}

export async function getBatch(id: string) {
  return apiFetch<ImportBatch>(IMPORTS.batches.byId(id))
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
  return apiFetch<ImportItem[]>(IMPORTS.batches.items(batchId, qs))
}

export async function listProductItems(
  batchId: string,
  opts?: { status?: string; limit?: number; offset?: number; authToken?: string }
) {
  const params = new URLSearchParams()
  if (opts?.status) params.set('status', opts.status)
  if (opts?.limit != null) params.set('limit', String(opts.limit))
  if (opts?.offset != null) params.set('offset', String(opts.offset))
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch<{ items: ImportItem[]; total?: number }>(
    IMPORTS.batches.itemsProducts(batchId, qs),
    { authToken: opts?.authToken }
  )
}

/** Lista productos de importación de todos los batches (requiere tenant_id cuando no se usa RLS). */
export async function listAllProductItems(
  opts?: { status?: string; limit?: number; offset?: number; tenantId?: string; authToken?: string }
) {
  const params = new URLSearchParams()
  if (opts?.status) params.set('status', opts.status)
  if (opts?.limit != null) params.set('limit', String(opts.limit))
  if (opts?.offset != null) params.set('offset', String(opts.offset))
  if (opts?.tenantId) params.set('tenant_id', opts.tenantId)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch<{ items: ImportItem[]; total?: number; limit?: number; offset?: number }>(
    IMPORTS.items.products(qs),
    { authToken: opts?.authToken }
  )
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
    body = JSON.stringify({ field: a, value: b })
  } else if (a && typeof a === 'object' && 'normalized' in a && typeof a.normalized === 'object') {
    const entries = Object.entries(a.normalized as Record<string, unknown>)
    const [field, value] = entries[0] || ['', null]
    body = JSON.stringify({ field, value })
  } else {
    const isFlat =
      a &&
      typeof a === 'object' &&
      !Array.isArray(a) &&
      !('normalized' in a) &&
      !('raw' in a)
    if (isFlat) {
      const entries = Object.entries(a as Record<string, unknown>)
      const [field, value] = entries[0] || ['', null]
      body = JSON.stringify({ field, value })
  } else {
      body = JSON.stringify(a ?? {})
    }
  }
  return apiFetch<ImportItem>(IMPORTS.items.byId(batchId, itemId), {
    method: 'PATCH',
    body,
  })
}

export async function validateBatch(batchId: string) {
  return apiFetch<ImportItem[]>(IMPORTS.batches.itemsValidate(batchId), { method: 'POST' })
}

export async function promoteBatch(batchId: string) {
  return apiFetch<{ created: number; skipped: number; failed: number }>(
    IMPORTS.batches.promote(batchId),
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

  const res = await fetch(`${API_URL}${IMPORTS.reports.errorsCsv(batchId)}`, {
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

  const res = await fetch(`${API_URL}${IMPORTS.reports.batchPhotos(batchId)}`, {
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

  const res = await fetch(`${API_URL}${IMPORTS.reports.itemPhotos(batchId, itemId)}`, {
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
  return apiFetch<ImportMapping>(IMPORTS.mappings.create, { method: 'POST', body: JSON.stringify(payload), authToken })
}

export async function suggestMapping(file: File, authToken?: string) {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch<{ headers: string[]; mapping: any; transforms: any; defaults: any; confidence: Record<string, number> }>(
    IMPORTS.mappings.suggest,
    { method: 'POST', body: fd, authToken },
  )
}

export async function setBatchMapping(batchId: string, mappingId: string, authToken?: string) {
  return apiFetch(IMPORTS.batches.setMapping(batchId), { method: 'POST', body: JSON.stringify({ mapping_id: mappingId }), authToken })
}

export async function resetBatch(batchId: string, opts?: { clearItems?: boolean; newStatus?: string; mappingId?: string }, authToken?: string) {
  const u = new URL(IMPORTS.batches.reset(batchId), location.origin)
  u.searchParams.set('clear_items', String(opts?.clearItems ?? true))
  u.searchParams.set('new_status', opts?.newStatus ?? 'PENDING')
  if (opts?.mappingId) u.searchParams.set('mapping_id', opts.mappingId)
  return apiFetch(u.pathname + u.search, { method: 'POST', authToken })
}

export async function deleteBatch(batchId: string, authToken?: string) {
  return apiFetch(IMPORTS.batches.delete(batchId), { method: 'DELETE', authToken })
}

export async function cancelBatch(batchId: string, authToken?: string) {
  return apiFetch(IMPORTS.batches.cancel(batchId), { method: 'POST', authToken })
}

// --------- Large Excel via local chunked upload ---------

export async function initChunkUpload(
  filename: string,
  contentType: string,
  size: number,
  authToken?: string,
  partSizeBytes?: number,
) {
  return apiFetch<InitChunkUploadResp>(IMPORTS.uploads.chunkInit, {
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
    IMPORTS.uploads.chunkPart(uploadId, partNumber),
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
    IMPORTS.uploads.chunkComplete(uploadId),
    {
      method: 'POST',
      body: JSON.stringify({ expected_parts: expectedParts, expected_size: expectedSize }),
      authToken,
    },
  )
}

export async function createBatchFromUpload(fileKey: string, sourceType = 'products', mappingId?: string | null, authToken?: string, originalFilename?: string | null, parserId?: string | null) {
  return apiFetch<ImportBatch>(IMPORTS.batches.fromUpload, {
    method: 'POST',
    body: JSON.stringify({
      file_key: fileKey,
      source_type: sourceType,
      mapping_id: mappingId || undefined,
      original_filename: originalFilename || undefined,
      parser_id: parserId || undefined,
    }),
    authToken,
  })
}

export async function startExcelImport(batchId: string, authToken?: string) {
  return apiFetch<{ task_id: string; status: string; parser_id?: string; doc_type?: string }>(
    IMPORTS.batches.startExcel(batchId),
    {
      method: 'POST',
      authToken,
    },
  )
}

export async function getBatchStatus(batchId: string, authToken?: string) {
  return apiFetch<any>(IMPORTS.batches.status(batchId), { authToken })
}

export async function uploadExcelViaChunks(
  file: File,
  opts?: {
    sourceType?: string
    mappingId?: string | null
    parserId?: string | null
    onProgress?: (pct: number) => void
    authToken?: string
    desiredPartSizeBytes?: number
  },
) {
  const sourceType = opts?.sourceType ?? 'products'
  const mappingId = opts?.mappingId ?? null
  const authToken = opts?.authToken
  const parserId = opts?.parserId ?? null
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
  const batch = await createBatchFromUpload(
    completed.file_key,
    sourceType,
    mappingId,
    authToken,
    (completed as any).original_filename || file.name,
    parserId,
  )
  const { task_id } = await startExcelImport(batch.id, authToken)
  return { batchId: batch.id, fileKey: completed.file_key, taskId: task_id }
}

// Sprint 2: Obtener registry de parsers disponibles
export async function getParserRegistry(authToken?: string) {
  return apiFetch<ParserRegistry>(IMPORTS.parsersRegistry, {
    method: 'GET',
    authToken,
  })
}

export async function confirmBatch(
  batchId: string,
  payload: ConfirmBatchRequest,
  authToken?: string
) {
  return apiFetch<ConfirmBatchResponse>(IMPORTS.batches.confirm(batchId), {
    method: 'POST',
    body: JSON.stringify(payload),
    authToken,
  })
}

export async function getConfirmationStatus(batchId: string, authToken?: string) {
  return apiFetch<ConfirmationStatus>(IMPORTS.batches.confirmationStatus(batchId), {
    method: 'GET',
    authToken,
  })
}

export async function listCategories(authToken?: string) {
  try {
    return await apiFetch<{ id?: string | number; name?: string }[]>(
      '/api/v1/products/product-categories',
      { authToken },
    )
  } catch {
    return apiFetch<{ id?: string | number; name?: string }[]>('/api/v1/categorias', { authToken })
  }
}
