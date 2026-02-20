import React, { useEffect, useMemo, useState } from 'react'
import { payReceipt, redeemStoreCredit, createPaymentLink, type CheckoutResponse } from '../services'
import { createMovimientoCaja } from '../../finances/services'
import { listWarehouses, type Warehouse } from '../../inventory/services'
import StoreCreditsModal from './StoreCreditsModal'
import type { POSPayment, StoreCredit } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'
import { useToast } from '../../../shared/toast'

interface PaymentModalProps {
  receiptId: string
  totalAmount: number
  onSuccess: (payments: POSPayment[], checkoutResponse?: CheckoutResponse) => void
  onCancel: () => void
  warehouseId?: string
}

export default function PaymentModal({
  receiptId,
  totalAmount,
  onSuccess,
  onCancel,
  warehouseId,
}: PaymentModalProps) {
  const { symbol: currencySymbol, currency } = useCurrency()
  const toast = useToast()

  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'card' | 'transfer' | 'store_credit' | 'link'>('cash')
  const [cashAmount, setCashAmount] = useState(totalAmount.toFixed(2))
  const [splitEnabled, setSplitEnabled] = useState(false)
  const [splitCashAmount, setSplitCashAmount] = useState(totalAmount.toFixed(2))
  const [splitCardAmount, setSplitCardAmount] = useState('0')
  const [transferRef, setTransferRef] = useState('')
  const [storeCreditCode, setStoreCreditCode] = useState('')
  const [selectedStoreCredit, setSelectedStoreCredit] = useState<StoreCredit | null>(null)
  const [showStoreCreditsModal, setShowStoreCreditsModal] = useState(false)
  const [loading, setLoading] = useState(false)
  const [paymentLink, setPaymentLink] = useState<string | null>(null)
  const [showQR, setShowQR] = useState(false)

  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [selectedWarehouse, setSelectedWarehouse] = useState<string | null>(null)

  useEffect(() => {
    ; (async () => {
      try {
        const items = await listWarehouses()
        const actives = items.filter((w) => w.is_active)
        setWarehouses(actives)
        if (warehouseId) setSelectedWarehouse(warehouseId)
        else if (actives.length === 1) setSelectedWarehouse(String(actives[0].id))
      } catch {
        // silent fallback
      }
    })()
  }, [warehouseId])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onCancel()
      }
      if (e.key === 'Enter' && !loading && !showStoreCreditsModal) {
        e.preventDefault()
        void handlePay()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [loading, showStoreCreditsModal, onCancel, paymentMethod, cashAmount, splitEnabled, splitCashAmount, splitCardAmount, transferRef, storeCreditCode, selectedStoreCredit])

  const toNumber = (v: string | number): number => {
    if (typeof v === 'number') return v
    const normalized = String(v).trim().replace(/\s+/g, '').replace(',', '.')
    const n = parseFloat(normalized)
    return Number.isFinite(n) ? n : 0
  }

  const change = useMemo(() => {
    if (splitEnabled) {
      const paid = toNumber(splitCashAmount) + toNumber(splitCardAmount)
      return Math.max(0, paid - totalAmount)
    }
    if (paymentMethod === 'cash') {
      return Math.max(0, toNumber(cashAmount) - totalAmount)
    }
    return 0
  }, [splitEnabled, splitCashAmount, splitCardAmount, paymentMethod, cashAmount, totalAmount])

  const hasWarehouseSelectionIssue = () =>
    !warehouseId && warehouses.filter((w) => w.is_active).length > 1 && !selectedWarehouse

  const handlePay = async () => {
    if (loading) return
    if (hasWarehouseSelectionIssue()) {
      toast.warning('Selecciona un almacén para registrar el movimiento de stock.')
      return
    }

    setLoading(true)
    try {
      const payments: POSPayment[] = []

      if (splitEnabled) {
        const cash = Math.max(0, toNumber(splitCashAmount))
        const card = Math.max(0, toNumber(splitCardAmount))
        const paid = cash + card
        if (paid < totalAmount) {
          toast.error('El pago dividido no cubre el total.')
          setLoading(false)
          return
        }
        if (cash > 0) {
          payments.push({ receipt_id: receiptId, method: 'cash', amount: cash })
        }
        if (card > 0) {
          payments.push({ receipt_id: receiptId, method: 'card', amount: card })
        }
      } else if (paymentMethod === 'cash') {
        const paid = toNumber(cashAmount)
        if (paid <= 0) {
          toast.error('Ingresa el importe recibido.')
          setLoading(false)
          return
        }
        if (paid < totalAmount) {
          toast.error('El importe recibido es menor al total.')
          setLoading(false)
          return
        }
        payments.push({ receipt_id: receiptId, method: 'cash', amount: totalAmount })
      } else if (paymentMethod === 'card') {
        payments.push({ receipt_id: receiptId, method: 'card', amount: totalAmount })
      } else if (paymentMethod === 'transfer') {
        payments.push({
          receipt_id: receiptId,
          method: 'link',
          amount: totalAmount,
          ref: transferRef.trim() || undefined,
        })
      } else if (paymentMethod === 'store_credit') {
        if (!selectedStoreCredit && !storeCreditCode.trim()) {
          toast.warning('Selecciona un vale o ingresa un código.')
          setLoading(false)
          return
        }
        const code = selectedStoreCredit?.code || storeCreditCode
        await redeemStoreCredit(code, totalAmount)
        payments.push({
          receipt_id: receiptId,
          method: 'store_credit',
          amount: totalAmount,
          ref: code,
        })
      } else if (paymentMethod === 'link') {
        const result = await createPaymentLink({
          amount: totalAmount,
          currency,
          description: `Ticket POS #${receiptId.slice(0, 8)}`,
          metadata: { receipt_id: receiptId, payment_method: 'online_link' },
        })
        setPaymentLink(result.url)
        setShowQR(true)
        toast.success('Enlace de pago generado.')
        setLoading(false)
        return
      }

      const wh = warehouseId || selectedWarehouse || undefined
      const response = await payReceipt(receiptId, payments, wh ? { warehouse_id: wh } : undefined)

      try {
        const hasDocuments = !!(response?.documents_created?.sale || response?.documents_created?.invoice)
        if (!hasDocuments) {
          const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount || 0), 0)
          if (totalPaid > 0) {
            await createMovimientoCaja({
              fecha: new Date().toISOString(),
              concepto: `POS Receipt ${receiptId}`,
              tipo: 'ingreso',
              monto: totalPaid,
              referencia: receiptId,
            })
          }
        }
      } catch (syncErr) {
        console.warn('Could not sync cash movement fallback:', syncErr)
      }

      onSuccess(payments, response)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al procesar pago')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectStoreCredit = (credit: StoreCredit) => {
    setSelectedStoreCredit(credit)
    setStoreCreditCode(credit.code)
    setShowStoreCreditsModal(false)
  }

  return (
    <div className="pos-modal-overlay">
      <div
        className="pos-modal-card lg"
        style={{ background: '#f8fafc', border: '1px solid #cbd5e1', boxShadow: '0 24px 60px rgba(2, 6, 23, 0.28)' }}
      >
        <h2 className="text-2xl font-bold mb-4" style={{ color: '#0f172a' }}>Cobrar</h2>

        <div className="mb-4 p-4 rounded" style={{ background: '#e2e8f0', border: '1px solid #cbd5e1' }}>
          <p className="text-sm" style={{ color: '#334155' }}>Total</p>
          <p className="text-3xl font-bold" style={{ color: '#0f172a' }}>
            {currencySymbol}
            {totalAmount.toFixed(2)}
          </p>
        </div>

        <div className="mb-4 grid grid-cols-3 gap-2">
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('cash') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Efectivo</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('card') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'card' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Tarjeta</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('transfer') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'transfer' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Transferencia</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('store_credit') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'store_credit' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Vale</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('link') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'link' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Link</button>
          <button onClick={() => setSplitEnabled((v) => !v)} className={`p-3 border-2 rounded font-semibold ${splitEnabled ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>Dividido</button>
        </div>

        {splitEnabled && (
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div>
            <label className="block text-sm font-medium mb-1" style={{ color: '#1e293b' }}>Efectivo</label>
            <input type="text" inputMode="decimal" value={splitCashAmount} onChange={(e) => setSplitCashAmount(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: '#1e293b' }}>Tarjeta</label>
            <input type="text" inputMode="decimal" value={splitCardAmount} onChange={(e) => setSplitCardAmount(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
        </div>
      )}

        {!splitEnabled && paymentMethod === 'cash' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2" style={{ color: '#1e293b' }}>Recibido ({currencySymbol})</label>
            <input type="text" inputMode="decimal" value={cashAmount} onChange={(e) => setCashAmount(e.target.value)} className="w-full px-3 py-2 border rounded text-xl text-center font-bold text-slate-900" autoFocus />
          </div>
        )}

        {!splitEnabled && paymentMethod === 'transfer' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Referencia (opcional)</label>
            <input type="text" value={transferRef} onChange={(e) => setTransferRef(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
        )}

        {!splitEnabled && paymentMethod === 'store_credit' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Vale de descuento</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={storeCreditCode}
                onChange={(e) => setStoreCreditCode(e.target.value.toUpperCase())}
                className="flex-1 px-3 py-2 border rounded uppercase"
                placeholder="XXXX-XXXX-XXXX"
              />
              <button onClick={() => setShowStoreCreditsModal(true)} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Buscar</button>
            </div>
          </div>
        )}

        {!warehouseId && warehouses.length > 1 && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Almacén</label>
            <select value={selectedWarehouse || ''} onChange={(e) => setSelectedWarehouse(e.target.value || null)} className="w-full px-3 py-2 border rounded">
              <option value="">Selecciona un almacén…</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>{w.code} - {w.name}</option>
              ))}
            </select>
          </div>
        )}

        {change > 0 && (
          <p className="mb-3 font-bold text-lg" style={{ color: '#15803d' }}>
            Cambio: {currencySymbol}
            {change.toFixed(2)}
          </p>
        )}

        <div className="pos-modal-actions" style={{ justifyContent: 'stretch' }}>
          <button onClick={handlePay} disabled={loading} className="pos-modal-btn primary" style={{ flex: 1, minWidth: 220, height: 44 }}>
            {loading ? 'Procesando...' : 'Confirmar e imprimir'}
          </button>
          <button onClick={onCancel} disabled={loading} className="pos-modal-btn" style={{ minWidth: 120, height: 44 }}>
            Cancelar
          </button>
        </div>

        {showQR && paymentLink && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-sm font-medium mb-2">Enlace de pago</p>
            <div className="flex items-center gap-2">
              <input type="text" value={paymentLink} readOnly className="flex-1 px-3 py-2 bg-white border rounded text-sm" />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(paymentLink)
                  toast.success('Enlace copiado')
                }}
                className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Copiar
              </button>
            </div>
          </div>
        )}

        {showStoreCreditsModal && (
          <StoreCreditsModal onSelect={handleSelectStoreCredit} onClose={() => setShowStoreCreditsModal(false)} />
        )}
      </div>
    </div>
  )
}
