// MÓDULOS GESTIQCLOUD - Sistema completo
import { manifest as pos } from './pos/manifest'
import { manifest as produccion } from './produccion/manifest'
import { inventoryManifest } from './inventory/manifest'
import { manifest as sales } from './sales/manifest'
import { manifest as purchases } from './purchases/manifest'
import { manifest as suppliers } from './suppliers/manifest'
import { manifest as expenses } from './expenses/manifest'
import { manifest as usuarios } from './usuarios/manifest'
import { productsManifest } from './products/manifest'
import { crmManifest } from './crm/manifest'
import { manifest as reportes } from './reportes/manifest'
import { manifest as copilot } from './copilot/manifest'
import { manifest as templates } from './templates/manifest'
import { manifest as webhooks } from './webhooks/manifest'
import { manifest as einvoicing } from './einvoicing/manifest'
import { manifest as reconciliation } from './reconciliation/manifest'

export const MODULES = [
  productosManifest,   // 0 - Productos
  inventarioManifest, // 1 - Inventario
  pos,                 // 2 - Punto de Venta
  produccion,          // 3 - Recetas y Costos
  ventas,              // 4 - Ventas y Reportes
  compras,             // 5 - Compras de Insumos
  proveedores,         // 6 - Proveedores
  gastos,              // 7 - Gastos Diarios
  usuarios,            // 8 - Usuarios
  crmManifest,         // 9 - CRM
  reportes,            // 10 - Reportes
  copilot,             // 11 - Copilot
  templates,           // 12 - Templates
  webhooks,            // 13 - Webhooks
  einvoicing,          // 14 - Facturación Electrónica (stub)
  reconciliation,      // 15 - Conciliación Bancaria (stub)
]

export type ModuleManifest = typeof pos
