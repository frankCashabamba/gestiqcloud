import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './app/App'
import { AuthProvider } from './auth/AuthContext'
import { ToastProvider } from './shared/toast'
import './index.css'
import { setupPWA } from '@pwa'
import { sendTelemetry } from '@shared'
import { IdleLogout } from '@ui'
import { useAuth } from './auth/AuthContext'
import { EnvProvider } from '@ui/env'
import { env } from './env'

function IdleBridge() {
  const { logout } = useAuth()
  return <IdleLogout onLogout={logout} timeoutMs={30 * 60_000} />
}

// Build stamp / runtime debug: ayuda a verificar que el bundle cargado es el más reciente
try {
  if (typeof window !== 'undefined') {
    // Activa trazas del cliente HTTP si quieres: window.__GC_DEBUG = true en consola
    // eslint-disable-next-line no-console
    console.info('[admin] build', {
      mode: import.meta.env.MODE,
      apiUrl: import.meta.env.VITE_API_URL,
      adminOrigin: import.meta.env.VITE_ADMIN_ORIGIN,
      tenantOrigin: import.meta.env.VITE_TENANT_ORIGIN,
      ts: new Date().toISOString(),
    })
  }
} catch {}

// Register PWA service worker with auto updates and update prompt
setupPWA((ev: 'need-refresh' | 'offline-ready') => {
  if (ev === 'need-refresh') sendTelemetry('pwa_need_refresh')
  if (ev === 'offline-ready') sendTelemetry('pwa_offline_ready')
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <EnvProvider value={env}>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <App />
            <IdleBridge />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </EnvProvider>
  </React.StrictMode>
)
