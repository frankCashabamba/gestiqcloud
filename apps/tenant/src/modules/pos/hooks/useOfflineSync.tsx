/**
 * useOfflineSync - Hook para sincronización automática de tickets offline
 */
import { useEffect, useState, useCallback } from 'react'
import { syncOfflineReceipts } from '../services'

interface OutboxItem {
    id: string
    timestamp: string
    payload: any
    retries: number
}

export default function useOfflineSync(intervalMs: number = 30000) {
    const [isOnline, setIsOnline] = useState(navigator.onLine)
    const [pendingCount, setPendingCount] = useState(0)
    const [lastSyncAt, setLastSyncAt] = useState<Date | null>(null)
    const [syncing, setSyncing] = useState(false)

    // Detectar cambios de conectividad
    useEffect(() => {
        const handleOnline = () => {
            setIsOnline(true)
            // Sincronizar inmediatamente cuando vuelve online
            syncNow()
        }

        const handleOffline = () => {
            setIsOnline(false)
        }

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    // Sincronización periódica
    useEffect(() => {
        const interval = setInterval(() => {
            if (isOnline) {
                syncNow()
            }
        }, intervalMs)

        return () => clearInterval(interval)
    }, [isOnline, intervalMs])

    // Contar pendientes
    useEffect(() => {
        const updateCount = () => {
            const outbox = getOutbox()
            setPendingCount(outbox.length)
        }

        updateCount()
        const interval = setInterval(updateCount, 5000)

        return () => clearInterval(interval)
    }, [])

    const getOutbox = (): OutboxItem[] => {
        try {
            const data = localStorage.getItem('pos_outbox')
            return data ? JSON.parse(data) : []
        } catch {
            return []
        }
    }

    const setOutbox = (items: OutboxItem[]) => {
        localStorage.setItem('pos_outbox', JSON.stringify(items))
        setPendingCount(items.length)
    }

    const syncNow = useCallback(async () => {
        if (!isOnline || syncing) return

        setSyncing(true)
        try {
            await syncOfflineReceipts()
            setLastSyncAt(new Date())

            // Actualizar contador
            const outbox = getOutbox()
            setPendingCount(outbox.length)
        } catch (error) {
            console.error('Sync failed:', error)
        } finally {
            setSyncing(false)
        }
    }, [isOnline, syncing])

    const clearOutbox = useCallback(() => {
        if (confirm('¿Limpiar todos los tickets pendientes? Esta acción no se puede deshacer.')) {
            localStorage.removeItem('pos_outbox')
            setPendingCount(0)
        }
    }, [])

    const retryFailed = useCallback(async () => {
        const outbox = getOutbox()
        const failed = outbox.filter((item) => item.retries > 3)

        if (failed.length === 0) {
            alert('No hay tickets fallidos para reintentar')
            return
        }

        // Resetear retries
        const updated = outbox.map((item) => ({
            ...item,
            retries: 0
        }))
        setOutbox(updated)

        // Reintentar sync
        await syncNow()
    }, [syncNow])

    return {
        isOnline,
        pendingCount,
        lastSyncAt,
        syncing,
        syncNow,
        clearOutbox,
        retryFailed
    }
}
