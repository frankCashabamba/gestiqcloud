export type Producto = {
  id: number | string
  sku: string
  nombre: string
  stock: number
  precio: number
}

export type Bodega = {
  id: number | string
  nombre: string
  ubicacion?: string
}

export type KardexEntry = {
  id: number | string
  fecha: string
  movimiento: 'IN' | 'OUT'
  cantidad: number
  saldo: number
  referencia?: string
}

