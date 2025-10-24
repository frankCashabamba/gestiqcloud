import { manifest as clientes } from './clientes/manifest'
import { manifest as compras } from './compras/manifest'
import { manifest as contabilidad } from './contabilidad/manifest'
import { manifest as facturacion } from './facturacion/manifest'
import { manifest as finanzas } from './finanzas/manifest'
import { manifest as gastos } from './gastos/manifest'
import { manifest as importador } from './importador/manifest'
import { manifest as inventario } from './inventario/manifest'
import { manifest as pos } from './pos/manifest'
import { manifest as proveedores } from './proveedores/manifest'
import { manifest as rrhh } from './rrhh/manifest'
import { manifest as settings } from './settings/manifest'
import { manifest as usuarios } from './usuarios/manifest'
import { manifest as ventas } from './ventas/manifest'

export const MODULES = [
  pos,           // 5 - POS (más importante)
  ventas,        // 10 - Ventas
  facturacion,   // 15 - Facturación
  inventario,    // 20 - Inventario
  contabilidad,  // 25 - Contabilidad
  compras,       // 30 - Compras
  clientes,      // 35 - Clientes
  proveedores,   // 40 - Proveedores
  finanzas,      // 45 - Finanzas
  gastos,        // 50 - Gastos
  importador,    // 55 - Importador
  rrhh,          // 60 - RRHH
  settings,      // 65 - Configuración
  usuarios       // 70 - Usuarios
]

export type ModuleManifest = typeof clientes

