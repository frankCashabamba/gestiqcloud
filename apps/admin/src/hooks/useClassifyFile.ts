// src/hooks/useClassifyFile.ts
// Hook para clasificar archivos de importación

import { useState, useCallback } from 'react'
import { classifyFile, ClassifyResponse } from '../services/classify'

export interface UseClassifyFileState {
  loading: boolean
  error: Error | null
  result: ClassifyResponse | null
  confidence: 'high' | 'medium' | 'low' | null
}

/**
 * Hook para clasificar un archivo
 * Maneja estados de carga, error y resultado
 */
export const useClassifyFile = () => {
  const [state, setState] = useState<UseClassifyFileState>({
    loading: false,
    error: null,
    result: null,
    confidence: null,
  })

  const classify = useCallback(
    async (file: File, useAI = true) => {
      setState((s) => ({ ...s, loading: true, error: null }))
      try {
        const result = await classifyFile(file, useAI)

        // Determinar nivel de confianza
        let confidence: 'high' | 'medium' | 'low' = 'low'
        if (result.confidence >= 0.8) {
          confidence = 'high'
        } else if (result.confidence >= 0.6) {
          confidence = 'medium'
        }

        setState((s) => ({
          ...s,
          loading: false,
          result,
          confidence,
          error: null,
        }))

        return result
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error))
        setState((s) => ({
          ...s,
          loading: false,
          error: err,
          result: null,
          confidence: null,
        }))
        throw err
      }
    },
    []
  )

  const reset = useCallback(() => {
    setState({
      loading: false,
      error: null,
      result: null,
      confidence: null,
    })
  }, [])

  return {
    ...state,
    classify,
    reset,
  }
}
