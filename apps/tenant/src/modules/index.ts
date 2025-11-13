// MÓDULOS GESTIQCLOUD - Sistema completo
import { manifest as pos } from './pos/manifest'
import { manifest as produccion } from './produccion/manifest'
import { inventarioManifest } from './inventario/manifest'
import { manifest as ventas } from './ventas/manifest'
import { manifest as compras } from './compras/manifest'
import { manifest as proveedores } from './proveedores/manifest'
import { manifest as gastos } from './gastos/manifest'
import { manifest as usuarios } from './usuarios/manifest'
import { productosManifest } from './productos/manifest'
import { crmManifest } from './crm/manifest'

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
]

export type ModuleManifest = typeof pos
