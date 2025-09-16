import type { Producto, Bodega, KardexEntry } from '../types/producto'
import { mockProductos, mockBodegas, mockKardex } from '../mock/mockInventario'

export async function fetchProductos(): Promise<Producto[]> {
  return new Promise((r) => setTimeout(() => r(mockProductos), 150))
}

export async function fetchBodegas(): Promise<Bodega[]> {
  return new Promise((r) => setTimeout(() => r(mockBodegas), 150))
}

export async function fetchKardex(_productoId?: string | number): Promise<KardexEntry[]> {
  return new Promise((r) => setTimeout(() => r(mockKardex), 150))
}

