import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getReceipt, payReceipt, redeemStoreCredit, createPaymentLink, type CheckoutResponse } from '../services'
import { createMovimientoCaja } from '../../finances/services'
import { listStockItems, listWarehouses, type StockItem, type Warehouse } from '../../inventory/services'
import StoreCreditsModal from './StoreCreditsModal'
import type { POSLineStockSelection, POSPayment, POSReceiptLine, StoreCredit } from '../../../types/pos'
import { useCurrency } from '../../../hooks/useCurrency'
import { useToast } from '../../../shared/toast'

type LotOption = {
  key: string
  lot?: string | null
  expires_at?: string | null
  qty: number
}

const buildLotOptionKey = (lot?: string | null, expiresAt?: string | null) =>
  JSON.stringify([lot || null, expiresAt || null])

const readLotOptionKey = (key: string): { lot?: string; expires_at?: string } => {
  try {
    const [lot, expiresAt] = JSON.parse(key) as [string | null, string | null]
    return {
      lot: lot || undefined,
      expires_at: expiresAt || undefined,
    }
  } catch {
    return {}
  }
}

const formatLotOptionLabel = (option: LotOption, noLotLabel: string, noExpiryLabel: string): string => {
  const lotLabel = option.lot?.trim() || noLotLabel
  const expiryLabel = option.expires_at ? new Date(option.expires_at).toLocaleDateString() : noExpiryLabel
  return `${lotLabel} · ${option.qty} · ${expiryLabel}`
}

interface PaymentModalProps {
  receiptId: string
  totalAmount: number
  onSuccess: (payments: POSPayment[], checkoutResponse?: CheckoutResponse) => void
  onCancel: () => void
  warehouseId?: string
  isWholesaleCustomer?: boolean
}

