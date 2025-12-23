/**
 * classifyApi.ts
 * Servicio para consumir endpoints de clasificación del backend
 *
 * Endpoints disponibles:
 * - POST /api/v1/imports/files/classify (clasificación básica)
 * - POST /api/v1/imports/files/classify-with-ai (clasificación con IA)
 */

import { apiFetch } from '../../../lib/http'

export interface ClassifyResponse {
  /** Parser sugerido basado en análisis del archivo */
  suggested_parser: string
  /** Confianza de la clasificación (0.0 a 1.0) */
  confidence: number
  /** Razón de la clasificación */
  reason?: string
  /** Si fue mejorado con IA (no solo heurística) */
  enhanced_by_ai: boolean
  /** Proveedor de IA usado (local, openai, azure) */
  ai_provider?: string
  /** Probabilidades para cada parser disponible */
  probabilities?: Record<string, number>
  /** Lista de parsers disponibles en el backend */
  available_parsers?: string[]
}

/**
 * Clasificar archivo con métodos básicos (heurística local)
 */
export async function classifyFileBasic(file: File, authToken?: string): Promise<ClassifyResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch<ClassifyResponse>('/api/v1/imports/files/classify', {
    method: 'POST',
    body: formData,
    authToken,
  })
}

/**
 * Clasificar archivo con IA (local, OpenAI, o Azure)
 */
export async function classifyFileWithAI(file: File, authToken?: string): Promise<ClassifyResponse> {
  const formData = new FormData()
  formData.append('file', file)

  return apiFetch<ClassifyResponse>('/api/v1/imports/files/classify-with-ai', {
    method: 'POST',
    body: formData,
    authToken,
  })
}

/**
 * Intentar clasificar con IA, fallback a clasificación básica si falla
 */
export async function classifyFileWithFallback(file: File, authToken?: string): Promise<ClassifyResponse> {
  try {
    return await classifyFileWithAI(file, authToken)
  } catch (error) {
    console.warn('AI classification failed, falling back to basic:', error)
    return classifyFileBasic(file, authToken)
  }
}

// Mantener clase para compatibilidad con código existente
class ClassifyApi {
  async classifyFileBasic(file: File, authToken?: string): Promise<ClassifyResponse> {
    return classifyFileBasic(file, authToken)
  }

  async classifyFileWithAI(file: File, authToken?: string): Promise<ClassifyResponse> {
    return classifyFileWithAI(file, authToken)
  }

  async classifyFileWithFallback(file: File, authToken?: string): Promise<ClassifyResponse> {
    return classifyFileWithFallback(file, authToken)
  }
}

export const classifyApi = new ClassifyApi()

export default classifyApi
