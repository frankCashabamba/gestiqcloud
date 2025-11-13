// src/services/classify.ts
// Servicio para clasificación de archivos de importación

import api from '../shared/api/client'

export interface ClassifyResponse {
  suggested_parser: string
  confidence: number
  reason: string
  available_parsers: string[]
  content_analysis?: {
    headers?: string[]
    scores?: Record<string, number>
  }
  probabilities?: Record<string, number>
  enhanced_by_ai?: boolean
  ai_provider?: string
}

const BASE_URL = '/api/v1/imports/files'

/**
 * Clasifica un archivo usando análisis heurístico básico
 */
export async function classifyFileBasic(file: File): Promise<ClassifyResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<ClassifyResponse>(
    `${BASE_URL}/classify`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return data
}

/**
 * Clasifica un archivo con potencial mejora de IA
 */
export async function classifyFileWithAI(file: File): Promise<ClassifyResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post<ClassifyResponse>(
    `${BASE_URL}/classify-with-ai`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return data
}

/**
 * Clasifica un archivo. Intenta primero con IA, fallback a básico
 */
export async function classifyFile(file: File, useAI = true): Promise<ClassifyResponse> {
  try {
    if (useAI) {
      return await classifyFileWithAI(file)
    }
    return await classifyFileBasic(file)
  } catch (error) {
    console.error('Error clasificando archivo:', error)
    // Fallback a clasificación básica si falla la con IA
    if (useAI) {
      try {
        return await classifyFileBasic(file)
      } catch (fallbackError) {
        console.error('Error en fallback de clasificación:', fallbackError)
        throw fallbackError
      }
    }
    throw error
  }
}
