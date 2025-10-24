declare module 'virtual:pwa-register' {
  export function registerSW(options?: {
    immediate?: boolean
    onNeedRefresh?: () => void
    onOfflineReady?: () => void
  }): (reloadPage?: boolean) => void
}

declare const __APP_BUILD_ID__: string
declare const __APP_VERSION__: string
