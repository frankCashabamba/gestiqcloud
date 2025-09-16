import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './app/App'
import { AuthProvider } from './auth/AuthContext'
import { ToastProvider } from './shared/toast'
import './index.css'
import { registerSW } from 'virtual:pwa-register'
import { sendTelemetry } from './lib/telemetry'

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

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
