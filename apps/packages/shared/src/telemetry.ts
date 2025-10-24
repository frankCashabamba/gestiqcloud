export function sendTelemetry(event: string, data?: any) {
  try {
    const url = '/api/v1/telemetry/event'
    const body = JSON.stringify({ event, data, ts: Math.floor(Date.now() / 1000) })
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' })
      navigator.sendBeacon(url, blob)
      return
    }
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true })
  } catch {}
}

export { track } from '@shared/telemetry'

