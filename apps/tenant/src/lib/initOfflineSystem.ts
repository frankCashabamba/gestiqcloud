/**
 * Initialize Offline System
 *
 * Central entry point for setting up the complete offline infrastructure.
 * Call this once on app startup.
 */

import { initOfflineStore } from './offlineStore'
import { initSyncEventListener, getSyncManager } from './syncManager'
import { registerPOSSyncAdapters } from '@/modules/pos/offlineSync'
import { registerProductsSyncAdapter } from '@/modules/products/offlineSync'
import { registerCustomersSyncAdapter } from '@/modules/customers/offlineSync'
import { registerSalesSyncAdapter } from '@/modules/sales/offlineSync'
import { registerBillingSyncAdapter } from '@/modules/billing/offlineSync'

export async function initializeOfflineSystem() {
  try {
    console.log('[offline] Initializing offline system...')

    // Step 1: Initialize storage
    await initOfflineStore()
    console.log('[offline] Offline store initialized')

    // Step 2: Setup event listener
    initSyncEventListener()
    console.log('[offline] Sync event listener initialized')

    // Step 3: Register adapters
    const manager = getSyncManager()

    registerPOSSyncAdapters()
    registerProductsSyncAdapter()
    registerCustomersSyncAdapter()
    registerSalesSyncAdapter()
    registerBillingSyncAdapter()

    console.log(`[offline] ${manager.getAdapterCount()} sync adapters registered`)

    // Step 4: Start periodic sync check
    startPeriodicSyncCheck()

    console.log('[offline] Offline system fully initialized')
    return true
  } catch (error) {
    console.error('[offline] Failed to initialize offline system:', error)
    return false
  }
}

/**
 * Start periodic sync check when app detects online
 */
function startPeriodicSyncCheck() {
  // Auto-sync when coming online
  window.addEventListener('online', () => {
    console.log('[offline] Online detected - triggering sync')
    window.dispatchEvent(new CustomEvent('offline:sync-requested'))
  })

  // Periodic sync check every 5 minutes when online
  setInterval(() => {
    if (navigator.onLine) {
      window.dispatchEvent(new CustomEvent('offline:sync-requested'))
    }
  }, 5 * 60 * 1000)
}

/**
 * Check if offline system is ready
 */
export function isOfflineSystemReady(): boolean {
  try {
    const manager = getSyncManager()
    return manager.getAdapterCount() > 0
  } catch {
    return false
  }
}
