import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import { getOrder, addOrderItem, updateOrderItem, sendToKitchen, closeOrder, Order, OrderItem, MenuItem } from './services'
import MenuPicker from './MenuPicker'

export default function OrderView() {
  const { orderId } = useParams<{ orderId: string }>()
  const navigate = useNavigate()
  const { success, error: showError } = useToast()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [itemNotes, setItemNotes] = useState('')
  const [closePending, setClosePending] = useState(false)

  const load = async () => {
    if (!orderId) return
    try {
      const o = await getOrder(orderId)
      setOrder(o)
    } catch {
      showError('Error cargando comanda')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [orderId])

  const handleAddProduct = async (product: MenuItem) => {
    if (!orderId) return
    try {
      await addOrderItem(orderId, {
        product_id: product.id,
        product_name: product.name,
        qty: 1,
        unit_price: product.price,
        notes: itemNotes || undefined,
      })
      setItemNotes('')
      setSearch('')
      success(`${product.name} agregado`)
      load()
    } catch {
      showError('Error agregando producto')
    }
  }

  const handleSendKitchen = async () => {
    if (!orderId) return
    try {
      await sendToKitchen(orderId)
      success('Enviado a cocina')
      load()
    } catch {
      showError('Error enviando a cocina')
    }
  }

  const handleClose = async () => {
    if (!orderId) return
    try {
      await closeOrder(orderId)
      success('Comanda cerrada')
      navigate('/restaurant')
    } catch {
      showError('Error cerrando comanda')
    } finally {
      setClosePending(false)
    }
  }

  const handleItemStatus = async (itemId: string, status: string) => {
    if (!orderId) return
    try {
      await updateOrderItem(orderId, itemId, { status } as Partial<OrderItem>)
      load()
    } catch {
      showError('Error actualizando')
    }
  }

  const STATUS_ITEM_COLORS: Record<string, string> = {
    pending: 'bg-yellow-50',
    preparing: 'bg-orange-50',
    ready: 'bg-green-50',
    served: 'bg-gray-50',
    canceled: 'bg-red-50 line-through',
  }

  if (loading) return <div className="p-6">Cargando comanda...</div>
  if (!order) return <div className="p-6">Comanda no encontrada</div>

  const pendingItems = (order.items || []).filter(i => i.status === 'pending')

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <button onClick={() => navigate('/restaurant')} className="text-blue-600 hover:underline text-sm">← Volver a mesas</button>
          <h1 className="text-2xl font-bold">🧾 Comanda {order.order_number}</h1>
          <p className="text-sm text-gray-500">
            {order.guests} comensales {order.waiter_name && `· Mesero: ${order.waiter_name}`}
          </p>
        </div>
        <div className="flex gap-2">
          {pendingItems.length > 0 && (
            <button onClick={handleSendKitchen} className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600">
              🔥 Enviar a Cocina ({pendingItems.length})
            </button>
          )}
          {order.status !== 'paid' && (
            <button onClick={() => setClosePending(true)} className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
              💵 Cerrar Comanda
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Product search / add */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="font-semibold">Agregar productos</h3>
          <input
            type="text"
            placeholder="Buscar producto..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full border rounded px-3 py-2"
          />
          <input
            type="text"
            placeholder="Notas (sin cebolla, extra queso...)"
            value={itemNotes}
            onChange={e => setItemNotes(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          />
          <MenuPicker onPick={handleAddProduct} search={search} limit={12} />
        </div>

        {/* Order items */}
        <div className="lg:col-span-2">
          <h3 className="font-semibold mb-3">Items de la comanda</h3>
          <div className="space-y-2">
            {(order.items || []).map(item => (
              <div key={item.id} className={`p-3 rounded border flex justify-between items-center ${STATUS_ITEM_COLORS[item.status]}`}>
                <div className="flex-1">
                  <span className="font-medium">{item.qty}x {item.product_name}</span>
                  {item.notes && <span className="text-xs text-gray-500 ml-2">({item.notes})</span>}
                  <span className="ml-2 text-sm">${item.line_total}</span>
                </div>
                <div className="flex gap-1">
                  {item.status === 'pending' && (
                    <button onClick={() => handleItemStatus(item.id, 'canceled')} className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded">Cancelar</button>
                  )}
                  {item.status === 'preparing' && (
                    <button onClick={() => handleItemStatus(item.id, 'ready')} className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">Listo</button>
                  )}
                  {item.status === 'ready' && (
                    <button onClick={() => handleItemStatus(item.id, 'served')} className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">Servido</button>
                  )}
                  <span className="text-xs px-2 py-1 bg-gray-100 rounded capitalize">{item.status}</span>
                </div>
              </div>
            ))}
            {(order.items || []).length === 0 && (
              <p className="text-gray-400 text-center py-4">Sin items — busca un producto a la izquierda</p>
            )}
          </div>

          {/* Totals */}
          <div className="mt-4 border-t pt-4 text-right">
            <p className="text-lg">Subtotal: <span className="font-bold">${order.subtotal}</span></p>
            <p className="text-sm text-slate-600">Impuestos: <span className="font-mono">${(order as any).tax_total ?? 0}</span></p>
            <p className="text-2xl font-bold">Total: ${order.total}</p>
          </div>
        </div>
      </div>
      {closePending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">Cerrar comanda</h3>
            <p className="text-sm text-slate-600 mb-4">¿Cerrar la comanda {order.order_number}? Esta acción no se puede deshacer.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setClosePending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancelar</button>
              <button onClick={handleClose} className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm">Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
