/**
 * Module manifest registry.
 *
 * Eagerly loads every `./<module>/manifest.ts` so each manifest is imported
 * at app startup. Without this side-effect import, manifests are dead code
 * (they were only referenced from a few barrels and tests) and tree-shaken /
 * flagged as unused by knip — meaning their `permissions`, `menu` and `routes`
 * declarations were silently disabled.
 *
 * The shape of each manifest is heterogeneous across modules — some export
 * `manifest`, some `crmManifest`, `productsManifest`, `inventoryManifest`,
 * `accountingManifest`, and a few re-export `default`. We pick the first
 * export whose value looks like a manifest object (`{ id: string, ... }`).
 */

export type ModuleManifest = {
  id: string
  name?: string
  version?: string
  enabled?: boolean
  permissions?: readonly string[]
  routes?: readonly unknown[]
  menu?: unknown
  // Allow extra fields without typing them — manifests are intentionally loose.
  readonly [key: string]: unknown
}

type ManifestModule = Record<string, unknown>

const MANIFEST_MODULES = import.meta.glob<ManifestModule>('./*/manifest.ts', {
  eager: true,
})

function isManifest(value: unknown): value is ModuleManifest {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as { id?: unknown }).id === 'string'
  )
}

function pickManifest(mod: ManifestModule): ModuleManifest | null {
  // Prefer the canonical `manifest` named export, then `default`, then any
  // other named export whose value satisfies the manifest shape.
  const preferredKeys = ['manifest', 'default']
  for (const key of preferredKeys) {
    if (key in mod && isManifest(mod[key])) return mod[key] as ModuleManifest
  }
  for (const value of Object.values(mod)) {
    if (isManifest(value)) return value
  }
  return null
}

function buildRegistry(): ReadonlyMap<string, ModuleManifest> {
  const out = new Map<string, ModuleManifest>()
  for (const [path, mod] of Object.entries(MANIFEST_MODULES)) {
    const manifest = pickManifest(mod)
    if (!manifest) {
      // Shouldn't happen unless someone adds a malformed manifest. Surface it
      // loudly during dev rather than silently dropping the module.
      // eslint-disable-next-line no-console
      console.warn(`[modules/registry] No manifest object found in ${path}`)
      continue
    }
    out.set(manifest.id, manifest)
  }
  return out
}

export const moduleRegistry: ReadonlyMap<string, ModuleManifest> = buildRegistry()

/** Number of manifests successfully registered. Useful for diagnostics/tests. */
export const moduleCount: number = moduleRegistry.size

/** Raw glob result, exposed for tests / debugging. */
export const manifestPaths: readonly string[] = Object.keys(MANIFEST_MODULES)

if (import.meta.env?.DEV) {
  // eslint-disable-next-line no-console
  console.info(`[modules/registry] Registered ${moduleCount} module manifests`)
}
