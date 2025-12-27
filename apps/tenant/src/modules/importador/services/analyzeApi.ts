/**
 * analyzeApi.ts
 * Servicio para consumir el endpoint de análisis de archivos
 *
 * Endpoint: POST /api/v1/imports/uploads/analyze
 */

import { apiFetch } from '../../../lib/http'

export interface DecisionLogEntry {
  step: string
  timestamp: string
  input_data: Record<string, unknown>
  output_data: Record<string, unknown>
  confidence?: number
  duration_ms?: number
}

export interface AnalyzeResponse {
  suggested_parser: string
  suggested_doc_type: string
  confidence: number
  headers_sample: string[]
  headers?: string[]
  mapping_suggestion: Record<string, string> | null
  explanation: string
  decision_log: DecisionLogEntry[]
  requires_confirmation: boolean
  available_parsers: string[]
  probabilities: Record<string, number> | null
  ai_enhanced: boolean
  ai_provider: string | null
}

/**
 * Analiza un archivo para detectar su tipo y sugerir parser/mapping.
 * Usa apiFetch para incluir automáticamente el token de autenticación.
 */
export async function analyzeFile(file: File, authToken?: string): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch<AnalyzeResponse>('/api/v1/imports/uploads/analyze', {
    method: 'POST',
    body: formData,
    authToken,
  })
}

// Mantener clase para compatibilidad con código existente
class AnalyzeApi {
  async analyzeFile(file: File, authToken?: string): Promise<AnalyzeResponse> {
    return analyzeFile(file, authToken)
  }
}

export const analyzeApi = new AnalyzeApi()

export default analyzeApi
