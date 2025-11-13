const _lastTelemetry: Record<string, number> = {}
const TELEMETRY_THROTTLE_MS = 10000 // 10 seconds between same event

export function sendTelemetry(event: string, data?: any) {
  try {
    // Throttle duplicate events
    const now = Date.now()
    const last = _lastTelemetry[event] || 0
    if (now - last < TELEMETRY_THROTTLE_MS) return
    _lastTelemetry[event] = now

    const url = '/api/v1/telemetry/event'
    const body = JSON.stringify({ event, data, ts: Math.floor(now / 1000) })
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' })
      navigator.sendBeacon(url, blob)
      return
    }
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true }).catch(() => {})
  } catch {}
}

export { track } from '@shared/telemetry'
