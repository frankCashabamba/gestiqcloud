export function track(event: string, props?: Record<string, any>) {
  const app = (import.meta as any).env?.VITE_APP_NAME || 'web'
  const build = (globalThis as any).__APP_BUILD_ID__
  if ((import.meta as any).env?.DEV) {
    // eslint-disable-next-line no-console
    console.debug('[telemetry]', { app, event, props, build })
  }
}

