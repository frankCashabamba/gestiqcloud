import React, { useEffect, useMemo, useState } from 'react'
import {
  canSaveDocument,
  fetchSaveCapabilities,
  saveDocument,
  suggestSaveDestination,
  type DocumentPaymentStatus,
  type Documento,
  type SaveDocumentPayload,
  type SaveDocumentResult,
} from '../services'

type SaveDocumentModalProps = {
  doc: Documento | null
  open: boolean
  onClose: () => void
  onSaved?: (result: SaveDocumentResult) => void
}

const paymentMethods: Array<NonNullable<SaveDocumentPayload['payment_method']>> = [
  'bank',
  'cash',
  'card',
  'transfer',
  'direct_debit',
  'check',
  'other',
]

function formatMoney(value: number | null): string {
  return value == null || Number.isNaN(value) ? '' : value.toFixed(2)
}

function getDocumentData(doc: Documento | null): Record<string, unknown> {
  const source = doc?.datos_confirmados || doc?.datos_extraidos
  return source && typeof source === 'object' ? source as Record<string, unknown> : {}
}

function getDocumentValue(data: Record<string, unknown>, ...keys: string[]): unknown {
  const normalized: Record<string, unknown> = {}
  for (const [rawKey, value] of Object.entries(data || {})) {
    const key = String(rawKey || '').trim().toLowerCase()
    if (key && !(key in normalized)) normalized[key] = value
  }
  for (const rawKey of keys) {
    const key = String(rawKey || '').trim().toLowerCase()
    if (!key || !(key in normalized)) continue
    const value = normalized[key]
    if (typeof value === 'string' && !value.trim()) continue
    if (value != null) return value
  }
  return undefined
}

function parseMoney(value: unknown): number | null {
  if (value == null || typeof value === 'boolean') return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null

  let raw = String(value).trim()
  if (!raw) return null
  raw = raw.replace(/[^0-9,.-]/g, '')
  if (!raw || raw === '-' || raw === '.' || raw === ',') return null

  if (raw.includes(',') && raw.includes('.')) {
    raw = raw.lastIndexOf(',') > raw.lastIndexOf('.')
      ? raw.replace(/\./g, '').replace(',', '.')
      : raw.replace(/,/g, '')
  } else if (raw.includes(',') && !raw.includes('.')) {
    raw = raw.replace(',', '.')
  }

  const numeric = Number(raw)
  return Number.isFinite(numeric) ? numeric : null
}

function inferPaymentMethod(value: unknown): NonNullable<SaveDocumentPayload['payment_method']> {
  const raw = String(value || '').trim().toLowerCase()
  if (!raw) return 'bank'
  if (raw.includes('cash') || raw.includes('efectivo')) return 'cash'
  if (raw.includes('card') || raw.includes('tarjeta')) return 'card'
  if (raw.includes('transfer') || raw.includes('transferencia')) return 'transfer'
  if (raw.includes('direct debit') || raw.includes('debito directo') || raw.includes('direct_debit')) return 'direct_debit'
  if (raw.includes('check') || raw.includes('cheque')) return 'check'
  if (raw.includes('bank') || raw.includes('banco')) return 'bank'
  return 'other'
}

