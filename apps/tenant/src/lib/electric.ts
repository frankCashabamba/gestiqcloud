/**
 * ElectricSQL Configuration for Offline-First Sync
 *
 * Sets up PGlite (local PostgreSQL) with Electric sync for offline capabilities.
 */

import { ElectricDatabase, electrify } from 'electric-sql/pglite'
import { PGlite } from '@electric-sql/pglite'

// ElectricSQL sync URL (backend shapes endpoint)
const ELECTRIC_URL = import.meta.env.VITE_ELECTRIC_URL || 'ws://localhost:5133'

// Database file name (stored in IndexedDB)
const DB_NAME = 'gestiqcloud_tenant.db'

let electric: ElectricDatabase | null = null
let db: PGlite | null = null

export async function initElectric(tenantId: string): Promise<ElectricDatabase> {
  if (electric) {
    return electric
  }

  try {
    // Initialize PGlite (local PostgreSQL in browser)
    db = new PGlite(DB_NAME)

    // Electrify the database for sync
    electric = await electrify(db, ELECTRIC_URL, {
      auth: {
        token: `tenant_${tenantId}`, // Simple auth token
      },
      shapes: {
        // Define shapes to sync (matches backend shapes)
        products: {
          url: `/api/v1/electric/shapes`,
          params: { table: 'products' }
        },
        clients: {
          url: `/api/v1/electric/shapes`,
          params: { table: 'clients' }
        },
        pos_receipts: {
          url: `/api/v1/electric/shapes`,
          params: { table: 'pos_receipts' }
        },
        // Add more shapes as needed
      }
    })

    console.log('✅ ElectricSQL initialized for tenant:', tenantId)
    return electric

  } catch (error) {
    console.error('❌ Failed to initialize ElectricSQL:', error)
    throw error
  }
}

export function getElectric(): ElectricDatabase | null {
  return electric
}

export function getLocalDb(): PGlite | null {
  return db
}

// Utility to check if we're online
export function isOnline(): boolean {
  return navigator.onLine
}

// Conflict handling callback
let onConflictCallback: ((conflicts: any[]) => void) | null = null

export function setConflictHandler(callback: (conflicts: any[]) => void) {
  onConflictCallback = callback
}

// Start sync when coming online
export function setupOnlineSync(tenantId: string) {
  window.addEventListener('online', async () => {
    console.log('🔄 Going online, starting sync...')
    try {
      const electric = await initElectric(tenantId)
      const result = await electric.sync()

      // Check for conflicts that need manual resolution
      if (result.conflicts && result.conflicts.length > 0) {
        const manualConflicts = result.conflicts.filter((c: any) =>
          c.resolution === 'manual_review_required'
        )

        if (manualConflicts.length > 0 && onConflictCallback) {
          onConflictCallback(manualConflicts)
        }
      }

      console.log('✅ Sync completed')
    } catch (error) {
      console.error('❌ Sync failed:', error)
    }
  })

  window.addEventListener('offline', () => {
    console.log('📴 Going offline')
  })
}
