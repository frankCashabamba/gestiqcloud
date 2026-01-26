/**
 * useOffline - Universal hook for offline-first operations
 * 
 * Replaces useOfflineSync (POS-only) with global offline management.
 * Handles online/offline detection, pending items, and sync triggering.
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { 
  getTotalPendingCount, 
  getMetadata, 
  EntityType, 
  initOfflineStore,
  clearAllOfflineData,
  getStatusCounts,
} from '../lib/offlineStore'

export interface UseOfflineReturn {
  isOnline: boolean
  totalPending: number
  syncStatus: Record<EntityType, number>
  statusCounts: Record<string, number>
  lastSyncAt: Date | null
  syncing: boolean
  syncNow: (entity?: EntityType) => Promise<void>
  clearPending: () => Promise<void>
}

export default function useOffline(autoSyncIntervalMs: number = 30000): UseOfflineReturn {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [totalPending, setTotalPending] = useState(0)
  const [syncStatus, setSyncStatus] = useState<Record<EntityType, number>>({})
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({})
  const [lastSyncAt, setLastSyncAt] = useState<Date | null>(null)
  const [syncing, setSyncing] = useState(false)
  const storeInitialized = useRef(false)

  // Initialize offline store on mount
  useEffect(() => {
    if (!storeInitialized.current) {
      storeInitialized.current = true
      initOfflineStore().catch(err => console.error('Failed to init offline store:', err))
    }
  }, [])

  // Detect online/offline changes
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      console.log('🟢 Going online - triggering sync')
    }

    const handleOffline = () => {
      setIsOnline(false)
      console.log('🔴 Going offline')
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Update pending count periodically
  useEffect(() => {
    const updateCounts = async () => {
      try {
        const pending = await getTotalPendingCount()
        setTotalPending(pending)

        // Get metadata for each entity type
        const entities: EntityType[] = ['product', 'customer', 'sale', 'receipt', 'purchase', 'shift', 'invoice']
        const statuses: Record<EntityType, number> = {} as any
        
        for (const entity of entities) {
          try {
            const meta = await getMetadata(entity)
            statuses[entity] = meta?.pendingCount ?? 0
          } catch (err) {
            // Silently handle individual entity metadata errors
            statuses[entity] = 0
          }
        }
        
        setSyncStatus(statuses)
        try {
          const counts = await getStatusCounts()
          setStatusCounts(counts)
        } catch {
          setStatusCounts({})
        }
      } catch (error) {
        // Silently handle offline store errors - offline feature is optional
        console.debug('Offline counts unavailable:', error)
        setTotalPending(0)
        setSyncStatus({})
        setStatusCounts({})
      }
    }

    updateCounts()
    const interval = setInterval(updateCounts, 5000)

    return () => clearInterval(interval)
  }, [])

  // Auto-sync when online
  useEffect(() => {
    if (!isOnline || syncing) return

    const interval = setInterval(() => {
      // Emit event for SyncManager to handle
      window.dispatchEvent(new CustomEvent('offline:sync-requested'))
    }, autoSyncIntervalMs)

    return () => clearInterval(interval)
  }, [isOnline, syncing, autoSyncIntervalMs])

  const syncNow = useCallback(async (entity?: EntityType) => {
    if (!isOnline || syncing) return

    setSyncing(true)
    try {
      if (entity) {
        console.log(`Syncing entity: ${entity}`)
        window.dispatchEvent(new CustomEvent('offline:sync-requested', { detail: { entity } }))
      } else {
        console.log('Syncing all entities')
        window.dispatchEvent(new CustomEvent('offline:sync-requested'))
      }

      // Wait a bit for sync to complete
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      setLastSyncAt(new Date())
      const pending = await getTotalPendingCount()
      setTotalPending(pending)
    } catch (error) {
      console.error('Sync error:', error)
    } finally {
      setSyncing(false)
    }
  }, [isOnline, syncing])

  const clearPending = useCallback(async () => {
    if (!confirm('Limpiar todos los cambios pendientes? Esta accion no se puede deshacer.')) {
      return
    }

    try {
      await clearAllOfflineData()
      setTotalPending(0)
      setSyncStatus({} as any)
    } catch (error) {
      console.error('Failed to clear pending:', error)
    }
  }, [])

  return {
    isOnline,
    totalPending,
    syncStatus,
    statusCounts,
    lastSyncAt,
    syncing,
    syncNow,
    clearPending,
  }
}
