/**
 * ElectricSQL Configuration for Offline-First Sync (MVP-safe)
 *
 * In MVP we gate Electric behind a feature flag to avoid hard deps on SDK.
 *
 * Environment Variables (REQUIRED if VITE_ELECTRIC_ENABLED=1):
 * - VITE_ELECTRIC_URL: WebSocket URL for ElectricSQL (e.g., ws://electric.internal:3000)
 * - VITE_ELECTRIC_ENABLED: Set to "1" to enable ElectricSQL sync
 */

export type ElectricDatabase = { sync: () => Promise<{ conflicts?: any[] }> } & Record<string, any>

// ElectricSQL sync URL (backend shapes endpoint)
// Must be configured via VITE_ELECTRIC_URL env var
const ELECTRIC_URL = (import.meta as any).env?.VITE_ELECTRIC_URL
const ELECTRIC_ENABLED = (import.meta as any).env?.VITE_ELECTRIC_ENABLED === '1'
const DB_NAME = 'gestiqcloud_tenant.db'
const IS_PRODUCTION = (import.meta as any).env?.MODE === 'production'

// Validation on module load
if (ELECTRIC_ENABLED && !ELECTRIC_URL) {
  const errorMsg = (
    '❌ CRITICAL: VITE_ELECTRIC_ENABLED=1 but VITE_ELECTRIC_URL is not configured.\n' +
    'Please set VITE_ELECTRIC_URL environment variable.\n' +
    'Example: VITE_ELECTRIC_URL=ws://electric.internal:3000'
  )
  console.error(errorMsg)
  if (IS_PRODUCTION) {
    throw new Error('ElectricSQL configuration error: VITE_ELECTRIC_URL is required when VITE_ELECTRIC_ENABLED=1')
  }
}

if (!ELECTRIC_URL && !ELECTRIC_ENABLED) {
  console.debug('ℹ️  ElectricSQL is disabled (VITE_ELECTRIC_ENABLED not set)')
}

let PGliteCtor: any = null
let electrifyFn: any = null

let electric: ElectricDatabase | null = null
let db: any | null = null

export async function initElectric(tenantId: string): Promise<ElectricDatabase> {
  if (electric) return electric

  // Validation: if enabled but no URL, fail in production
  if (ELECTRIC_ENABLED && !ELECTRIC_URL) {
    const errorMsg = 'ElectricSQL enabled but VITE_ELECTRIC_URL is not configured'
    console.error(`❌ ${errorMsg}`)
    if (IS_PRODUCTION) {
      throw new Error(errorMsg)
    }
    // In development, return no-op
    electric = { sync: async () => ({ conflicts: [] }) }
    return electric as ElectricDatabase
  }

  // If not enabled, return no-op
  if (!ELECTRIC_ENABLED) {
    console.debug('ℹ️  ElectricSQL not enabled (VITE_ELECTRIC_ENABLED != "1")')
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