export default function PaymentModal({
  receiptId,
  totalAmount,
  onSuccess,
  onCancel,
  warehouseId,
  isWholesaleCustomer = false,
}: PaymentModalProps) {
  const { t } = useTranslation(['pos', 'common'])
  const { symbol: currencySymbol, currency } = useCurrency()
  const toast = useToast()

  const [paymentMethod, setPaymentMethod] = useState<'cash' | 'card' | 'transfer' | 'store_credit' | 'link' | 'credit'>('cash')
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
  const [receiptLines, setReceiptLines] = useState<POSReceiptLine[]>([])
  const [stockOptionsByLine, setStockOptionsByLine] = useState<Record<string, LotOption[]>>({})
  const [allocationDrafts, setAllocationDrafts] = useState<Record<string, Record<string, string>>>({})
  const [stockLoading, setStockLoading] = useState(false)
  const payingRef = useRef(false)

  const activeWarehouseId = warehouseId || selectedWarehouse || undefined

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
    let cancelled = false
    ; (async () => {
      try {
        const receipt = await getReceipt(receiptId)
        if (!cancelled) {
          setReceiptLines(Array.isArray(receipt?.lines) ? receipt.lines : [])
        }
      } catch {
        if (!cancelled) {
          setReceiptLines([])
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [receiptId])

  useEffect(() => {
    if (!activeWarehouseId || receiptLines.length === 0) {
      setStockLoading(false)
      setStockOptionsByLine({})
      return
    }

    let cancelled = false
    setStockLoading(true)

    ; (async () => {
      try {
        const uniqueProductIds = Array.from(new Set(receiptLines.map((line) => String(line.product_id))))
        const stockByProduct = new Map<string, StockItem[]>()

        await Promise.all(
          uniqueProductIds.map(async (productId) => {
            const items = await listStockItems({ warehouse_id: activeWarehouseId, product_id: productId })
            stockByProduct.set(
              productId,
              (items || []).filter((item) => Number(item.qty || 0) > 0)
            )
          })
        )

        if (cancelled) return

        const nextOptions: Record<string, LotOption[]> = {}
        for (const line of receiptLines) {
          const lineId = String(line.id || '')
          if (!lineId) continue
          const grouped = new Map<string, LotOption>()
          for (const item of stockByProduct.get(String(line.product_id)) || []) {
            const key = buildLotOptionKey(item.lot || null, item.expires_at || null)
            const existing = grouped.get(key)
            if (existing) {
              existing.qty += Number(item.qty || 0)
            } else {
              grouped.set(key, { key, lot: item.lot || null, expires_at: item.expires_at || null, qty: Number(item.qty || 0) })
            }
          }
          nextOptions[lineId] = Array.from(grouped.values())
        }

        setStockOptionsByLine(nextOptions)
        setAllocationDrafts((prev) => {
          const next = { ...prev }
          for (const [lineId, selections] of Object.entries(next)) {
            const validKeys = new Set((nextOptions[lineId] || []).map((option) => option.key))
            const filtered = Object.fromEntries(
              Object.entries(selections).filter(([optionKey]) => validKeys.has(optionKey))
            )
            if (Object.keys(filtered).length === 0) {
              delete next[lineId]
            } else {
              next[lineId] = filtered
            }
          }
          return next
        })
      } catch {
        if (!cancelled) {
          setStockOptionsByLine({})
        }
      } finally {
        if (!cancelled) {
          setStockLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [activeWarehouseId, receiptLines])

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

  const lineSelectionRequirements = useMemo(
    () =>
      receiptLines
        .map((line) => {
          const lineId = String(line.id || '')
          const options = stockOptionsByLine[lineId] || []
          const draft = allocationDrafts[lineId] || {}
          const totalAssigned = options.reduce((sum, option) => sum + toNumber(draft[option.key] || 0), 0)
          return {
            line,
            lineId,
            options,
            requiresSelection: options.length > 1,
            totalAssigned,
          }
        })
        .filter((entry) => entry.lineId && entry.requiresSelection),
    [allocationDrafts, receiptLines, stockOptionsByLine]
  )

  const handlePay = async () => {
    if (loading || payingRef.current) return
    payingRef.current = true
    if (hasWarehouseSelectionIssue()) {
      toast.warning(t('pos:payment.selectWarehouseWarning'))
      return
    }
    if (activeWarehouseId && stockLoading) {
      toast.warning(
        t('pos:payment.loadingLotOptions', {
          defaultValue: 'Cargando lotes disponibles. Espera un momento.',
        })
      )
      return
    }

    setLoading(true)
    try {
      const payments: POSPayment[] = []
      const stockSelections: POSLineStockSelection[] = []

      for (const requirement of lineSelectionRequirements) {
        const draft = allocationDrafts[requirement.lineId] || {}
        const allocations = requirement.options
          .map((option) => {
            const qty = toNumber(draft[option.key] || 0)
            if (qty <= 0) return null
            const parsedSelection = readLotOptionKey(option.key)
            return {
              lot: parsedSelection.lot,
              expires_at: parsedSelection.expires_at,
              qty,
            }
          })
          .filter(Boolean) as Array<{ lot?: string; expires_at?: string; qty: number }>

        if (allocations.length === 0) {
          toast.warning(
            t('pos:payment.selectLotRequired', {
              defaultValue: 'Selecciona un lote para cada linea requerida antes de cobrar.',
            })
          )
          setLoading(false)
          return
        }
        const assignedQty = allocations.reduce((sum, allocation) => sum + Number(allocation.qty || 0), 0)
        const lineQty = Number(requirement.line.qty || 0)
        if (Math.abs(assignedQty - lineQty) > 0.000001) {
          toast.error(
            t('pos:payment.invalidLotAllocationTotal', {
              defaultValue: 'La suma asignada por lotes debe coincidir exactamente con la cantidad de la linea.',
            })
          )
          setLoading(false)
          return
        }
        const hasInsufficientAllocation = allocations.some((allocation) => {
          const match = requirement.options.find((option) => {
            const parsed = readLotOptionKey(option.key)
            return parsed.lot === allocation.lot && parsed.expires_at === allocation.expires_at
          })
          return !match || match.qty + 0.000001 < Number(allocation.qty || 0)
        })
        if (hasInsufficientAllocation) {
          toast.error(
            t('pos:payment.selectedLotInsufficient', {
              defaultValue: 'El lote seleccionado no tiene stock suficiente para esa linea.',
            })
          )
          setLoading(false)
          return
        }
        stockSelections.push({
          line_id: requirement.lineId,
          allocations,
        })
      }

      if (splitEnabled) {
        const cash = Math.max(0, toNumber(splitCashAmount))
        const card = Math.max(0, toNumber(splitCardAmount))
        const paid = cash + card
        if (paid < totalAmount) {
          toast.error(t('pos:payment.splitNotEnough'))
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
          toast.error(t('pos:payment.enterAmount'))
          setLoading(false)
          return
        }
        if (paid < totalAmount) {
          toast.error(t('pos:payment.amountLessThanTotal'))
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
          toast.warning(t('pos:payment.selectCreditOrCode'))
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
      } else if (paymentMethod === 'credit') {
        // Venta a crédito: registrar como OTHER con ref 'credit_sale'
        payments.push({ receipt_id: receiptId, method: 'other', amount: totalAmount, ref: 'credit_sale' })
      } else if (paymentMethod === 'link') {
        const result = await createPaymentLink({
          amount: totalAmount,
          currency,
          description: `Ticket POS #${receiptId.slice(0, 8)}`,
          metadata: { receipt_id: receiptId, payment_method: 'online_link' },
        })
        setPaymentLink(result.url)
        setShowQR(true)
        toast.success(t('pos:payment.linkGenerated'))
        setLoading(false)
        return
      }

      const wh = warehouseId || selectedWarehouse || undefined
      const response = await payReceipt(
        receiptId,
        payments,
        wh ? { warehouse_id: wh, stock_selections: stockSelections } : undefined
      )

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
      const detail = error?.response?.data?.detail
      if (detail === 'lot_selection_required') {
        toast.error(
          t('pos:payment.selectLotRequired', {
            defaultValue: 'Selecciona un lote para cada linea requerida antes de cobrar.',
          })
        )
      } else if (detail === 'invalid_lot_allocation_total') {
        toast.error(
          t('pos:payment.invalidLotAllocationTotal', {
            defaultValue: 'La suma asignada por lotes debe coincidir exactamente con la cantidad de la linea.',
          })
        )
      } else if (detail === 'selected_lot_insufficient') {
        toast.error(
          t('pos:payment.selectedLotInsufficient', {
            defaultValue: 'El lote seleccionado no tiene stock suficiente para esa linea.',
          })
        )
      } else if (detail === 'selected_lot_not_found') {
        toast.error(
          t('pos:payment.selectedLotNotFound', {
            defaultValue: 'El lote seleccionado ya no esta disponible. Recarga y vuelve a intentar.',
          })
        )
      } else {
        toast.error(detail || t('pos:payment.errorProcessing'))
      }
    } finally {
      setLoading(false)
      payingRef.current = false
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
        <h2 className="text-2xl font-bold mb-4" style={{ color: '#0f172a' }}>{t('pos:payment.charge')}</h2>

        <div className="mb-4 p-4 rounded" style={{ background: '#e2e8f0', border: '1px solid #cbd5e1' }}>
          <p className="text-sm" style={{ color: '#334155' }}>{t('pos:payment.total')}</p>
          <p className="text-3xl font-bold" style={{ color: '#0f172a' }}>
            {currencySymbol}
            {totalAmount.toFixed(2)}
          </p>
        </div>

        <div className={`mb-4 grid gap-2 ${isWholesaleCustomer ? 'grid-cols-3' : 'grid-cols-3'}`}>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('cash') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>{t('pos:payment.cash')}</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('card') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'card' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>{t('pos:payment.cardMethod')}</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('transfer') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'transfer' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>{t('pos:payment.transfer')}</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('store_credit') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'store_credit' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>{t('pos:payment.creditVoucher')}</button>
          <button onClick={() => { setSplitEnabled(false); setPaymentMethod('link') }} className={`p-3 border-2 rounded font-semibold ${!splitEnabled && paymentMethod === 'link' ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>{t('pos:payment.link')}</button>
          <button onClick={() => setSplitEnabled((v) => !v)} className={`p-3 border-2 rounded font-semibold ${splitEnabled ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'}`}>{t('pos:payment.split')}</button>
          {isWholesaleCustomer && (
            <button
              onClick={() => { setSplitEnabled(false); setPaymentMethod('credit') }}
              className={`p-3 border-2 rounded font-semibold col-span-3 ${!splitEnabled && paymentMethod === 'credit' ? 'border-amber-500 bg-amber-50 text-amber-800' : 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'}`}
            >
              💳 {t('pos:payment.creditSale', { defaultValue: 'Crédito / Cuenta corriente' })}
            </button>
          )}
        </div>
        {paymentMethod === 'credit' && !splitEnabled && (
          <div className="mb-4 p-3 rounded border border-amber-300 bg-amber-50 text-amber-800 text-sm">
            <strong>{t('pos:payment.creditSaleWarning', { defaultValue: 'Venta a crédito' })}</strong>
            {' — '}{t('pos:payment.creditSaleInfo', { defaultValue: 'El pago quedará pendiente de cobro. Se generará la factura y se registrará en cuentas por cobrar.' })}
          </div>
        )}

        {splitEnabled && (
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div>
            <label className="block text-sm font-medium mb-1" style={{ color: '#1e293b' }}>{t('pos:payment.cash')}</label>
            <input type="text" inputMode="decimal" value={splitCashAmount} onChange={(e) => setSplitCashAmount(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: '#1e293b' }}>{t('pos:payment.cardMethod')}</label>
            <input type="text" inputMode="decimal" value={splitCardAmount} onChange={(e) => setSplitCardAmount(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
        </div>
      )}

        {!splitEnabled && paymentMethod === 'cash' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2" style={{ color: '#1e293b' }}>{t('pos:payment.received')} ({currencySymbol})</label>
            <input type="text" inputMode="decimal" value={cashAmount} onChange={(e) => setCashAmount(e.target.value)} className="w-full px-3 py-2 border rounded text-xl text-center font-bold text-slate-900" autoFocus />
          </div>
        )}

        {!splitEnabled && paymentMethod === 'transfer' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">{t('pos:payment.refOptional')}</label>
            <input type="text" value={transferRef} onChange={(e) => setTransferRef(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
        )}

        {!splitEnabled && paymentMethod === 'store_credit' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">{t('pos:payment.storeCredit')}</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={storeCreditCode}
                onChange={(e) => setStoreCreditCode(e.target.value.toUpperCase())}
                className="flex-1 px-3 py-2 border rounded uppercase"
                placeholder="XXXX-XXXX-XXXX"
              />
              <button onClick={() => setShowStoreCreditsModal(true)} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">{t('pos:payment.search')}</button>
            </div>
          </div>
        )}

        {!warehouseId && warehouses.length > 1 && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">{t('pos:payment.warehouse')}</label>
            <select value={selectedWarehouse || ''} onChange={(e) => setSelectedWarehouse(e.target.value || null)} className="w-full px-3 py-2 border rounded">
              <option value="">{t('pos:payment.selectWarehouse')}</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>{w.code} - {w.name}</option>
              ))}
            </select>
          </div>
        )}

        {!!activeWarehouseId && lineSelectionRequirements.length > 0 && (
          <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-4">
            <div className="mb-2 text-sm font-semibold text-amber-900">
              {t('pos:payment.lotSelectionTitle', {
                defaultValue: 'Seleccion de lote requerida',
              })}
            </div>
            <p className="mb-3 text-xs text-amber-800">
              {t('pos:payment.lotSelectionHelp', {
                defaultValue: 'Estas lineas tienen varios lotes disponibles en el almacen seleccionado. Elige el lote a consumir.',
              })}
            </p>
            <div className="space-y-3">
              {lineSelectionRequirements.map((requirement) => (
                <div key={requirement.lineId} className="rounded border border-amber-200 bg-white p-3">
                  <div className="mb-2 text-sm font-medium text-slate-900">
                    {requirement.line.product_name || requirement.line.product_code || requirement.line.product_id}
                    {' · '}
                    {Number(requirement.line.qty || 0)} {t('pos:waste.qty')}
                  </div>
                  <div className="space-y-2">
                    {requirement.options.map((option) => (
                      <div key={option.key} className="grid grid-cols-[1fr_120px] gap-3 items-center">
                        <div className="text-xs text-slate-700">{formatLotOptionLabel(option, t('pos:payment.noLot'), t('pos:payment.noExpiry'))}</div>
                        <input
                          type="text"
                          inputMode="decimal"
                          value={allocationDrafts[requirement.lineId]?.[option.key] || ''}
                          onChange={(e) =>
                            setAllocationDrafts((prev) => ({
                              ...prev,
                              [requirement.lineId]: {
                                ...(prev[requirement.lineId] || {}),
                                [option.key]: e.target.value,
                              },
                            }))
                          }
                          className="w-full rounded border px-3 py-2 text-right"
                          placeholder="0"
                          disabled={stockLoading}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 text-xs text-slate-600">
                    {t('pos:payment.assignedLotQty', {
                      defaultValue: 'Asignado',
                    })}{' '}
                    {requirement.totalAssigned.toFixed(2)} / {Number(requirement.line.qty || 0).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {change > 0 && (
          <p className="mb-3 font-bold text-lg" style={{ color: '#15803d' }}>
            {t('pos:payment.change')}: {currencySymbol}
            {change.toFixed(2)}
          </p>
        )}

        <div className="pos-modal-actions" style={{ justifyContent: 'stretch' }}>
          <button onClick={handlePay} disabled={loading} className="pos-modal-btn primary" style={{ flex: 1, minWidth: 220, height: 44 }}>
            {loading ? t('pos:payment.processing') : t('pos:payment.confirmAndPrint')}
          </button>
          <button onClick={onCancel} disabled={loading} className="pos-modal-btn" style={{ minWidth: 120, height: 44 }}>
            {t('pos:payment.cancel')}
          </button>
        </div>

        {showQR && paymentLink && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
            <p className="text-sm font-medium mb-2">{t('pos:payment.paymentLink')}</p>
            <div className="flex items-center gap-2">
              <input type="text" value={paymentLink} readOnly className="flex-1 px-3 py-2 bg-white border rounded text-sm" />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(paymentLink)
                  toast.success(t('pos:payment.linkCopied'))
                }}
                className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {t('pos:payment.copyLink')}
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
