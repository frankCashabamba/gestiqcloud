/**
 * Cart - Carrito lateral con totales y acciones
 */

import CartItem from './CartItem'

type CartItem = {
  product_id: string
  name: string
  price: number
  qty: number
  tax_rate: number
}

type CartProps = {
  items: CartItem[]
  total: number
  onUpdateQty: (productId: string, qty: number) => void
  onRemove: (productId: string) => void
  onClear: () => void
  onCheckout: () => void
}

export default function Cart({ items, total, onUpdateQty, onRemove, onClear, onCheckout }: CartProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(value)
  }

  const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0)
  const tax = items.reduce((sum, item) => sum + item.price * item.qty * item.tax_rate, 0)

  return (
    <aside className="flex w-96 flex-col border-l border-slate-200 bg-white">
      {/* Header */}
      <div className="border-b border-slate-200 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">🛒 Carrito</h2>
          <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-700">
            {items.length} items
          </span>
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-auto p-4">
        {items.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <svg className="mx-auto h-16 w-16 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
              <p className="mt-4 text-sm text-slate-500">Carrito vacío</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <CartItem
                key={item.product_id}
                item={item}
                onUpdateQty={(qty) => onUpdateQty(item.product_id, qty)}
                onRemove={() => onRemove(item.product_id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Totals */}
      <div className="border-t border-slate-200 p-6">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-600">Subtotal:</span>
            <span className="font-medium">{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-600">IVA:</span>
            <span className="font-medium">{formatCurrency(tax)}</span>
          </div>
          <div className="flex justify-between border-t border-slate-200 pt-2">
            <span className="text-lg font-bold text-slate-900">TOTAL:</span>
            <span className="text-2xl font-bold text-green-600">
              {formatCurrency(total)}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 space-y-3">
          <button
            onClick={onCheckout}
            disabled={items.length === 0}
            className="btn-touch w-full rounded-xl bg-blue-600 py-4 text-lg font-bold text-white hover:bg-blue-500 disabled:bg-slate-300"
          >
            💳 COBRAR
          </button>
          
          <button
            onClick={onClear}
            disabled={items.length === 0}
            className="w-full rounded-xl border-2 border-red-300 py-3 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            🗑️ Vaciar Carrito
          </button>
        </div>
      </div>
    </aside>
  )
}
