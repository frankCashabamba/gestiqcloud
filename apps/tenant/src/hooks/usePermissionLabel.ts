import { useTranslation } from 'react-i18next'

/**
 * Hook para obtener label legible de un permiso
 *
 * Uso:
 *   const label = usePermissionLabel('billing:create')  // "Crear facturas"
 *   const label = usePermissionLabel('usuarios', 'delete')  // "Eliminar usuarios"
 */
export function usePermissionLabel() {
  const { t } = useTranslation()

  return (actionOrModule: string, action?: string): string => {
    let key: string

    if (action !== undefined) {
      key = `${actionOrModule}:${action}`
    } else {
      key = actionOrModule
    }

    // Intenta traducción; fallback a la clave misma
    const translated = t(`permissions.${key}`, { defaultValue: '' })
    return translated || key
  }
}
