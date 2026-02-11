/**
 * Navigation Service - i18n Support
 * Provides translated messages and labels for dashboard navigation
 */

export const NAVIGATION_I18N = {
  en: {
    // Module error messages
    modules: {
      pos: 'POS',
      ventas: 'Sales',
      inventario: 'Inventory',
      clientes: 'Customers',
      reportes: 'Reports',
      facturas: 'Invoicing',
    },
    // Action labels (fallback if not using i18n for all strings)
    actions: {
      newSale: 'New sale',
      createPromotion: 'Create promotion',
      newCustomer: 'New customer',
      cashClose: 'Cash close',
      inventory: 'Inventory',
      replenishment: 'Replenishment',
      stockReplenishment: 'Stock replenishment',
      promotions: 'Promotions',
      salesAnalysis: 'Sales analysis',
    },
    // Messages
    messages: {
      moduleRequired: (module: string) => `${module} module required`,
      notAvailable: 'This action is not available',
      actionSuccess: (action: string) => `${action} completed successfully`,
      actionError: (action: string) => `Error performing ${action}. Please try again.`,
      storeClosed: 'The store is currently closed',
      noActiveRegister: 'No active register found. Please open a cash register first.',
    },
  },
  es: {
    // Module error messages
    modules: {
      pos: 'POS',
      ventas: 'Ventas',
      inventario: 'Inventario',
      clientes: 'Clientes',
      reportes: 'Reportes',
      facturas: 'Facturación',
    },
    // Action labels (fallback)
    actions: {
      newSale: 'Nueva venta',
      createPromotion: 'Crear promoción',
      newCustomer: 'Nuevo cliente',
      cashClose: 'Cerrar caja',
      inventory: 'Inventario',
      replenishment: 'Reposición',
      stockReplenishment: 'Reposición de stock',
      promotions: 'Promociones',
      salesAnalysis: 'Análisis de ventas',
    },
    // Messages
    messages: {
      moduleRequired: (module: string) => `Módulo ${module} requerido`,
      notAvailable: 'Esta acción no está disponible',
      actionSuccess: (action: string) => `${action} completado exitosamente`,
      actionError: (action: string) => `Error al realizar ${action}. Por favor intenta de nuevo.`,
      storeClosed: 'La tienda está actualmente cerrada',
      noActiveRegister: 'No se encontró un registro activo. Por favor abre una caja primero.',
    },
  },
}

/**
 * Get translated module name
 * @param module Module slug (pos, ventas, etc)
 * @param locale Language code (en, es)
 * @returns Translated module name
 */
export function getModuleName(module: string, locale: string = 'en'): string {
  const moduleMap = NAVIGATION_I18N[locale as keyof typeof NAVIGATION_I18N]?.modules
  return moduleMap?.[module as keyof typeof moduleMap] || module
}

/**
 * Get translated action label
 * @param actionKey Action key (newSale, createPromotion, etc)
 * @param locale Language code (en, es)
 * @returns Translated action label
 */
export function getActionLabel(actionKey: string, locale: string = 'en'): string {
  const actionMap = NAVIGATION_I18N[locale as keyof typeof NAVIGATION_I18N]?.actions
  return actionMap?.[actionKey as keyof typeof actionMap] || actionKey
}

/**
 * Get translated message
 * @param messageKey Message key
 * @param locale Language code (en, es)
 * @param args Optional arguments for template
 * @returns Translated message
 */
export function getMessage(
  messageKey: string,
  locale: string = 'en',
  args?: Record<string, any>
): string {
  const messageMap = NAVIGATION_I18N[locale as keyof typeof NAVIGATION_I18N]?.messages
  const messageFunc = messageMap?.[messageKey as keyof typeof messageMap]

  if (typeof messageFunc === 'function') {
    return messageFunc(args?.module || args?.action || '')
  }

  return messageKey
}

/**
 * Export all translations for use in components
 */
export function getNavigationI18n(locale: string = 'en') {
  return NAVIGATION_I18N[locale as keyof typeof NAVIGATION_I18N]
}
