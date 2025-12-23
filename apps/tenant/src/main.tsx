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
import { applyTheme, OutboxIndicator } from '@shared/ui'
import { IdleLogout } from '@ui'
import { useAuth } from './auth/AuthContext'
import { EnvProvider } from '@ui/env'
import { ConflictResolver } from '@shared/ui'
import { env } from './env'
import { TenantProvider } from './contexts/TenantContext'
import { fetchTenantTheme } from './services/theme'

function IdleBridge() {
  const { logout } = useAuth()
  return <IdleLogout onLogout={logout} timeoutMs={30 * 60_000} />
}

function ConflictBridge() {
  const handleResolve = (conflict: any, resolution: string) => {
    console.log('Resolving conflict:', conflict, resolution)
    // Send resolution to backend
    // Implementation depends on ElectricSQL conflict API
  }

  return <ConflictResolver onResolve={handleResolve} />
}

// Register PWA service worker with auto updates and update prompt
setupPWA((ev) => {
  if (ev === 'need-refresh') sendTelemetry('pwa_need_refresh')
  if (ev === 'offline-ready') sendTelemetry('pwa_offline_ready')
})

// Load tenant theme tokens (non-blocking)
;(async () => {
  try {
    const t = await fetchTenantTheme()
    if (t) applyTheme(t)
  } catch {}
})()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <EnvProvider value={env}>
      <BrowserRouter>
        <AuthProvider>
          <TenantProvider>
            <I18nProvider defaultLang="es">
            <ToastProvider>
              <App />
              <IdleBridge />
              <ConflictBridge />
              <OutboxIndicator />
            </ToastProvider>
            </I18nProvider>
          </TenantProvider>
        </AuthProvider>
      </BrowserRouter>
    </EnvProvider>
  </React.StrictMode>
)
