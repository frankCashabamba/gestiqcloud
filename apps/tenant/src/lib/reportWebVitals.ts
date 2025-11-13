import { getCLS, getFID, getFCP, getLCP, getTTFB, Metric } from 'web-vitals'
import { sendTelemetry } from '@shared'

/**
 * Reporta Web Vitals a telemetría
 * - CLS: Cumulative Layout Shift
 * - FID: First Input Delay
 * - FCP: First Contentful Paint
 * - LCP: Largest Contentful Paint
 * - TTFB: Time to First Byte
 */
function sendToAnalytics({ name, value, id, rating }: Metric) {
  // Enviar a backend de telemetría
  sendTelemetry('web_vitals', {
    metric: name,
    value: Math.round(value),
    id,
    rating,
    timestamp: new Date().toISOString()
  })

  // Log en desarrollo
  if (import.meta.env.DEV) {
    console.log(`[Web Vitals] ${name}:`, {
      value: Math.round(value),
      rating,
      id
    })
  }
}

/**
 * Inicializa el monitoreo de Web Vitals
 * Debe llamarse una vez al inicio de la aplicación
 */
export function reportWebVitals() {
  getCLS(sendToAnalytics)
  getFID(sendToAnalytics)
  getFCP(sendToAnalytics)
  getLCP(sendToAnalytics)
  getTTFB(sendToAnalytics)
}
