/**
 * PaymentModal - Modal de pago (efectivo, tarjeta, vale)
 */
import React, { useState } from 'react'
import { payReceipt, redeemStoreCredit } from '../services'
import type { POSPayment } from '../../../types/pos'

interface PaymentModalProps {
  receiptId: string
  totalAmount: number
  onSuccess: () => void
  onCancel: () => void
}

export default function PaymentModal({ receiptId, totalAmount, onSuccess, onCancel }: PaymentModalProps) {
  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'card' | 'store_credit' | 'link'>('cash')
  const [cashAmount, setCashAmount] = useState(totalAmount.toFixed(2))
  const [storeCreditCode, setStoreCreditCode] = useState('')
  const [loading, setLoading] = useState(false)

  const calculateChange = () => {
    if (paymentMethod === 'cash') {
      const paid = parseFloat(cashAmount) || 0
      return Math.max(0, paid - totalAmount)
    }
    return 0
  }

  const handlePay = async () => {
    setLoading(true)
    try {
      const payments: POSPayment[] = []

      if (paymentMethod === 'cash') {
        const paid = parseFloat(cashAmount) || 0
        if (paid < totalAmount) {
          alert('El monto pagado es insuficiente')
          setLoading(false)
          return
        }
        payments.push({
          receipt_id: receiptId,
          method: 'cash',
          amount: totalAmount
        })
      } else if (paymentMethod === 'card') {
        payments.push({
          receipt_id: receiptId,
          method: 'card',
          amount: totalAmount
        })
      } else if (paymentMethod === 'store_credit') {
        if (!storeCreditCode.trim()) {
          alert('Ingrese el código del vale')
          setLoading(false)
          return
        }
        
        // Validar vale
        try {
          await redeemStoreCredit(storeCreditCode, totalAmount)
          payments.push({
            receipt_id: receiptId,
            method: 'store_credit',
            amount: totalAmount,
            ref: storeCreditCode
          })
        } catch (error: any) {
          alert(error.response?.data?.detail || 'Vale inválido o insuficiente')
          setLoading(false)
          return
        }
      } else if (paymentMethod === 'link') {
        alert('Pago online: Se generará enlace tras confirmar')
        // Implementar en siguiente iteración
        setLoading(false)
        return
      }

      await payReceipt(receiptId, payments)
      alert('Pago procesado exitosamente')
      onSuccess()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al procesar pago')
    } finally {
      setLoading(false)
    }
  }

  const change = calculateChange()

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full">
        <h2 className="text-2xl font-bold mb-4">Procesar Pago</h2>

        <div className="mb-6 p-4 bg-blue-50 rounded">
          <p className="text-sm text-gray-600">Total a pagar:</p>
          <p className="text-3xl font-bold">€{totalAmount.toFixed(2)}</p>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Método de Pago</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setPaymentMethod('cash')}
              className={`p-3 border-2 rounded ${
                paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
              }`}
            >
              💵 Efectivo
            </button>
            <button
              onClick={() => setPaymentMethod('card')}
              className={`p-3 border-2 rounded ${
                paymentMethod === 'card' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
              }`}
            >
              💳 Tarjeta
            </button>
            <button
              onClick={() => setPaymentMethod('store_credit')}
              className={`p-3 border-2 rounded ${
                paymentMethod === 'store_credit' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
              }`}
            >
              🎟️ Vale
            </button>
            <button
              onClick={() => setPaymentMethod('link')}
              className={`p-3 border-2 rounded ${
                paymentMethod === 'link' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
              }`}
            >
              🔗 Link Online
            </button>
          </div>
        </div>

        {paymentMethod === 'cash' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Monto Recibido (€)</label>
            <input
              type="number"
              step="0.01"
              value={cashAmount}
              onChange={(e) => setCashAmount(e.target.value)}
              className="w-full px-3 py-2 border rounded text-xl text-center font-bold"
              autoFocus
            />
            {change > 0 && (
              <p className="mt-2 text-green-600 font-bold text-lg">
                Cambio: €{change.toFixed(2)}
              </p>
            )}
          </div>
        )}

        {paymentMethod === 'store_credit' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Código del Vale</label>
            <input
              type="text"
              value={storeCreditCode}
              onChange={(e) => setStoreCreditCode(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border rounded uppercase"
              placeholder="XXXX-XXXX-XXXX"
              autoFocus
            />
          </div>
        )}

        <div className="flex gap-2 mt-6">
          <button
            onClick={handlePay}
            disabled={loading}
            className="flex-1 bg-green-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-green-700 disabled:opacity-50"
          >
            {loading ? 'Procesando...' : 'Confirmar Pago'}
          </button>
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-6 py-3 bg-gray-300 rounded-lg hover:bg-gray-400"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
