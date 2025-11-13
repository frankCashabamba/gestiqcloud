declare module 'virtual:pwa-register' {
  export function registerSW(options?: any): (reload?: boolean) => Promise<void>
}
