/* Service Worker Core - Shared between Admin & Company */
import { precacheAndRoute } from 'workbox-precaching'
import { clientsClaim } from 'workbox-core'
import { createStore, set, del, entries } from 'idb-keyval'

// Injected by workbox at build time
// eslint-disable-next-line no-undef
precacheAndRoute(self.__WB_MANIFEST || [])

self.skipWaiting()
clientsClaim()

const RUNTIME_CACHE = 'runtime-v1'
const OFFLINE_URL = '/offline.html'
const OUTBOX_DB = createStore('pwa-store', 'outbox')
const BUILD_ID = __APP_BUILD_ID__
const APP_VERSION = __APP_VERSION__
const SENSITIVE_API = [/\/api\/.*auth/i, /\/api\/.*token/i, /\/api\/.*profile/i, /\/api\/.*\/me(\/|$)/i]
const MAX_BACKOFF_MS = 5 * 60 * 1000 // 5 min cap
const BASE_BACKOFF_MS = 2000

// Configuration (can be overridden by apps)
const config = {
  skipTelemetry: true, // Skip telemetry from outbox queue
  maxAttempts: 5, // Max retry attempts before discarding
}

function isNavRequest(req) {
  return req.mode === 'navigate' || (req.method === 'GET' && req.headers.get('accept')?.includes('text/html'))
}

function isAsset(req) {
  const url = new URL(req.url)
  return url.pathname.startsWith('/assets/') || /\.(js|css|png|jpg|svg|woff2?)$/i.test(url.pathname)
}

function isApi(req) {
  const url = new URL(req.url)
  return url.pathname.startsWith('/api/')
}

function isCacheableApiResponse(res) {
  const cc = res.headers.get('Cache-Control') || ''
  if (/no-store|private/i.test(cc)) return false
  return /public/i.test(cc)
}

async function queueRequest(request) {
  // Skip telemetry from outbox (never queue telemetry)
  if (config.skipTelemetry) {
    const url = new URL(request.url)
    if (url.pathname.includes('/telemetry')) {
      return
    }
  }

  const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
  const headers = {}
  request.headers.forEach((v, k) => { headers[k] = v })
  let body = null
  try {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      body = await request.clone().arrayBuffer()
    }
  } catch (_) {}
  const item = {
    id,
    url: request.url,
    method: request.method,
    headers,
    body,
    createdAt: Date.now(),
    attempts: 0,
    nextAttemptAt: Date.now(),
  }
  await set(id, item, OUTBOX_DB)
  try {
    const clientsList = await self.clients.matchAll({ type: 'window' })
    clientsList.forEach((c) => c.postMessage({ type: 'OUTBOX_QUEUED' }))
  } catch {}
  try { await self.registration.sync.register('sync-api') } catch (_) {
    flushQueue()
  }
}

async function flushQueue() {
  const items = await entries(OUTBOX_DB)
  let ok = 0
  let fail = 0
  let deferred = 0
  let discarded = 0

  for (const [key, item] of items) {
    // Discard items that have failed too many times
    if ((item.attempts || 0) >= config.maxAttempts) {
      await del(key, OUTBOX_DB)
      discarded += 1
      continue
    }

    if (Date.now() < (item.nextAttemptAt || 0)) { deferred += 1; continue }

    try {
      const init = {
        method: item.method,
        headers: item.headers,
        body: item.body ? new Uint8Array(item.body) : undefined,
        credentials: 'include',
        mode: 'cors',
      }
      const res = await fetch(item.url, init)
      if (res.ok) {
        await del(key, OUTBOX_DB)
        ok += 1
      } else {
        const attempts = (item.attempts || 0) + 1
        const delay = Math.min(MAX_BACKOFF_MS, BASE_BACKOFF_MS * Math.pow(2, attempts - 1))
        item.attempts = attempts
        item.nextAttemptAt = Date.now() + delay
        await set(key, item, OUTBOX_DB)
        fail += 1
      }
    } catch (_) {
      const attempts = (item.attempts || 0) + 1
      const delay = Math.min(MAX_BACKOFF_MS, BASE_BACKOFF_MS * Math.pow(2, attempts - 1))
      item.attempts = attempts
      item.nextAttemptAt = Date.now() + delay
      await set(key, item, OUTBOX_DB)
      fail += 1
    }
  }

  try {
    const clientsList = await self.clients.matchAll({ type: 'window' })
    clientsList.forEach((c) => c.postMessage({
      type: 'OUTBOX_SYNCED',
      ok,
      fail,
      deferred,
      discarded
    }))
  } catch {}

  const remaining = (await entries(OUTBOX_DB)).length
  if (remaining > 0) {
    try { await self.registration.sync.register('sync-api') } catch {}
  }
}

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-api') {
    event.waitUntil(flushQueue())
  }
})

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SYNC_NOW') {
    event.waitUntil(flushQueue())
  }
})

self.addEventListener('fetch', (event) => {
  const { request } = event

  if (isNavRequest(request)) {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html').then((r) => r || caches.match(OFFLINE_URL)))
    )
    return
  }

  if (isAsset(request)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached
        return fetch(request)
          .then((res) => {
            const resClone = res.clone()
            caches.open(RUNTIME_CACHE).then((c) => c.put(request, resClone))
            return res
          })
          .catch(() => caches.match(OFFLINE_URL))
      })
    )
    return
  }

  if (isApi(request)) {
    const url = new URL(request.url)
    const isTelemetry = config.skipTelemetry && url.pathname.includes('/telemetry')

    if (request.method === 'GET') {
      event.respondWith(
        fetch(withVersionHeader(request))
          .then((res) => {
            const sensitive = SENSITIVE_API.some((re) => re.test(url.pathname))
            if (!sensitive && isCacheableApiResponse(res)) {
              const resClone = res.clone()
              caches.open(RUNTIME_CACHE).then((c) => c.put(request, resClone))
            }
            return res
          })
          .catch(() => caches.match(request))
      )
      return
    } else {
      event.respondWith(
        (async () => {
          const offlineManaged = request.headers.get('X-Offline-Managed') === '1'
          try {
            const res = await fetch(withVersionHeader(request.clone()))
            return res
          } catch (_) {
            if (offlineManaged) {
              throw _
            }
            if (isTelemetry) {
              return new Response(null, { status: 204 })
            }
            await queueRequest(withVersionHeader(request))
            return new Response(JSON.stringify({ queued: true }), {
              status: 202,
              headers: { 'Content-Type': 'application/json', 'X-Offline-Queued': '1' },
            })
          }
        })()
      )
      return
    }
  }
})

function withVersionHeader(request) {
  try {
    const url = request.url
    const init = {
      method: request.method,
      headers: new Headers(request.headers),
      body: request.method === 'GET' || request.method === 'HEAD' ? undefined : request.body,
      credentials: request.credentials,
      cache: request.cache,
      mode: request.mode,
      redirect: request.redirect,
      referrer: request.referrer,
      referrerPolicy: request.referrerPolicy,
      integrity: request.integrity,
    }
    init.headers.set('X-Client-Revision', BUILD_ID)
    init.headers.set('X-Client-Version', APP_VERSION)
    return new Request(url, init)
  } catch (_) {
    return request
  }
}

self.addEventListener('activate', async () => {
  try {
    const clientsList = await self.clients.matchAll({ type: 'window' })
    clientsList.forEach((c) => c.postMessage({ type: 'APP_VERSION', buildId: BUILD_ID, version: APP_VERSION }))
  } catch {}
})
