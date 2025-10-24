/**
 * Plantilla Panadería - Módulo SPEC-1
 * 
 * Sistema especializado para panaderías/queserías con:
 * - Inventario diario
 * - Registro de compras MP
 * - Control de leche
 * - Importación desde Excel
 * 
 * CONFIGURACIÓN: Este módulo solo se muestra si tenant tiene feature 'spec1'
 */

// Componentes principales
export { default as PanaderiaDashboard } from './components/Dashboard'
export { default as DailyInventoryList } from './components/DailyInventoryList'
export { default as PurchaseList } from './components/PurchaseList'
export { default as MilkRecordList } from './components/MilkRecordList'
export { default as ExcelImporter } from './components/ExcelImporter'

// Services
export * from './services'

/**
 * Configuración de módulos disponibles por plan
 */
export const PANADERIA_MODULES = {
  basic: ['dashboard', 'inventory'],
  standard: ['dashboard', 'inventory', 'purchases'],
  professional: ['dashboard', 'inventory', 'purchases', 'milk', 'excel_import'],
} as const

export type PanaderiaPlan = keyof typeof PANADERIA_MODULES
export type PanaderiaModule = (typeof PANADERIA_MODULES)[PanaderiaPlan][number]

/**
 * Hook para verificar si un módulo está disponible
 */
export function useModuleEnabled(module: PanaderiaModule): boolean {
  // TODO: Integrar con config real de tenant
  // const { plan } = useTenantConfig()
  const plan: PanaderiaPlan = 'professional' // Hardcoded por ahora
  
  return PANADERIA_MODULES[plan].includes(module as any)
}
