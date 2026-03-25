/**
 * OfflineAuth - Offline authentication using IndexedDB
 *
 * Caches user credentials (hashed) so the app can authenticate
 * when the network is unavailable. Credentials expire after 30 days.
 */

import { createStore, get, set, del, entries } from 'idb-keyval'

export interface OfflineProfile {
  user_id: string
  username?: string
  tenant_id: string
  empresa_slug?: string
  es_admin_empresa?: boolean
  roles?: string[]
  base_currency?: string
  permisos?: Record<string, unknown>
  permissions?: Record<string, unknown>
}

interface StoredCredentials {
  identifier: string
  passwordHash: string
  salt: string
  token: string
  profile: OfflineProfile
  savedAt: number
  tokenPayload: Record<string, unknown>
}

const DB_NAME = 'gestiqcloud-offline'
const STORE_NAME = 'offline-auth'
const OFFLINE_SESSION_KEY = 'offline_session_tenant'
const MAX_CREDENTIAL_AGE_MS = 30 * 24 * 60 * 60 * 1000

let authStore: ReturnType<typeof createStore> | null = null
let dbInitialized = false

// =============================================================================
// Crypto Helpers
// =============================================================================

async function hashPassword(password: string, salt: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(salt + password)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hashBuffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

function generateSalt(): string {
  const array = new Uint8Array(16)
  crypto.getRandomValues(array)
  return Array.from(array)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

function extractTokenPayload(token: string): Record<string, unknown> {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return {}
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return {}
  }
}

// =============================================================================
// Database Init
// =============================================================================

async function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 2)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }
  })
}

async function getStore() {
  if (!authStore) {
    try {
      if (!dbInitialized) {
        await openDatabase()
        dbInitialized = true
      }
      authStore = createStore(DB_NAME, STORE_NAME)
      console.log('[offline-auth] Store initialized')
    } catch (error) {
      console.error('[offline-auth] Failed to initialize store:', error)
      throw error
    }
  }
  return authStore!
}

// =============================================================================
// Credential Management
// =============================================================================

export async function saveCredentialsForOffline(
  identifier: string,
  password: string,
  token: string,
  profile: OfflineProfile
): Promise<void> {
  const store = await getStore()
  const salt = generateSalt()
  const passwordHash = await hashPassword(password, salt)
  const tokenPayload = extractTokenPayload(token)

  const credentials: StoredCredentials = {
    identifier,
    passwordHash,
    salt,
    token,
    profile,
    savedAt: Date.now(),
    tokenPayload,
  }

  await set(identifier, credentials, store)
  console.log('[offline-auth] Credentials saved for:', identifier)
}

export async function verifyOfflineCredentials(
  identifier: string,
  password: string
): Promise<{ token: string; profile: OfflineProfile; isOfflineSession: true } | null> {
  const store = await getStore()
  const credentials = (await get(identifier, store)) as StoredCredentials | undefined

  if (!credentials) return null

  // Check if credentials are expired
  if (Date.now() - credentials.savedAt > MAX_CREDENTIAL_AGE_MS) {
    console.warn('[offline-auth] Credentials expired for:', identifier)
    await del(identifier, store)
    return null
  }

  const hash = await hashPassword(password, credentials.salt)
  if (hash !== credentials.passwordHash) return null

  return {
    token: credentials.token,
    profile: credentials.profile,
    isOfflineSession: true,
  }
}

// =============================================================================
// Cached Data Access
// =============================================================================

export async function getOfflineProfile(): Promise<OfflineProfile | null> {
  const store = await getStore()
  const allEntries = (await entries(store)) as Array<[IDBValidKey, StoredCredentials]>

  if (allEntries.length === 0) return null

  // Return the most recently saved profile
  const sorted = allEntries.sort(([, a], [, b]) => b.savedAt - a.savedAt)
  return sorted[0][1].profile
}

export async function getOfflineToken(): Promise<string | null> {
  const store = await getStore()
  const allEntries = (await entries(store)) as Array<[IDBValidKey, StoredCredentials]>

  if (allEntries.length === 0) return null

  const sorted = allEntries.sort(([, a], [, b]) => b.savedAt - a.savedAt)
  return sorted[0][1].token
}

// =============================================================================
// Cleanup
// =============================================================================

export async function clearOfflineCredentials(): Promise<void> {
  const store = await getStore()
  const allEntries = await entries(store)

  for (const [key] of allEntries) {
    await del(key, store)
  }

  console.log('[offline-auth] All credentials cleared')
}

// =============================================================================
// Status Checks
// =============================================================================

export async function hasOfflineCredentials(identifier?: string): Promise<boolean> {
  const store = await getStore()

  if (identifier) {
    const credentials = (await get(identifier, store)) as StoredCredentials | undefined
    if (!credentials) return false
    // Also check expiry
    return Date.now() - credentials.savedAt <= MAX_CREDENTIAL_AGE_MS
  }

  const allEntries = (await entries(store)) as Array<[IDBValidKey, StoredCredentials]>
  return allEntries.some(([, cred]) => Date.now() - cred.savedAt <= MAX_CREDENTIAL_AGE_MS)
}

export function isOfflineSession(): boolean {
  return sessionStorage.getItem(OFFLINE_SESSION_KEY) === 'true'
}

export function markOfflineSession(): void {
  sessionStorage.setItem(OFFLINE_SESSION_KEY, 'true')
}

export function markOnlineSession(): void {
  sessionStorage.removeItem(OFFLINE_SESSION_KEY)
}
