/**
 * Service Worker - TPV Offline Support
 */

const CACHE_NAME = 'tpv-v1'
const API_CACHE = 'tpv-api-v1'

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
]

// Install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS)
    })
  )
  self.skipWaiting()
})

// Activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME && key !== API_CACHE) {
            return caches.delete(key)
          }
        })
      )
    })
  )
  self.clients.claim()
})

// Fetch
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache products
          if (url.pathname.includes('/products')) {
            const cloned = response.clone()
            caches.open(API_CACHE).then((cache) => {
              cache.put(request, cloned)
            })
          }
          return response
        })
        .catch(() => {
          // Offline: return cached
          return caches.match(request)
        })
    )
    return
  }

  // Static assets
  event.respondWith(
    caches.match(request).then((cached) => {
      return cached || fetch(request)
    })
  )
})

// Background Sync (queue pending sales)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-sales') {
    event.waitUntil(syncPendingSales())
  }
})

async function syncPendingSales() {
  // TODO: Implementar sync de ventas pendientes
  console.log('Syncing pending sales...')
}
