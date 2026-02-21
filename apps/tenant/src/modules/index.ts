// MÓDULOS GESTIQCLOUD - Sistema completo
import { manifest as pos } from './pos/manifest'
import { manifest as productions } from './productions/manifest'
import { inventarioManifest } from './inventory/manifest'
import { manifest as sales } from './sales/manifest'
import { manifest as purchases } from './purchases/manifest'
import { manifest as suppliers } from './suppliers/manifest'
import { manifest as expenses } from './expenses/manifest'
import { manifest as users } from './users/manifest'
import { productosManifest } from './products/manifest'
import { crmManifest } from './crm/manifest'
import { manifest as reports } from './reports/manifest'
import { manifest as templates } from './templates/manifest'
import { manifest as webhooks } from './webhooks/manifest'
import { manifest as einvoicing } from './einvoicing/manifest'
import { manifest as reconciliation } from './reconciliation/manifest'
import { manifest as notifications } from './notifications/manifest'

export const MODULES = [
  productosManifest,   // 0 - Productos
  inventarioManifest,  // 1 - Inventario
  pos,                 // 2 - Punto de Venta
  productions,         // 3 - Recetas y Costos
  sales,               // 4 - Ventas y Reportes
  purchases,           // 5 - Compras de Insumos
  suppliers,           // 6 - Proveedores
  expenses,            // 7 - Gastos Diarios
  users,               // 8 - Usuarios
  crmManifest,         // 9 - CRM
  reports,             // 10 - Reportes
  templates,           // 11 - Templates
  webhooks,            // 13 - Webhooks
  einvoicing,          // 14 - Facturación Electrónica (stub)
  reconciliation,      // 15 - Conciliación Bancaria (stub)
  notifications,       // 16 - Notificaciones
]

export type ModuleManifest = typeof pos
