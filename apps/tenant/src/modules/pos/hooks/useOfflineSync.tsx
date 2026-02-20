import { useCallback, useEffect, useState } from 'react'
import { addToOutbox } from '../services'
import { retryFailedReceipts } from '../offlineSync'
import useOffline from '../../../hooks/useOffline'
import { clearEntity } from '../../../lib/offlineStore'
import { useToast } from '../../../shared/toast'

interface LegacyOutboxItem {
  id: string
  timestamp: string
  payload: any
  retries?: number
}

export default function useOfflineSync(intervalMs: number = 30000) {
  const toast = useToast()
  const { isOnline, syncStatus, syncNow: globalSyncNow } = useOffline(intervalMs)
  const pendingCount = syncStatus.receipt ?? 0
  const [lastSyncAt, setLastSyncAt] = useState<Date | null>(null)
  const [syncing, setSyncing] = useState(false)

  const getLegacyOutbox = (): LegacyOutboxItem[] => {
    try {
      const data = localStorage.getItem('pos_outbox')
      return data ? JSON.parse(data) : []
    } catch {
      return []
    }
  }

  useEffect(() => {
    let mounted = true
    const migrateLegacyOutbox = async () => {
      const legacyItems = getLegacyOutbox()
      if (!legacyItems.length) return

      for (const item of legacyItems) {
        if (!mounted) return
        await addToOutbox(item.payload)
      }
      localStorage.removeItem('pos_outbox')
    }

    migrateLegacyOutbox().catch((error) => console.error('Legacy POS outbox migration failed:', error))
    return () => { mounted = false }
  }, [])

  const syncNow = useCallback(async () => {
    if (!isOnline || syncing) return
    setSyncing(true)
    try {
      await globalSyncNow('receipt')
      setLastSyncAt(new Date())
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }, [isOnline, syncing, globalSyncNow])

  useEffect(() => {
    const handleOnline = () => { syncNow() }
    window.addEventListener('online', handleOnline)
    return () => {
      window.removeEventListener('online', handleOnline)
    }
  }, [syncNow])

  const clearOutbox = useCallback(() => {
    toast.warning('¿Limpiar todos los tickets pendientes? Esta acción no se puede deshacer.', {
      action: {
        label: 'Confirmar',
        onClick: async () => {
          await clearEntity('receipt')
          toast.success('Tickets pendientes eliminados')
        },
      },
    })
  }, [toast])

  const retryFailed = useCallback(async () => {
    await retryFailedReceipts()
    await syncNow()
  }, [syncNow])

  return {
    isOnline,
    pendingCount,
    lastSyncAt,
    syncing,
    syncNow,
    clearOutbox,
    retryFailed,
  }
}
