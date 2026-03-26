export const OFFLINE_DB_NAME = 'gestiqcloud-offline'
export const OFFLINE_DB_VERSION = 3

export const OFFLINE_DB_STORES = {
  entity: 'offline-store',
  metadata: 'offline-metadata',
  auth: 'offline-auth',
} as const

export async function ensureOfflineDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(OFFLINE_DB_NAME, OFFLINE_DB_VERSION)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)

    request.onupgradeneeded = () => {
      const db = request.result
      for (const storeName of Object.values(OFFLINE_DB_STORES)) {
        if (!db.objectStoreNames.contains(storeName)) {
          db.createObjectStore(storeName)
        }
      }
    }
  })
}
