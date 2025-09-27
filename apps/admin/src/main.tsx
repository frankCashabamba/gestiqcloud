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

function IdleBridge() {
  const { logout } = useAuth()
  return <IdleLogout onLogout={logout} timeoutMs={30 * 60_000} />
}

// Register PWA service worker with auto updates and update prompt
setupPWA((ev: 'need-refresh' | 'offline-ready') => {
  if (ev === 'need-refresh') sendTelemetry('pwa_need_refresh')
  if (ev === 'offline-ready') sendTelemetry('pwa_offline_ready')
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <App />
          <IdleBridge />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
