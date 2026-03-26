import { registerSW } from 'virtual:pwa-register'

export function setupPWA(onEvent?: (ev: 'need-refresh' | 'offline-ready') => void) {
  const metaEnv = (import.meta as ImportMeta & { env?: { DEV?: boolean } }).env
  if (metaEnv?.DEV) {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        registrations.forEach((registration) => {
          try {
            const scope = new URL(registration.scope)
            if (scope.origin === window.location.origin) {
              void registration.unregister()
            }
          } catch {
            void registration.unregister()
          }
        })
      }).catch(() => {})
    }
    return async () => {}
  }

  const updateSW = registerSW({
    immediate: true,
    onNeedRefresh() {
      window.dispatchEvent(new Event('pwa:need-refresh'))
      onEvent?.('need-refresh')
    },
    onOfflineReady() {
      window.dispatchEvent(new Event('pwa:offline-ready'))
      onEvent?.('offline-ready')
    }
  })
  ;(window as any).__updateSW = updateSW
  return updateSW
}
