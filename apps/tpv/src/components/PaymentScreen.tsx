/**
 * Payment Screen - Pantalla de cobro (fullscreen)
 */
import { useState } from 'react'
import { processPayment } from '../services/api'

type PaymentScreenProps = {
  items: any[]
  total: number
  onCancel: () => void
  onComplete: () => void
}

export default function PaymentScreen({ items, total, onCancel, onComplete }: PaymentScreenProps) {
  const [method, setMethod] = useState<'cash' | 'card'>('cash')
  const [amountReceived, setAmountReceived] = useState(total.toFixed(2))
  const [processing, setProcessing] = useState(false)

  const change = parseFloat(amountReceived) - total

  const handlePay = async () => {
    if (method === 'cash' && change < 0) {
      alert('Monto insuficiente')
      return
    }

    setProcessing(true)

    try {
      await processPayment({
        items,
        total,
        method,
        amount_received: method === 'cash' ? parseFloat(amountReceived) : total,
      })

      onComplete()
    } catch (err: any) {
      alert(err.message || 'Error al procesar pago')
    } finally {
      setProcessing(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(value)
  }

  const quickAmounts = [5, 10, 20, 50, 100]

  return (
    <div className="flex h-screen flex-col bg-slate-100">
      {/* Header */}
      <header className="bg-white px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">💳 Cobrar</h1>
          <button
            onClick={onCancel}
            disabled={processing}
            className="rounded-xl border-2 border-slate-300 px-6 py-2 font-medium hover:bg-slate-50"
          >
            Cancelar
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-2xl space-y-8">
          {/* Total Grande */}
          <div className="rounded-3xl bg-white p-12 text-center shadow-lg">
            <p className="text-xl text-slate-600">Total a Cobrar</p>
            <p className="mt-4 text-7xl font-bold text-blue-600">{formatCurrency(total)}</p>
          </div>

          {/* Método de Pago */}
          <div>
            <p className="mb-4 text-center text-lg font-semibold text-slate-700">Método de Pago</p>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setMethod('cash')}
                className={`btn-touch rounded-2xl border-4 py-8 text-2xl font-bold transition ${
                  method === 'cash'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-slate-300 bg-white text-slate-700'
                }`}
              >
                💵 Efectivo
              </button>
              
              <button
                onClick={() => setMethod('card')}
                className={`btn-touch rounded-2xl border-4 py-8 text-2xl font-bold transition ${
                  method === 'card'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-slate-300 bg-white text-slate-700'
                }`}
              >
                💳 Tarjeta
              </button>
            </div>
          </div>

          {/* Monto Recibido (solo efectivo) */}
          {method === 'cash' && (
            <div className="rounded-2xl bg-white p-6 shadow-lg">
              <label className="block text-center text-lg font-semibold text-slate-700">
                Monto Recibido (€)
              </label>
              <input
                type="number"
                step="0.01"
                value={amountReceived}
                onChange={(e) => setAmountReceived(e.target.value)}
                className="mt-4 block w-full rounded-xl border-2 border-slate-300 px-6 py-4 text-center text-4xl font-bold focus:border-blue-500 focus:outline-none"
                autoFocus
              />

              {/* Quick Amounts */}
              <div className="mt-4 grid grid-cols-5 gap-2">
                {quickAmounts.map((amount) => (
                  <button
                    key={amount}
                    onClick={() => setAmountReceived((total + amount).toFixed(2))}
                    className="btn-touch rounded-lg bg-slate-100 py-3 text-lg font-bold hover:bg-slate-200"
                  >
                    +{amount}€
                  </button>
                ))}
              </div>

              {/* Cambio */}
              {change >= 0 && (
                <div className="mt-6 rounded-xl bg-green-50 p-6 text-center">
                  <p className="text-lg text-green-700">Cambio</p>
                  <p className="mt-2 text-5xl font-bold text-green-900">
                    {formatCurrency(change)}
                  </p>
                </div>
              )}

              {change < 0 && (
                <div className="mt-6 rounded-xl bg-red-50 p-4 text-center">
                  <p className="text-lg font-medium text-red-700">
                    Falta {formatCurrency(Math.abs(change))}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Confirmar */}
          <button
            onClick={handlePay}
            disabled={processing || (method === 'cash' && change < 0)}
            className="btn-touch w-full rounded-2xl bg-green-600 py-8 text-3xl font-bold text-white hover:bg-green-500 disabled:bg-slate-300"
          >
            {processing ? '⏳ Procesando...' : '✅ CONFIRMAR PAGO'}
          </button>
        </div>
      </div>
    </div>
  )
}
