export type Producto = {
  id: number | string
  sku: string
  name: string
  stock: number
  price: number
  categoria?: string
}

export type Bodega = {
  id: number | string
  name: string
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
