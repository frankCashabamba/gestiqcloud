import { registerSW } from 'virtual:pwa-register'

export function setupPWA(onEvent?: (ev: 'need-refresh' | 'offline-ready') => void) {
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
