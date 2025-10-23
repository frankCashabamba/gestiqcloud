// Simple de-duplication/throttling to avoid floods on rapid re-renders or SW bursts
const __telemetryLastSent: Map<string, number> = (globalThis as any).__telemetryLastSent || new Map()
;(globalThis as any).__telemetryLastSent = __telemetryLastSent

export function sendTelemetry(event: string, data?: any) {
  // Disable telemetry in dev or when flag is set
  try {
    const env: any = (import.meta as any)?.env || {}
    if (env?.DEV || env?.VITE_DISABLE_TELEMETRY === '1') return
  } catch {}
  try {
    const url = '/api/v1/telemetry/event'
    const now = Date.now()
    const key = `${event}|${safeStableStringify(data)}`
    const last = __telemetryLastSent.get(key) || 0
    // Cooldown: drop duplicates within 5 seconds for same event+payload
    if (now - last < 5000) return
    __telemetryLastSent.set(key, now)

    const body = JSON.stringify({ event, data, ts: Math.floor(now / 1000) })
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' })
      navigator.sendBeacon(url, blob)
      return
    }
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true })
  } catch {}
}

function safeStableStringify(obj: any): string {
  try {
    if (!obj || typeof obj !== 'object') return String(obj ?? '')
    const allKeys = new Set<string>()
    JSON.stringify(obj, (k, v) => { allKeys.add(k); return v })
    return JSON.stringify(obj, Array.from(allKeys).sort())
  } catch {
    try { return JSON.stringify(obj) } catch { return '' }
  }
}

export { track } from '@shared/telemetry'
