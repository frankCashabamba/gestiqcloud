/**
 * TicketCart - Carrito de compras POS
 */
import React from 'react'
import type { CartItem } from '../../../types/pos'

interface TicketCartProps {
  items: CartItem[]
  onUpdateQty: (index: number, qty: number) => void
  onRemoveItem: (index: number) => void
  onClear: () => void
}

export default function TicketCart({ items, onUpdateQty, onRemoveItem, onClear }: TicketCartProps) {
  const calculateTotals = () => {
    let subtotal = 0
    let taxTotal = 0

    items.forEach((item) => {
      const lineSubtotal = item.qty * item.unit_price
      const discount = lineSubtotal * (item.discount_pct / 100)
      const lineNet = lineSubtotal - discount
      const lineTax = lineNet * item.tax_rate

      subtotal += lineNet
      taxTotal += lineTax
    })

    return {
      subtotal: subtotal.toFixed(2),
      taxTotal: taxTotal.toFixed(2),
      total: (subtotal + taxTotal).toFixed(2)
    }
  }

  const totals = calculateTotals()

  return (
    <div className="bg-white rounded-lg shadow h-full flex flex-col">
      <div className="p-4 border-b flex justify-between items-center">
        <h2 className="text-lg font-bold">Ticket Actual</h2>
        {items.length > 0 && (
          <button
            onClick={onClear}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Limpiar
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <p className="text-gray-400 text-center py-8">Carrito vacío</p>
        ) : (
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="border rounded p-3 hover:bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1">
                    <p className="font-medium">{item.product_name || item.product_id}</p>
                    {item.product_code && (
                      <p className="text-xs text-gray-500">{item.product_code}</p>
                    )}
                  </div>
                  <button
                    onClick={() => onRemoveItem(index)}
                    className="text-red-500 hover:text-red-700 ml-2"
                  >
                    ✕
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0.001"
                    step="0.001"
                    value={item.qty}
                    onChange={(e) => onUpdateQty(index, parseFloat(e.target.value) || 0)}
                    className="w-20 px-2 py-1 border rounded text-sm"
                  />
                  <span className="text-sm">× €{item.unit_price.toFixed(2)}</span>
                  <span className="ml-auto font-semibold">
                    €{item.line_total.toFixed(2)}
                  </span>
                </div>

                {item.discount_pct > 0 && (
                  <p className="text-xs text-orange-600 mt-1">
                    Descuento: {item.discount_pct}%
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {items.length > 0 && (
        <div className="border-t p-4 bg-gray-50">
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Subtotal:</span>
              <span>€{totals.subtotal}</span>
            </div>
            <div className="flex justify-between">
              <span>IVA:</span>
              <span>€{totals.taxTotal}</span>
            </div>
            <div className="flex justify-between font-bold text-lg pt-2 border-t">
              <span>TOTAL:</span>
              <span>€{totals.total}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
