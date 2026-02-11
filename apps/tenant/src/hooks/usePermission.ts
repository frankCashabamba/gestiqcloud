import { usePermissions } from '../contexts/PermissionsContext'

/**
 * Hook para chequear permisos del usuario
 *
 * Uso:
 *   const can = usePermission('billing:create')
 *   const can = usePermission('billing', 'create')
 *   const can = usePermission('pos')  // por defecto 'read'
 */
export function usePermission() {
  const { hasPermission } = usePermissions()

  return (actionOrModule: string, action?: string): boolean => {
    return hasPermission(actionOrModule, action)
  }
}
