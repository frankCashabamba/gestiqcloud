import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './app/App'
import { AuthProvider } from './auth/AuthContext'
import { ToastProvider } from './shared/toast'
import './index.css'
import { I18nProvider } from './i18n/I18nProvider'
import { setupPWA } from '@pwa'
import { sendTelemetry } from '@shared'
import { apiFetch } from './lib/http'
import { applyTheme } from '@shared/ui'
import { IdleLogout } from '@ui'
import { useAuth } from './auth/AuthContext'

function IdleBridge() {
  const { logout } = useAuth()
  return <IdleLogout onLogout={logout} timeoutMs={30 * 60_000} />
}

// Register PWA service worker with auto updates and update prompt
setupPWA((ev) => {
  if (ev === 'need-refresh') sendTelemetry('pwa_need_refresh')
  if (ev === 'offline-ready') sendTelemetry('pwa_offline_ready')
})

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
            <IdleBridge />
          </ToastProvider>
        </I18nProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
