import type { Producto, Bodega, KardexEntry } from '../types/producto'

export const mockProductos: Producto[] = [
  { id: 1, sku: 'P-001', nombre: 'Producto A', stock: 25, precio: 12.5 },
  { id: 2, sku: 'P-002', nombre: 'Producto B', stock: 5, precio: 8.75 },
]

export const mockBodegas: Bodega[] = [
  { id: 1, nombre: 'Principal', ubicacion: 'Matriz' },
  { id: 2, nombre: 'Secundaria', ubicacion: 'Sucursal 1' },
]

export const mockKardex: KardexEntry[] = [
  { id: 1, fecha: '2025-01-01', movimiento: 'IN', cantidad: 10, saldo: 10, referencia: 'Compra #1001' },
  { id: 2, fecha: '2025-01-05', movimiento: 'OUT', cantidad: 2, saldo: 8, referencia: 'Venta #2001' },
]

