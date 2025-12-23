import { apiFetch } from '../../../lib/http'
import { IMPORTS } from '@endpoints/imports'
import { ImportMapping } from '@api-types/imports'

export interface AnalyzeFileResponse {
  headers: string[]
  header_row: number
  sample_data: Record<string, any>[]
  suggested_mapping: Record<string, string>
  total_rows: number
  total_columns: number
  saved_mappings: ImportMapping[]
}

export interface CreateColumnMappingRequest {
  name: string
  mapping: Record<string, string>
  description?: string
  file_pattern?: string
}

export async function analyzeExcelFile(file: File): Promise<AnalyzeFileResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch<AnalyzeFileResponse>(IMPORTS.analyzeFile, {
    method: 'POST',
    body: formData,
  })
}

export async function listColumnMappings(): Promise<ImportMapping[]> {
  return apiFetch<ImportMapping[]>(IMPORTS.mappings.list)
}

export async function createColumnMapping(
  data: CreateColumnMappingRequest
): Promise<ImportMapping> {
  return apiFetch<ImportMapping>(IMPORTS.mappings.create, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteColumnMapping(id: string): Promise<void> {
  return apiFetch<void>(`${IMPORTS.mappings.create}/${id}`, {
    method: 'DELETE',
  })
}
