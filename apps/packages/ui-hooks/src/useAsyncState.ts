/**
 * Hook genérico para manejo de estado asíncrono
 */
import { useState, useCallback, useEffect } from 'react'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
  success: boolean
}

export interface UseAsyncStateConfig<T> {
  initialData?: T | null
  onSuccess?: (data: T) => void
  onError?: (error: string) => void
  resetOnSuccess?: boolean
  resetOnError?: boolean
}

export function useAsyncState<T = any>(config: UseAsyncStateConfig<T> = {}) {
  const {
    initialData = null,
    onSuccess,
    onError,
    resetOnSuccess = false,
    resetOnError = false
  } = config

  const [state, setState] = useState<AsyncState<T>>({
    data: initialData,
    loading: false,
    error: null,
    success: false
  })

  const execute = useCallback(async <R>(
    asyncFn: () => Promise<R>,
    options?: {
      onSuccess?: (data: R) => void
      onError?: (error: string) => void
      showLoading?: boolean
    }
  ): Promise<R | null> => {
    const {
      onSuccess: localOnSuccess,
      onError: localOnError,
      showLoading = true
    } = options || {}

    try {
      if (showLoading) {
        setState(prev => ({ ...prev, loading: true, error: null, success: false }))
      }

      const result = await asyncFn()

      setState(prev => ({
        ...prev,
        data: result as T,
        loading: false,
        error: null,
        success: true
      }))

      localOnSuccess?.(result as R)
      onSuccess?.(result as T)

      if (resetOnSuccess) {
        setTimeout(() => {
          setState(prev => ({ ...prev, success: false }))
        }, 2000)
      }

      return result as R
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Error desconocido'

      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
        success: false
      }))

      localOnError?.(errorMessage)
      onError?.(errorMessage)

      if (resetOnError) {
        setTimeout(() => {
          setState(prev => ({ ...prev, error: null }))
        }, 5000)
      }

      return null
    }
  }, [onSuccess, onError, resetOnSuccess, resetOnError])

  const reset = useCallback((options?: { keepData?: boolean }) => {
    const { keepData = false } = options || {}
    setState(prev => ({
      ...prev,
      data: keepData ? prev.data : null,
      loading: false,
      error: null,
      success: false
    }))
  }, [])

  const setData = useCallback((data: T | null) => {
    setState(prev => ({ ...prev, data }))
  }, [])

  const setLoading = useCallback((loading: boolean) => {
    setState(prev => ({ ...prev, loading }))
  }, [])

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error, success: false }))
  }, [])

  const setSuccess = useCallback((success: boolean) => {
    setState(prev => ({ ...prev, success }))
  }, [])

  return {
    ...state,
    execute,
    reset,
    setData,
    setLoading,
    setError,
    setSuccess
  }
}