export default function SaveDocumentModal({ doc, open, onClose, onSaved }: SaveDocumentModalProps) {
  const [destination, setDestination] = useState<'recipe' | 'expense' | 'supplier_invoice'>('expense')
  const [paymentStatus, setPaymentStatus] = useState<DocumentPaymentStatus>('pending')
  const [paymentMethod, setPaymentMethod] = useState<NonNullable<SaveDocumentPayload['payment_method']>>('bank')
  const [paidAmount, setPaidAmount] = useState('')
  const [pendingAmount, setPendingAmount] = useState('')
  const [paidAt, setPaidAt] = useState(() => new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({})
  const [updateStock, setUpdateStock] = useState(false)

  const lineItems = useMemo(() => {
    const data = getDocumentData(doc)
    const items = (data.line_items || data.lineas) as Array<Record<string, unknown>> | undefined
    return Array.isArray(items) ? items.filter(it => it && (it.quantity || it.cantidad)) : []
  }, [doc])

  const hasStockItems = lineItems.length > 0
  const canUpdateStock = hasStockItems && capabilities.inventory

  const totalAmount = useMemo(() => {
    if (!doc) return null
    if (doc.monto_total != null && !Number.isNaN(Number(doc.monto_total))) return Number(doc.monto_total)
    const data = getDocumentData(doc)
    return parseMoney(getDocumentValue(data, 'monto_total', 'total', 'amount', 'importe', 'grand_total', 'total_general'))
  }, [doc])

  const inferredDefaults = useMemo(() => {
    const data = getDocumentData(doc)
    const saveMeta = data._save && typeof data._save === 'object'
      ? data._save as Record<string, unknown>
      : {}
    const rawPayments = getDocumentValue(data, 'pagos', 'pago', 'payments', 'payment', 'payment_method', 'metodo_pago', 'metodo')
    const savedMethod = typeof saveMeta.payment_method === 'string' && paymentMethods.includes(saveMeta.payment_method as NonNullable<SaveDocumentPayload['payment_method']>)
      ? saveMeta.payment_method as NonNullable<SaveDocumentPayload['payment_method']>
      : null
    const savedStatus = typeof saveMeta.payment_status === 'string' && ['pending', 'partial', 'paid'].includes(saveMeta.payment_status)
      ? saveMeta.payment_status as DocumentPaymentStatus
      : null
    const savedPaid = parseMoney(saveMeta.paid_amount)
    const savedPending = parseMoney(saveMeta.pending_amount)
    const paidFromText = parseMoney(rawPayments)
    const paidAtValue = typeof saveMeta.paid_at === 'string' && saveMeta.paid_at.trim()
      ? saveMeta.paid_at.slice(0, 10)
      : new Date().toISOString().slice(0, 10)

    let paymentStatus: DocumentPaymentStatus = savedStatus || 'pending'
    let paid = savedPaid
    let pending = savedPending

    if (!savedStatus && paidFromText != null) {
      if (totalAmount != null) {
        if (paidFromText <= 0.005) paymentStatus = 'pending'
        else if (paidFromText + 0.01 >= totalAmount) paymentStatus = 'paid'
        else paymentStatus = 'partial'
      } else if (paidFromText > 0) {
        paymentStatus = 'paid'
      }
      paid = paid ?? paidFromText
    }

    if (paymentStatus === 'paid') {
      paid = paid ?? totalAmount
      pending = 0
    } else if (paymentStatus === 'pending') {
      paid = 0
      pending = pending ?? totalAmount
    } else if (paymentStatus === 'partial' && totalAmount != null) {
      if (paid == null && pending != null) paid = Math.max(totalAmount - pending, 0)
      if (pending == null && paid != null) pending = Math.max(totalAmount - paid, 0)
    }

    return {
      paymentStatus,
      paymentMethod: savedMethod || inferPaymentMethod(rawPayments),
      paidAmount: paymentStatus === 'partial' && paid == null ? '' : formatMoney(paid),
      pendingAmount: paymentStatus === 'paid' ? '0.00' : formatMoney(pending),
      paidAt: paidAtValue,
      notes: typeof saveMeta.notes === 'string' ? saveMeta.notes : '',
    }
  }, [doc, totalAmount])

  useEffect(() => {
    if (!open || !doc) return
    fetchSaveCapabilities().then(setCapabilities).catch(() => {})
    setUpdateStock(false)
    const suggested = suggestSaveDestination(doc)
    setDestination(suggested)
    setPaymentStatus(inferredDefaults.paymentStatus)
    setPaymentMethod(inferredDefaults.paymentMethod)
    setPaidAt(inferredDefaults.paidAt)
    setNotes(inferredDefaults.notes)
    setError('')

    if (suggested === 'recipe') {
      setPaidAmount('')
      setPendingAmount('')
      return
    }

    setPaidAmount(inferredDefaults.paidAmount)
    setPendingAmount(inferredDefaults.pendingAmount)
  }, [open, doc, totalAmount, inferredDefaults])

  if (!open || !doc) return null
  if (!canSaveDocument(doc)) return null

  const canSaveInvoice = capabilities.purchases || capabilities.invoicing
  const canSaveExpense = capabilities.expenses !== false

  const handlePaymentStatusChange = (nextStatus: DocumentPaymentStatus) => {
    setPaymentStatus(nextStatus)
    setError('')
    if (destination === 'recipe') return

    if (nextStatus === 'paid') {
      setPaidAmount(formatMoney(totalAmount))
      setPendingAmount('0.00')
      return
    }
    if (nextStatus === 'pending') {
      setPaidAmount('0.00')
      setPendingAmount(formatMoney(totalAmount))
      return
    }

    setPaidAmount('')
    setPendingAmount(formatMoney(totalAmount))
  }

  const handleDestinationChange = (nextDestination: 'recipe' | 'expense' | 'supplier_invoice') => {
    setDestination(nextDestination)
    setError('')
    if (nextDestination === 'recipe') {
      setPaidAmount('')
      setPendingAmount('')
      return
    }
    handlePaymentStatusChange(paymentStatus)
  }

  const handlePaidAmountChange = (value: string) => {
    setPaidAmount(value)
    if (totalAmount == null || value.trim() === '') return
    const numeric = Number(value)
    if (Number.isNaN(numeric)) return
    setPendingAmount(formatMoney(Math.max(totalAmount - numeric, 0)))
  }

  const handlePendingAmountChange = (value: string) => {
    setPendingAmount(value)
    if (totalAmount == null || value.trim() === '') return
    const numeric = Number(value)
    if (Number.isNaN(numeric)) return
    setPaidAmount(formatMoney(Math.max(totalAmount - numeric, 0)))
  }

  const submit = async () => {
    if (!doc?.id) return
    setSaving(true)
    setError('')

    try {
      const payload: SaveDocumentPayload = { destination, update_stock: updateStock && canUpdateStock }

      if (destination !== 'recipe') {
        payload.payment_status = paymentStatus
        payload.payment_method = paymentMethod
        payload.paid_at = paymentStatus === 'paid' ? paidAt : undefined
        payload.notes = notes.trim() || undefined

        if (paymentStatus === 'partial') {
          if (!paidAmount.trim() && !pendingAmount.trim()) {
            throw new Error('Debes indicar cuanto esta pagado o cuanto falta.')
          }
          payload.paid_amount = paidAmount.trim() ? Number(paidAmount) : undefined
          payload.pending_amount = pendingAmount.trim() ? Number(pendingAmount) : undefined
        } else if (paymentStatus === 'paid') {
          payload.paid_amount = paidAmount.trim() ? Number(paidAmount) : totalAmount ?? undefined
          payload.pending_amount = 0
        } else {
          payload.paid_amount = 0
          payload.pending_amount = pendingAmount.trim()
            ? Number(pendingAmount)
            : totalAmount ?? undefined
        }
      }

      const result = await saveDocument(doc.id, payload)
      onSaved?.(result)
      onClose()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'No se pudo guardar el documento.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={overlay}>
      <div style={modal}>
        <div style={header}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Guardar documento</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{doc.nombre_archivo}</div>
          </div>
          <button onClick={onClose} style={closeBtn} disabled={saving}>X</button>
        </div>

        <div style={body}>
          <div>
            <div style={label}>Guardar como</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
              {canSaveInvoice && (
                <button
                  type="button"
                  onClick={() => handleDestinationChange('supplier_invoice')}
                  style={{ ...choiceBtn, ...(destination === 'supplier_invoice' ? choiceBtnActive : null) }}
                  disabled={saving}
                >
                  Factura proveedor
                </button>
              )}
              {canSaveExpense && (
                <button
                  type="button"
                  onClick={() => handleDestinationChange('expense')}
                  style={{ ...choiceBtn, ...(destination === 'expense' ? choiceBtnActive : null) }}
                  disabled={saving}
                >
                  Gasto
                </button>
              )}
              <button
                type="button"
                onClick={() => handleDestinationChange('recipe')}
                style={{ ...choiceBtn, ...(destination === 'recipe' ? choiceBtnActive : null) }}
                disabled={saving}
              >
                Receta
              </button>
            </div>
            {destination === 'supplier_invoice' && (
              <div style={hintBox}>Se guardará en compras/cuentas por pagar como factura de proveedor.</div>
            )}
            {destination === 'expense' && (
              <div style={hintBox}>Se registrará como gasto en el módulo de gastos.</div>
            )}
          </div>

          {canUpdateStock && destination !== 'recipe' && (
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={updateStock}
                onChange={(e) => setUpdateStock(e.target.checked)}
                disabled={saving}
                style={{ width: 16, height: 16, marginTop: 2, cursor: 'pointer' }}
              />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
                  Actualizar stock ({lineItems.length} producto{lineItems.length > 1 ? 's' : ''})
                </div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                  {lineItems.map((it, i) => (
                    <span key={i}>
                      {i > 0 && ', '}
                      +{String(it.quantity ?? it.cantidad)} {String(it.description ?? it.descripcion ?? '').slice(0, 40)}
                    </span>
                  ))}
                </div>
              </div>
            </label>
          )}

          {destination !== 'recipe' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
                <label style={field}>
                  <span style={label}>Estado de pago</span>
                  <select
                    value={paymentStatus}
                    onChange={(e) => handlePaymentStatusChange(e.target.value as DocumentPaymentStatus)}
                    style={input}
                    disabled={saving}
                  >
                    <option value="pending">Pendiente</option>
                    <option value="partial">Parcial</option>
                    <option value="paid">Pagado</option>
                  </select>
                </label>

                <label style={field}>
                  <span style={label}>Metodo</span>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value as NonNullable<SaveDocumentPayload['payment_method']>)}
                    style={input}
                    disabled={saving}
                  >
                    {paymentMethods.map((method) => (
                      <option key={method} value={method}>{method}</option>
                    ))}
                  </select>
                </label>

                {paymentStatus === 'paid' && (
                  <label style={field}>
                    <span style={label}>Fecha de pago</span>
                    <input
                      type="date"
                      value={paidAt}
                      onChange={(e) => setPaidAt(e.target.value)}
                      style={input}
                      disabled={saving}
                    />
                  </label>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
                <label style={field}>
                  <span style={label}>Pagado</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={paidAmount}
                    onChange={(e) => handlePaidAmountChange(e.target.value)}
                    style={input}
                    disabled={saving || paymentStatus === 'pending'}
                    placeholder={formatMoney(totalAmount)}
                  />
                </label>

                <label style={field}>
                  <span style={label}>Falta por pagar</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={pendingAmount}
                    onChange={(e) => handlePendingAmountChange(e.target.value)}
                    style={input}
                    disabled={saving || paymentStatus === 'paid'}
                    placeholder={formatMoney(totalAmount)}
                  />
                </label>
              </div>

              <label style={field}>
                <span style={label}>Notas</span>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  style={{ ...input, minHeight: 88, resize: 'vertical' as const }}
                  disabled={saving}
                  placeholder="Ej: proveedor harina, vence el lunes, pago parcial..."
                />
              </label>
            </>
          )}

          {totalAmount != null && (
            <div style={summaryBox}>
              Total detectado: <strong>{doc.moneda || '$'} {totalAmount.toFixed(2)}</strong>
            </div>
          )}

          {error && <div style={errorBox}>{error}</div>}
        </div>

        <div style={footer}>
          <button onClick={onClose} style={secondaryBtn} disabled={saving}>Cancelar</button>
          <button onClick={submit} style={primaryBtn} disabled={saving}>
            {saving ? 'Guardando...' : destination === 'recipe' ? 'Guardar receta' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

const overlay: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(15, 23, 42, 0.48)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '1rem',
  zIndex: 50,
}

const modal: React.CSSProperties = {
  width: '100%',
  maxWidth: 720,
  background: '#fff',
  borderRadius: 14,
  boxShadow: '0 22px 48px rgba(15, 23, 42, 0.22)',
  overflow: 'hidden',
}

const header: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  padding: '1rem 1.1rem',
  borderBottom: '1px solid #e2e8f0',
}

const body: React.CSSProperties = {
  display: 'grid',
  gap: 16,
  padding: '1rem 1.1rem',
}

const footer: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  padding: '0.9rem 1.1rem 1rem',
  borderTop: '1px solid #e2e8f0',
}

const field: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const label: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  color: '#475569',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const input: React.CSSProperties = {
  border: '1px solid #cbd5e1',
  borderRadius: 10,
  padding: '0.7rem 0.8rem',
  fontSize: 14,
  color: '#0f172a',
  background: '#fff',
}

const choiceBtn: React.CSSProperties = {
  border: '1px solid #cbd5e1',
  borderRadius: 10,
  padding: '0.75rem 0.7rem',
  fontSize: 13,
  fontWeight: 600,
  background: '#fff',
  color: '#334155',
  cursor: 'pointer',
}

const choiceBtnActive: React.CSSProperties = {
  border: '1px solid #2563eb',
  background: '#eff6ff',
  color: '#1d4ed8',
}

const hintBox: React.CSSProperties = {
  marginTop: 8,
  padding: '0.65rem 0.8rem',
  borderRadius: 10,
  background: '#f8fafc',
  border: '1px solid #e2e8f0',
  fontSize: 12,
  color: '#475569',
}

const summaryBox: React.CSSProperties = {
  padding: '0.8rem 0.9rem',
  borderRadius: 10,
  background: '#eff6ff',
  border: '1px solid #bfdbfe',
  color: '#1e3a8a',
  fontSize: 13,
}

const errorBox: React.CSSProperties = {
  padding: '0.75rem 0.85rem',
  borderRadius: 10,
  background: '#fef2f2',
  border: '1px solid #fecaca',
  color: '#b91c1c',
  fontSize: 13,
}

const primaryBtn: React.CSSProperties = {
  border: 'none',
  borderRadius: 10,
  padding: '0.7rem 1rem',
  background: '#2563eb',
  color: '#fff',
  fontSize: 14,
  fontWeight: 700,
  cursor: 'pointer',
}

const secondaryBtn: React.CSSProperties = {
  border: '1px solid #cbd5e1',
  borderRadius: 10,
  padding: '0.7rem 1rem',
  background: '#fff',
  color: '#334155',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
}

const closeBtn: React.CSSProperties = {
  border: 'none',
  background: 'transparent',
  color: '#64748b',
  fontSize: 16,
  cursor: 'pointer',
}
