/**
 * Hook para monitorear progreso de importación (polling HTTP)
 */

import { useEffect, useState } from 'react'
import api from '../../../shared/api/client'

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
        message: ''
    })

    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!batchId) {
            setProgress({ current: 0, total: 0, status: 'idle', message: '' })
            return
        }

        let cancelled = false
        let timer: any
        const poll = async () => {
            try {
                const { data } = await api.get<any>(`/api/v1/imports/batches/${batchId}/status`)
                if (cancelled) return
                const current = Number(data?.processed || 0)
                const total = Number(data?.total || 0)
                const status = (data?.status as ImportProgress['status']) || (current >= total && total > 0 ? 'completed' : 'processing')
                setProgress({
                    current,
                    total,
                    status,
                    message: data?.message || ''
                })
                if (status === 'completed' || status === 'error') return
            } catch (e: any) {
                setError(e?.message || 'Error obteniendo progreso')
            }
            timer = setTimeout(poll, 1000)
        }
        poll()
        return () => { cancelled = true; if (timer) clearTimeout(timer) }
    }, [batchId])

    return { progress, error }
}
