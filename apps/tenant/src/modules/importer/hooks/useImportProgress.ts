/**
 * Hook para monitorear progreso de importacion (polling HTTP)
 */
import { useEffect, useMemo, useState } from 'react'
import api from '../../../shared/api/client'
import { IMPORTS } from '@endpoints/imports'

export interface ImportProgress {
  current: number
  total: number
  status: 'idle' | 'processing' | 'completed' | 'error'
  message: string
  estimated_time_remaining?: number
}

export function useImportProgress(batchId: string | null) {
  const [progress, setProgress] = useState<ImportProgress>({
    current: 0,
    total: 0,
    status: 'idle',
    message: '',
  })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!batchId) {
      setProgress({ current: 0, total: 0, status: 'idle', message: '' })
      setError(null)
      return
    }

    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const poll = async () => {
      try {
        const { data } = await api.get<any>(IMPORTS.batches.status(batchId))
        if (cancelled) return

        const current = Number(data?.processed || 0)
        const total = Number(data?.total || 0)
        const status =
          (data?.status as ImportProgress['status']) ||
          (current >= total && total > 0 ? 'completed' : 'processing')

        setProgress({
          current,
          total,
          status,
          message: data?.message || '',
        })
        setError(null)

        if (status === 'completed' || status === 'error') return
      } catch (e: any) {
        setError(e?.message || 'Error obteniendo progreso')
      }

      timer = setTimeout(poll, 1000)
    }

    void poll()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [batchId])

  const progressPercent = useMemo(() => {
    if (!progress.total) return 0
    return Math.max(0, Math.min(100, Math.round((progress.current / progress.total) * 100)))
  }, [progress.current, progress.total])

  return {
    progress,
    progressPercent,
    isConnected: true,
    error,
  }
}
