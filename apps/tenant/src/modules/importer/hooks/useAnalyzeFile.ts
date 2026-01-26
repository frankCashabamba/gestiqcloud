/**
 * useAnalyzeFile.ts
 * Hook para analizar archivos usando el servicio analyzeApi
 *
 * Maneja:
 * - Estado de carga (loading)
 * - Resultados de análisis
 * - Errores
 * - Flag de confirmación requerida
 */

import { useState, useCallback } from 'react'
import { analyzeApi, AnalyzeResponse } from '../services/analyzeApi'

interface UseAnalyzeFileReturn {
  analyze: (file: File) => Promise<AnalyzeResponse | null>
  loading: boolean
  result: AnalyzeResponse | null
  error: Error | null
  requiresConfirmation: boolean
  reset: () => void
}

const getConfidenceLevel = (score: number): 'high' | 'medium' | 'low' => {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

export function useAnalyzeFile(): UseAnalyzeFileReturn & {
  confidence: 'high' | 'medium' | 'low' | null
} {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const analyze = useCallback(async (file: File): Promise<AnalyzeResponse | null> => {
    setLoading(true)
    setError(null)

    try {
      const analysisResult = await analyzeApi.analyzeFile(file)
      setResult(analysisResult)
      return analysisResult
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error')
      setError(error)
      setResult(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setLoading(false)
    setResult(null)
    setError(null)
  }, [])

  const requiresConfirmation = result?.requires_confirmation ?? false
  const confidence = result ? getConfidenceLevel(result.confidence) : null

  return {
    analyze,
    loading,
    result,
    error,
    requiresConfirmation,
    confidence,
    reset,
  }
}

export default useAnalyzeFile
