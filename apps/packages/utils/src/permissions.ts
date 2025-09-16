export const defaultPermissionKeys = ['ver', 'crear', 'editar', 'eliminar', 'descargar', 'importar'] as const

export type PermisosObject = Record<string, boolean>

export function normalizePermisos(input: string[]): PermisosObject {
  return (defaultPermissionKeys as readonly string[]).reduce((acc, key) => {
    acc[key] = input.includes(key)
    return acc
  }, {} as PermisosObject)
}

export function permisosToArray(input: PermisosObject): string[] {
  return Object.entries(input)
    .filter(([_, isActive]) => isActive)
    .map(([key]) => key)
}

export function toPermisosObject(raw: unknown): PermisosObject {
  if (Array.isArray(raw)) return normalizePermisos(raw)
  if (typeof raw === 'object' && raw !== null) {
    return normalizePermisos(
      Object.entries(raw as Record<string, any>)
        .filter(([_, val]) => val === true)
        .map(([key]) => key)
    )
  }
  return normalizePermisos([])
}

