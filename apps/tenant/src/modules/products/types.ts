export interface Producto {
  id: string
  name: string
  price: number
  stock?: number
  updated_at?: string
  active?: boolean
  [key: string]: any
}
