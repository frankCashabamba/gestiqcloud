/**
 * analyzeApi.ts
 * Servicio para consumir el endpoint de análisis de archivos
 *
 * Endpoint: POST /api/v1/imports/uploads/analyze
 */

import { apiFetch } from '../../../lib/http'
import { IMPORTS } from '@endpoints/imports'
import { withImportAIProvider } from './aiProviderPreference'

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

interface AnalyzeFileLegacyResponse {
  headers?: string[]
  sample_data?: Record<string, unknown>[]
  suggested_mapping?: Record<string, string>
}

function inferDocTypeFromHeaders(headers: string[]): string {
  const text = headers.join(' ').toLowerCase()
  if (/(producto|sku|precio|stock|codigo|articulo)/.test(text)) return 'products'
  if (/(factura|invoice|proveedor|iva|ruc|cliente)/.test(text)) return 'invoices'
  if (/(gasto|expense|recibo|categoria|monto)/.test(text)) return 'expenses'
  if (/(banco|iban|saldo|movimiento|transaccion|cuenta)/.test(text)) return 'bank'
  return 'expenses'
}

function toModernAnalyzeResponse(legacy: AnalyzeFileLegacyResponse): AnalyzeResponse {
  const headers = Array.isArray(legacy.headers) ? legacy.headers : []
  return {
    suggested_parser: 'generic_excel',
    suggested_doc_type: inferDocTypeFromHeaders(headers),
    confidence: 0.6,
    headers_sample: headers,
    headers,
    mapping_suggestion: legacy.suggested_mapping ?? null,
    explanation: 'Fallback a /tenant/imports/analyze-file (compatibilidad)',
    decision_log: [],
    requires_confirmation: true,
    available_parsers: [],
    probabilities: null,
    ai_enhanced: false,
    ai_provider: null,
  }
}

/**
 * Analiza un archivo para detectar su tipo y sugerir parser/mapping.
 * Usa apiFetch para incluir automáticamente el token de autenticación.
 */
export async function analyzeFile(file: File, authToken?: string): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('file', file)

  try {
    return await apiFetch<AnalyzeResponse>(withImportAIProvider(IMPORTS.public.uploadsAnalyze), {
      method: 'POST',
      body: formData,
      authToken,
    })
  } catch {
    const legacyData = await apiFetch<AnalyzeFileLegacyResponse>(IMPORTS.analyzeFile, {
      method: 'POST',
      body: formData,
      authToken,
    })
    return toModernAnalyzeResponse(legacyData)
  }
}

// Mantener clase para compatibilidad con código existente
class AnalyzeApi {
  async analyzeFile(file: File, authToken?: string): Promise<AnalyzeResponse> {
    return analyzeFile(file, authToken)
  }
}

export const analyzeApi = new AnalyzeApi()

export default analyzeApi
