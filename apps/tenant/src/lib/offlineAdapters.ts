type OfflineSyncModule = Record<string, unknown>

function isRegisterFnName(name: string): boolean {
  return /^register.*SyncAdapter(s)?$/.test(name)
}

export function registerAllOfflineAdapters() {
  const modules = import.meta.glob('../modules/**/offlineSync.ts', { eager: true }) as Record<string, OfflineSyncModule>

  let registered = 0
  for (const mod of Object.values(modules)) {
    for (const [name, value] of Object.entries(mod)) {
      if (isRegisterFnName(name) && typeof value === 'function') {
        ;(value as () => void)()
        registered += 1
      }
    }
  }

  console.log(`[offline] Auto-registered ${registered} adapter registrars from offlineSync modules`)
}
