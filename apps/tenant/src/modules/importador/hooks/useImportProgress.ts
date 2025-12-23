/**
 * useImportProgress - Hook para conectar WebSocket de progreso de importación
 * Sprint 3: Real-time progress updates durante importación
 */
import { useState, useEffect, useRef, useCallback } from 'react'

export interface ProgressUpdate {
  batchId: string
  rowsProcessed: number
  totalRows: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  currentStep: string
  errorCount: number
  speed: number // rows/sec
  estimatedTime: number // seconds
  errors?: Array<{ row: number; message: string }>
}

interface UseImportProgressOptions {
  batchId?: string
  token?: string
  onComplete?: () => void
  onError?: (error: string) => void
}

export const useImportProgress = ({
  batchId,
  token,
  onComplete,
  onError
}: UseImportProgressOptions = {}) => {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback((id: string) => {
    if (!id) return

    // Construir URL del WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/tenant/imports/batches/${id}/progress?token=${token}`

    try {
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        setIsConnected(true)
        setError(null)
      }

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ProgressUpdate
          setProgress(data)

          if (data.status === 'completed') {
            onComplete?.()
          } else if (data.status === 'failed') {
            const errorMsg = data.errors?.[0]?.message || 'Importación fallida'
            setError(errorMsg)
            onError?.(errorMsg)
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      wsRef.current.onerror = () => {
        setError('Conexión WebSocket perdida')
        onError?.('Conexión WebSocket perdida')
      }

      wsRef.current.onclose = () => {
        setIsConnected(false)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error conectando WebSocket'
      setError(errorMsg)
      onError?.(errorMsg)
    }
  }, [token, onComplete, onError])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  useEffect(() => {
    if (batchId) {
      connect(batchId)
    }

    return () => {
      disconnect()
    }
  }, [batchId, connect, disconnect])

  const progressPercent = progress
    ? Math.round((progress.rowsProcessed / progress.totalRows) * 100)
    : 0

  return {
    progress,
    progressPercent,
    isConnected,
    error,
    connect,
    disconnect
  }
}
