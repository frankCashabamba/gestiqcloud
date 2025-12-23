export type ParserInfo = {
  id: string
  doc_type: string
  description?: string
}

export type ParserRegistry = {
  parsers: Record<string, ParserInfo>
  count: number
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

export type ImportItem = {
  id: string
  idx: number
  status: string
  errors?: { field?: string; msg?: string }[]
  raw?: Record<string, unknown>
  normalized?: Record<string, unknown>
  attachments?: ImportAttachment[]
}

export type ImportBatch = {
  id: string
  source_type: string
  origin: string
  status: string
  file_key?: string | null
  mapping_id?: string | null
  parser_id?: string | null
  created_at: string
  attachments?: ImportAttachment[]
  suggested_parser?: string | null
  classification_confidence?: number | null
  ai_enhanced?: boolean
  ai_provider?: string | null
  requires_confirmation?: boolean
  confirmed_at?: string | null
  confirmed_parser?: string | null
  user_override?: boolean
}

export type ImportMapping = {
  id: string
  name: string
  source_type: string
  version: number
  created_at: string
  description?: string
  file_pattern?: string
  mapping?: Record<string, string>
  transforms?: Record<string, unknown>
  defaults?: Record<string, unknown>
}

export type CreateBatchPayload = {
  source_type: string
  origin: string
  mapping_id?: string | null
  file_key?: string | null
  notes?: string | null
  metadata?: Record<string, unknown>
  suggested_parser?: string | null
  classification_confidence?: number | null
  ai_enhanced?: boolean
  ai_provider?: string | null
  parser_id?: string | null
}

export type InitChunkUploadResp = {
  provider: string
  upload_id: string
  part_size: number
  max_part_size: number
}

export type OcrJobStatus = {
  job_id: string
  status: 'pending' | 'running' | 'done' | 'failed'
  result?: { archivo: string; documentos: any[] } | null
  error?: string | null
}

export type ConfirmBatchRequest = {
  parser_id: string
  mapping_id?: string | null
  custom_mapping?: Record<string, string> | null
  transforms?: Record<string, unknown> | null
  defaults?: Record<string, unknown> | null
}

export type ConfirmBatchResponse = {
  batch_id: string
  confirmed_parser: string
  mapping_applied: boolean
  ready_to_process: boolean
  message: string
}

export type ConfirmationStatus = {
  batch_id: string
  requires_confirmation: boolean
  confirmed_at: string | null
  confirmed_parser: string | null
  suggested_parser: string | null
  classification_confidence: number | null
  user_override: boolean
}
