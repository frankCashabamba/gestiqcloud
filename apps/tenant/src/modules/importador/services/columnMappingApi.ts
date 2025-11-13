import { apiFetch } from '../../../lib/http';

export interface AnalyzeFileResponse {
  headers: string[]
  header_row: number
  sample_data: Record<string, any>[]
  suggested_mapping: Record<string, string>
  total_rows: number
  total_columns: number
  saved_mappings: SavedColumnMapping[]
}

export interface SavedColumnMapping {
  id: string
  name: string
  description?: string
  mapping: Record<string, string>
  file_pattern?: string
  use_count: number
  last_used_at?: string
  created_at: string
}

export interface CreateColumnMappingRequest {
  name: string
  mapping: Record<string, string>
  description?: string
  file_pattern?: string
}

/**
 * Analiza un archivo Excel y detecta columnas automáticamente
 */
export async function analyzeExcelFile(
  file: File
): Promise<AnalyzeFileResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch<AnalyzeFileResponse>('/api/v1/imports/analyze-file', {
    method: 'POST',
    body: formData
  })
}

/**
 * Lista mapeos de columnas guardados
 */
export async function listColumnMappings(): Promise<SavedColumnMapping[]> {
  return apiFetch<SavedColumnMapping[]>('/api/v1/imports/column-mappings')
}

/**
 * Crea un nuevo mapeo de columnas
 */
export async function createColumnMapping(
  data: CreateColumnMappingRequest
): Promise<SavedColumnMapping> {
  return apiFetch<SavedColumnMapping>('/api/v1/imports/column-mappings', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

/**
 * Elimina un mapeo de columnas
 */
export async function deleteColumnMapping(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/imports/column-mappings/${id}`, {
    method: 'DELETE'
  })
}
