import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './app/App'
import { AuthProvider } from './auth/AuthContext'
import { ToastProvider } from './shared/toast'
import './index.css'
import { registerSW } from 'virtual:pwa-register'
import { I18nProvider } from './i18n/I18nProvider'
import { sendTelemetry } from './lib/telemetry'
import { apiFetch } from './lib/http'
import { applyTheme } from '@shared/ui'

// Register PWA service worker with auto updates and update prompt
const updateSW = registerSW({
  immediate: true,
  onNeedRefresh() {
    window.dispatchEvent(new Event('pwa:need-refresh'))
    sendTelemetry('pwa_need_refresh')
  },
  onOfflineReady() {
    window.dispatchEvent(new Event('pwa:offline-ready'))
    sendTelemetry('pwa_offline_ready')
  }
})
;(window as any).__updateSW = updateSW

// Load tenant theme tokens (non-blocking)
;(async () => {
  try {
    const t = await apiFetch<any>('/v1/tenant/settings/theme')
    if (t) applyTheme(t)
  } catch {}
})()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <I18nProvider defaultLang="es">
          <ToastProvider>
            <App />
          </ToastProvider>
        </I18nProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
