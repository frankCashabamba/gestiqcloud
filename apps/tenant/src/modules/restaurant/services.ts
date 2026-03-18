import api from '../../shared/api/client'

export interface Table {
  id: string
  number: number
  name: string | null
  capacity: number
  zone: string | null
  status: 'available' | 'occupied' | 'reserved' | 'cleaning'
  is_active: boolean
}

export interface OrderItem {
  id: string
  product_id: string
  product_name: string
  qty: number
  unit_price: number
  line_total: number
  notes: string | null
  status: 'pending' | 'preparing' | 'ready' | 'served' | 'canceled'
}

export interface Order {
  id: string
  table_id: string
  order_number: string
  waiter_name: string | null
  status: string
  guests: number
  notes: string | null
  subtotal: number
  total: number
  items: OrderItem[]
  opened_at: string
}

const BASE = '/api/v1/tenant/restaurant'

export const listTables = () => api.get(`${BASE}/tables`).then(r => r.data as Table[])
export const createTable = (data: Partial<Table>) => api.post(`${BASE}/tables`, data).then(r => r.data)
export const updateTable = (id: string, data: Partial<Table>) => api.put(`${BASE}/tables/${id}`, data).then(r => r.data)

export const listOrders = (params?: { status?: string; table_id?: string }) =>
  api.get(`${BASE}/orders`, { params }).then(r => r.data as Order[])
export const getOrder = (id: string) => api.get(`${BASE}/orders/${id}`).then(r => r.data as Order)
export const openOrder = (data: { table_id: string; guests?: number; waiter_name?: string }) =>
  api.post(`${BASE}/orders`, data).then(r => r.data)
export const addOrderItem = (orderId: string, data: { product_id: string; product_name: string; qty: number; unit_price: number; notes?: string }) =>
  api.post(`${BASE}/orders/${orderId}/items`, data).then(r => r.data)
export const updateOrderItem = (orderId: string, itemId: string, data: Partial<OrderItem>) =>
  api.put(`${BASE}/orders/${orderId}/items/${itemId}`, data).then(r => r.data)
export const sendToKitchen = (orderId: string) => api.post(`${BASE}/orders/${orderId}/send-kitchen`).then(r => r.data)
export const closeOrder = (orderId: string) => api.post(`${BASE}/orders/${orderId}/close`).then(r => r.data)
