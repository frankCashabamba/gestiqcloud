/**
 * useClassifyFile.ts
 * Hook para clasificar archivos usando el servicio classifyApi
 * 
 * Maneja:
 * - Estado de carga (loading)
 * - Resultados de clasificación
 * - Errores
 * - Nivel de confianza (high/medium/low)
 */

import { useState, useCallback } from 'react'
import { classifyApi, ClassifyResponse } from '../services/classifyApi'

interface UseClassifyFileReturn {
  /** Ejecutar clasificación de archivo */
  classify: (file: File) => Promise<void>
  /** Estado de carga */
  loading: boolean
  /** Resultado de clasificación */
  result: ClassifyResponse | null
  /** Error durante clasificación */
  error: Error | null
  /** Nivel de confianza basado en score */
  confidence: 'high' | 'medium' | 'low' | null
  /** Limpiar estado (para reiniciar) */
  reset: () => void
}

/**
 * Convertir score de confianza (0-1) a nivel (high/medium/low)
 */
const getConfidenceLevel = (score: number): 'high' | 'medium' | 'low' => {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

export function useClassifyFile(): UseClassifyFileReturn {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ClassifyResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const classify = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)

    try {
      // Intentar con IA, fallback a clasificación básica
      const classificationResult = await classifyApi.classifyFileWithFallback(file)
      setResult(classificationResult)
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error')
      setError(error)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setLoading(false)
    setResult(null)
    setError(null)
  }, [])

  // Calcular nivel de confianza basado en el resultado
  const confidence = result
    ? getConfidenceLevel(result.confidence)
    : null

  return {
    classify,
    loading,
    result,
    error,
    confidence,
    reset,
  }
}

export default useClassifyFile
