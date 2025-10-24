/**
 * Cart Item - Item individual del carrito
 */
import React from 'react'

type CartItemProps = {
  item: {
    product_id: string
    name: string
    price: number
    qty: number
    tax_rate: number
  }
  onUpdateQty: (qty: number) => void
  onRemove: () => void
}

export default function CartItem({ item, onUpdateQty, onRemove }: CartItemProps) {
  const lineTotal = item.price * item.qty * (1 + item.tax_rate)

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(value)
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="font-semibold text-slate-900">{item.name}</h4>
          <p className="text-sm text-slate-500">{formatCurrency(item.price)} c/u</p>
        </div>
        
        <button
          onClick={onRemove}
          className="rounded-lg p-1 text-red-600 hover:bg-red-50"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="mt-3 flex items-center justify-between">
        {/* Qty Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onUpdateQty(item.qty - 1)}
            className="btn-touch flex h-10 w-10 items-center justify-center rounded-lg bg-slate-200 font-bold hover:bg-slate-300"
          >
            -
          </button>
          
          <input
            type="number"
            value={item.qty}
            onChange={(e) => onUpdateQty(parseFloat(e.target.value) || 0)}
            className="w-16 rounded-lg border border-slate-300 py-2 text-center font-bold"
          />
          
          <button
            onClick={() => onUpdateQty(item.qty + 1)}
            className="btn-touch flex h-10 w-10 items-center justify-center rounded-lg bg-slate-200 font-bold hover:bg-slate-300"
          >
            +
          </button>
        </div>

        {/* Line Total */}
        <p className="text-lg font-bold text-slate-900">
          {formatCurrency(lineTotal)}
        </p>
      </div>
    </div>
  )
}
