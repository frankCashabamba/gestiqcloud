/**
 * Payment Modal - Modal de cobro
 */
import React, { useState } from 'react'

type PaymentModalProps = {
  total: number
  onClose: () => void
  onComplete: (payments: any[]) => void
}

export default function PaymentModal({ total, onClose, onComplete }: PaymentModalProps) {
  const [method, setMethod] = useState<'cash' | 'card' | 'store_credit'>('cash')
  const [amountReceived, setAmountReceived] = useState(total.toFixed(2))
  const [processing, setProcessing] = useState(false)

  const change = parseFloat(amountReceived) - total

  const handleConfirm = async () => {
    if (method === 'cash' && change < 0) {
      alert('El monto recibido es menor al total')
      return
    }
    
    setProcessing(true)
    
    const payments = [
      {
        method,
        amount: method === 'cash' ? parseFloat(amountReceived) : total,
        ref: null,
      },
    ]
    
    try {
      await onComplete(payments)
      onClose()
    } catch (err) {
      setProcessing(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(value)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-slate-900">Cobrar</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-slate-100"
            disabled={processing}
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Total */}
        <div className="mt-6 rounded-xl bg-blue-50 p-6 text-center">
          <p className="text-sm font-medium text-blue-700">Total a Cobrar</p>
          <p className="mt-2 text-4xl font-bold text-blue-900">
            {formatCurrency(total)}
          </p>
        </div>

        {/* Método de Pago */}
        <div className="mt-6 space-y-3">
          <label className="block text-sm font-semibold text-slate-700">
            Método de Pago
          </label>
          
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => setMethod('cash')}
              className={`rounded-lg border-2 p-3 text-sm font-medium transition ${
                method === 'cash'
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              💵 Efectivo
            </button>
            
            <button
              onClick={() => setMethod('card')}
              className={`rounded-lg border-2 p-3 text-sm font-medium transition ${
                method === 'card'
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              💳 Tarjeta
            </button>
            
            <button
              onClick={() => setMethod('store_credit')}
              className={`rounded-lg border-2 p-3 text-sm font-medium transition ${
                method === 'store_credit'
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              🎫 Vale
            </button>
          </div>
        </div>

        {/* Monto Recibido (solo efectivo) */}
        {method === 'cash' && (
          <div className="mt-4">
            <label className="block text-sm font-semibold text-slate-700">
              Monto Recibido (€)
            </label>
            <input
              type="number"
              step="0.01"
              value={amountReceived}
              onChange={(e) => setAmountReceived(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-4 py-2 text-lg"
              autoFocus
            />
            
            {change >= 0 && (
              <div className="mt-3 rounded-lg bg-green-50 p-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-green-700">Cambio:</span>
                  <span className="text-xl font-bold text-green-900">
                    {formatCurrency(change)}
                  </span>
                </div>
              </div>
            )}
            
            {change < 0 && (
              <p className="mt-2 text-sm text-red-600">
                Falta {formatCurrency(Math.abs(change))}
              </p>
            )}
          </div>
        )}

        {/* Botones Rápidos (solo efectivo) */}
        {method === 'cash' && (
          <div className="mt-4 grid grid-cols-4 gap-2">
            {[5, 10, 20, 50].map((amount) => (
              <button
                key={amount}
                onClick={() => setAmountReceived((total + amount).toFixed(2))}
                className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium hover:bg-slate-100"
              >
                +{amount}€
              </button>
            ))}
          </div>
        )}

        {/* Confirmar */}
        <button
          onClick={handleConfirm}
          disabled={processing || (method === 'cash' && change < 0)}
          className="mt-6 w-full rounded-lg bg-green-600 px-6 py-4 text-lg font-bold text-white hover:bg-green-500 disabled:bg-slate-300"
        >
          {processing ? 'Procesando...' : 'Confirmar Cobro'}
        </button>
      </div>
    </div>
  )
}
