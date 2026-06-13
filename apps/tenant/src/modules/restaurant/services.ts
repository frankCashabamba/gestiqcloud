import api from '../../shared/api/client'
import { TENANT_RESTAURANT } from '@shared/endpoints'

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

const BASE = TENANT_RESTAURANT.base

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

// ---------- KDS ----------
export interface KDSItem {
  id: string
  product_name: string
  qty: number
  notes: string | null
  status: 'pending' | 'preparing' | 'ready' | 'served' | 'canceled'
  created_at: string | null
}

export interface KDSOrder {
  order_id: string
  order_number: string
  table_id: string
  table_number: number
  table_name: string | null
  opened_at: string | null
  created_at: string | null
  items: KDSItem[]
}

export const listKDSOrders = () =>
  api.get(`${BASE}/kds/orders`).then(r => r.data as KDSOrder[])
export const markItemReady = (itemId: string) =>
  api.post(`${BASE}/kds/items/${itemId}/ready`).then(r => r.data)
export const markItemServed = (itemId: string) =>
  api.post(`${BASE}/kds/items/${itemId}/served`).then(r => r.data)

// ---------- Menu ----------
export interface MenuItem {
  id: string
  name: string
  price: number
  tax_rate: number
  category: string | null
  sku: string | null
}

export const listMenu = () => api.get(`${BASE}/menu`).then(r => r.data as MenuItem[])
