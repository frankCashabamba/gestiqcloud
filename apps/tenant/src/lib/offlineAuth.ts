/**
 * OfflineAuth - Offline authentication using IndexedDB
 *
 * Caches user credentials (hashed) so the app can authenticate
 * when the network is unavailable. Credentials expire after 30 days.
 */

import { createStore, get, set, del, entries } from 'idb-keyval'
import { ensureOfflineDatabase, OFFLINE_DB_NAME, OFFLINE_DB_STORES } from './offlineDb'

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

interface OfflineSessionSnapshot {
  token: string
  profile: OfflineProfile
  savedAt: number
  tokenPayload: Record<string, unknown>
}

const DB_NAME = OFFLINE_DB_NAME
const STORE_NAME = OFFLINE_DB_STORES.auth
const OFFLINE_SESSION_KEY = 'offline_session_tenant'
const MAX_CREDENTIAL_AGE_MS = 30 * 24 * 60 * 60 * 1000
const SESSION_SNAPSHOT_KEY = '__offline_session__'
const CREDENTIAL_KEY_PREFIX = 'cred:'

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

function credentialKey(identifier: string): string {
  return `${CREDENTIAL_KEY_PREFIX}${identifier}`
}

function isFresh(savedAt?: number): boolean {
  return typeof savedAt === 'number' && Date.now() - savedAt <= MAX_CREDENTIAL_AGE_MS
}

function isStoredCredentials(value: unknown): value is StoredCredentials {
  if (!value || typeof value !== 'object') return false
  const record = value as Partial<StoredCredentials>
  return (
    typeof record.identifier === 'string' &&
    typeof record.passwordHash === 'string' &&
    typeof record.salt === 'string' &&
    typeof record.token === 'string' &&
    !!record.profile &&
    typeof record.savedAt === 'number'
  )
}

function isSessionSnapshot(value: unknown): value is OfflineSessionSnapshot {
  if (!value || typeof value !== 'object') return false
  const snapshot = value as Partial<OfflineSessionSnapshot>
  return typeof snapshot.token === 'string' && !!snapshot.profile && typeof snapshot.savedAt === 'number'
}

async function getSnapshot(store: ReturnType<typeof createStore>): Promise<OfflineSessionSnapshot | null> {
  const snapshot = await get(SESSION_SNAPSHOT_KEY, store)
  if (!isSessionSnapshot(snapshot)) return null
  if (!isFresh(snapshot.savedAt)) {
    await del(SESSION_SNAPSHOT_KEY, store)
    return null
  }
  return snapshot
}

async function listCredentialEntries(
  store: ReturnType<typeof createStore>
): Promise<Array<[IDBValidKey, StoredCredentials]>> {
  const allEntries = await entries(store)
  return (allEntries as Array<[IDBValidKey, unknown]>)
    .filter(([key, value]) => key !== SESSION_SNAPSHOT_KEY && isStoredCredentials(value))
    .map(([key, value]) => [key, value as StoredCredentials])
}

async function getStore() {
  if (!authStore) {
    try {
      if (!dbInitialized) {
        await ensureOfflineDatabase()
        dbInitialized = true
      }
      authStore = createStore(DB_NAME, STORE_NAME)
      if (import.meta.env.DEV) { console.log('[offline-auth] Store initialized') }
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

  await set(credentialKey(identifier), credentials, store)
  try { await del(identifier, store) } catch {}
  await saveOfflineSessionSnapshot(token, profile)
  if (import.meta.env.DEV) { console.log('[offline-auth] Credentials saved for:', identifier) }
}

export async function saveOfflineSessionSnapshot(
  token: string,
  profile: OfflineProfile
): Promise<void> {
  const store = await getStore()
  const snapshot: OfflineSessionSnapshot = {
    token,
    profile,
    savedAt: Date.now(),
    tokenPayload: extractTokenPayload(token),
  }
  await set(SESSION_SNAPSHOT_KEY, snapshot, store)
}

export async function verifyOfflineCredentials(
  identifier: string,
  password: string
): Promise<{ token: string; profile: OfflineProfile; isOfflineSession: true } | null> {
  const store = await getStore()
  const credentials =
    ((await get(credentialKey(identifier), store)) as StoredCredentials | undefined) ||
    ((await get(identifier, store)) as StoredCredentials | undefined)

  if (!credentials) return null

  // Check if credentials are expired
  if (!isFresh(credentials.savedAt)) {
    console.warn('[offline-auth] Credentials expired for:', identifier)
    await del(credentialKey(identifier), store)
    try { await del(identifier, store) } catch {}
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
  const snapshot = await getSnapshot(store)
  if (snapshot?.profile) return snapshot.profile

  const allEntries = await listCredentialEntries(store)

  if (allEntries.length === 0) return null

  // Return the most recently saved profile
  const sorted = allEntries.sort(([, a], [, b]) => b.savedAt - a.savedAt)
  return sorted[0][1].profile
}

export async function getOfflineToken(): Promise<string | null> {
  const store = await getStore()
  const snapshot = await getSnapshot(store)
  if (snapshot?.token) return snapshot.token

  const allEntries = await listCredentialEntries(store)

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

  if (import.meta.env.DEV) { console.log('[offline-auth] All credentials cleared') }
}

export async function clearOfflineSessionSnapshot(): Promise<void> {
  const store = await getStore()
  await del(SESSION_SNAPSHOT_KEY, store)
}

// =============================================================================
// Status Checks
// =============================================================================

export async function hasOfflineCredentials(identifier?: string): Promise<boolean> {
  const store = await getStore()

  if (identifier) {
    const credentials =
      ((await get(credentialKey(identifier), store)) as StoredCredentials | undefined) ||
      ((await get(identifier, store)) as StoredCredentials | undefined)
    if (!credentials) return false
    // Also check expiry
    return isFresh(credentials.savedAt)
  }

  const snapshot = await getSnapshot(store)
  if (snapshot) return true

  const allEntries = await listCredentialEntries(store)
  return allEntries.some(([, cred]) => isFresh(cred.savedAt))
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
