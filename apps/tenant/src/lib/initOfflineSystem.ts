/**
 * Initialize Offline System
 *
 * Central entry point for setting up the complete offline infrastructure.
 * Call this once on app startup.
 */

import { initOfflineStore } from './offlineStore'
import { initSyncEventListener, getSyncManager } from './syncManager'
import { registerAllOfflineAdapters } from './offlineAdapters'

export async function initializeOfflineSystem() {
  try {
    if (import.meta.env.DEV) { console.log('[offline] Initializing offline system...') }

    // Step 1: Initialize storage
    await initOfflineStore()
    if (import.meta.env.DEV) { console.log('[offline] Offline store initialized') }

    // Step 2: Setup event listener
    initSyncEventListener()
    if (import.meta.env.DEV) { console.log('[offline] Sync event listener initialized') }

    // Step 3: Register adapters
    const manager = getSyncManager()

    registerAllOfflineAdapters()

    if (import.meta.env.DEV) { console.log(`[offline] ${manager.getAdapterCount()} sync adapters registered`) }

    // Step 4: Start periodic sync check
    startPeriodicSyncCheck()

    if (import.meta.env.DEV) { console.log('[offline] Offline system fully initialized') }
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
    if (import.meta.env.DEV) { console.log('[offline] Online detected - triggering sync') }
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
