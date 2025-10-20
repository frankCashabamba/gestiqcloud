/**
 * ElectricSQL Configuration for Offline-First Sync (MVP-safe)
 *
 * In MVP we gate Electric behind a feature flag to avoid hard deps on SDK.
 */

export type ElectricDatabase = { sync: () => Promise<{ conflicts?: any[] }> } & Record<string, any>

// ElectricSQL sync URL (backend shapes endpoint)
const ELECTRIC_URL = (import.meta as any).env?.VITE_ELECTRIC_URL || 'ws://localhost:5133'
const DB_NAME = 'gestiqcloud_tenant.db'

let PGliteCtor: any = null
let electrifyFn: any = null

let electric: ElectricDatabase | null = null
let db: any | null = null

export async function initElectric(tenantId: string): Promise<ElectricDatabase> {
  if (electric) return electric

  const enabled = (import.meta as any).env?.VITE_ELECTRIC_ENABLED === '1'
  if (!enabled) {
    // No-op implementation to keep app functional
    electric = { sync: async () => ({ conflicts: [] }) }
    return electric as ElectricDatabase
  }

  try {
    // Lazy import to avoid bundling/type issues if SDK not installed
    const mod: any = await import('electric-sql/pglite')
    PGliteCtor = mod?.PGlite || mod?.default
    electrifyFn = mod?.electrify

    db = new PGliteCtor(DB_NAME)
    electric = await electrifyFn(db, ELECTRIC_URL, {
      auth: { bearerToken: `tenant_${tenantId}` },
      shapes: {
        products: { url: `/api/v1/electric/shapes`, params: { table: 'products' } },
        clients: { url: `/api/v1/electric/shapes`, params: { table: 'clients' } },
        pos_receipts: { url: `/api/v1/electric/shapes`, params: { table: 'pos_receipts' } },
      }
    })

    console.log('ElectricSQL initialized for tenant:', tenantId)
    return electric as ElectricDatabase
  } catch (error) {
    console.error('Failed to initialize ElectricSQL:', error)
    electric = { sync: async () => ({ conflicts: [] }) }
    return electric as ElectricDatabase
  }
}

export function getElectric(): ElectricDatabase | null {
  return electric
}

export function getLocalDb(): any | null {
  return db
}

export function isOnline(): boolean {
  return navigator.onLine
}

let onConflictCallback: ((conflicts: any[]) => void) | null = null
export function setConflictHandler(callback: (conflicts: any[]) => void) {
  onConflictCallback = callback
}

export function setupOnlineSync(tenantId: string) {
  window.addEventListener('online', async () => {
    console.log('Going online, starting sync...')
    try {
      const electric = await initElectric(tenantId)
      const result = await electric.sync()
      if (result.conflicts?.length && onConflictCallback) {
        const manualConflicts = result.conflicts.filter((c: any) => c.resolution === 'manual_review_required')
        if (manualConflicts.length) onConflictCallback(manualConflicts)
      }
      console.log('Sync completed')
    } catch (error) {
      console.error('Sync failed:', error)
    }
  })

  window.addEventListener('offline', () => {
    console.log('Going offline')
  })
}
