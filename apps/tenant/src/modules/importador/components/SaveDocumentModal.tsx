import React, { useEffect, useMemo, useState } from 'react'
import { listPaymentMethods, type PaymentMethod } from '../../accounting/services'
import {
  canSaveDocument,
  fetchDocumentLineMatchCandidates,
  fetchSaveCapabilities,
  getCandidateSaveDestinations,
  getDocumentData,
  getDocumentValue,
  saveDocument,
  suggestSaveDestination,
  type DocumentCandidateDestination,
  type DocumentLineMatch,
  type DocumentPaymentStatus,
  type DocumentSaveDestination,
  type Documento,
  type SaveDocumentPayload,
  type SaveDocumentResult,
} from '../services'
import { getImportadorSaveActionLabel } from '../constants'

type SaveDocumentModalProps = {
  doc: Documento | null
  open: boolean
  resumeMode?: boolean
  onClose: () => void
  onSaved?: (result: SaveDocumentResult) => void
}

function formatMoney(value: number | null): string {
  return value == null || Number.isNaN(value) ? '' : value.toFixed(2)
}

function formatCompactNumber(
  value: number | null | undefined,
  options?: { minDecimals?: number; maxDecimals?: number },
): string {
  if (value == null || Number.isNaN(Number(value))) return '0'
  const numeric = Number(value)
  const minDecimals = Math.max(0, Math.min(options?.minDecimals ?? 0, 6))
  const maxDecimals = Math.max(minDecimals, Math.min(options?.maxDecimals ?? 2, 6))
  return numeric.toLocaleString(undefined, {
    minimumFractionDigits: Number.isInteger(numeric) ? minDecimals : Math.max(minDecimals, 1),
    maximumFractionDigits: maxDecimals,
  })
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
    const parts = raw.split(',').map((part) => part.trim()).filter(Boolean)
    const allNumeric = parts.length > 1 && parts.every((part) => /^\d+$/.test(part))
    if (allNumeric && parts[parts.length - 1].length === 3) {
      raw = parts.join('')
    } else {
      raw = raw.replace(',', '.')
    }
  }

  const numeric = Number(raw)
  return Number.isFinite(numeric) ? numeric : null
}

function getLineItemText(
  item: Record<string, unknown>,
  ...keys: string[]
): string {
  for (const key of keys) {
    const value = item[key]
    if (value == null) continue
    const text = String(value).trim()
    if (text) return text
  }
  return ''
}

function getLineItemDescription(item: Record<string, unknown>): string {
  const description = getLineItemText(
    item,
    'description',
    'descripcion',
    'concept',
    'concepto',
    'product_name',
    'nombre_producto',
    'item',
    'name',
  )
  if (description) return description
  const reference = getLineItemText(item, 'supplier_ref', 'codigo', 'code', 'sku')
  return reference || 'Producto sin nombre'
}

function getLineItemUnit(item: Record<string, unknown>): string {
  return getLineItemText(item, 'unit', 'unidad', 'uom')
}

function normalizeText(value: unknown): string {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function extractPaymentMethodText(value: unknown): string {
  if (Array.isArray(value)) {
    return value
      .map((item) => extractPaymentMethodText(item))
      .filter(Boolean)
      .join(', ')
  }

  if (value && typeof value === 'object') {
    const row = value as Record<string, unknown>
    for (const key of ['name', 'label', 'value', 'description', 'method', 'type']) {
      const candidate = extractPaymentMethodText(row[key])
      if (candidate) return candidate
    }
    return ''
  }

  const raw = String(value || '').trim()
  if (!raw) return ''
  return raw.replace(
    /^(payment\s*(method|type|terms?)|metodo\s+de\s+pago|forma\s+de\s+pago|tipo\s+de\s+pago|medio\s+de\s+pago|condiciones?\s+de\s+pago)\s*[:-]\s*/i,
    '',
  ).trim()
}

function scorePaymentMethod(rawNorm: string, method: PaymentMethod): number {
  const nameNorm = normalizeText(method.name)
  const descriptionNorm = normalizeText(method.description || '')
  if (!rawNorm || !nameNorm) return 0
  if (rawNorm === nameNorm) return 1
  if (descriptionNorm && rawNorm === descriptionNorm) return 0.96
  if (rawNorm.includes(nameNorm) || nameNorm.includes(rawNorm)) return 0.9
  if (descriptionNorm && (rawNorm.includes(descriptionNorm) || descriptionNorm.includes(rawNorm))) {
    return 0.84
  }

  const rawTokens = new Set(rawNorm.split(' ').filter(Boolean))
  const candidateTokens = new Set(`${nameNorm} ${descriptionNorm}`.split(' ').filter(Boolean))
  const common = Array.from(rawTokens).filter((token) => candidateTokens.has(token)).length
  if (common > 0) {
    return Math.min(common / Math.max(rawTokens.size, 1), 0.8)
  }
  return 0
}

function pickPaymentMethodId(
  rawValue: unknown,
  methods: PaymentMethod[],
  fallbackId = '',
): string {
  if (methods.length === 0) return ''

  const raw = extractPaymentMethodText(rawValue)
  if (!raw) return fallbackId || ''
  const rawNorm = normalizeText(raw)
  const byId = methods.find((method) => method.id === raw)
  if (byId) return byId.id

  let bestId = fallbackId || ''
  let bestScore = -1

  for (const method of methods) {
    const score = scorePaymentMethod(rawNorm, method)

    if (score > bestScore) {
      bestScore = score
      bestId = method.id
    }
  }

  return bestScore >= 0.78 ? bestId : (fallbackId || '')
}

function buildInferredDefaults(
  doc: Documento | null,
  totalAmount: number | null,
  methods: PaymentMethod[],
) {
  const data = getDocumentData(doc)
  const saveMeta = data._save && typeof data._save === 'object'
    ? data._save as Record<string, unknown>
    : {}
  const rawPayments = getDocumentValue(
    data,
    'pagos',
    'pago',
    'payments',
    'payment',
    'payment_method',
    'payment_type',
    'payment_terms',
    'metodo_pago',
    'metodo_de_pago',
    'forma_pago',
    'forma_de_pago',
    'tipo_pago',
    'tipo_de_pago',
    'medio_pago',
    'medio_de_pago',
    'condicion_pago',
    'condiciones_pago',
    'metodo',
  )
  const fallbackMethodId = typeof saveMeta.payment_method_id === 'string'
    ? saveMeta.payment_method_id
    : ''
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
    paymentMethodId: pickPaymentMethodId(
      saveMeta.payment_method_id ?? saveMeta.payment_method ?? rawPayments,
      methods,
      fallbackMethodId,
    ),
    paidAmount: paymentStatus === 'partial' && paid == null ? '' : formatMoney(paid),
    pendingAmount: paymentStatus === 'paid' ? '0.00' : formatMoney(pending),
    paidAt: paidAtValue,
    notes: typeof saveMeta.notes === 'string' ? saveMeta.notes : '',
  }
}

function getMatchReasonLabel(reason: string | null | undefined): string {
  switch (reason) {
    case 'create_new': return 'Create new product'
    case 'manual': return 'Manual selection'
    case 'alias_exact': return 'Exact alias'
    case 'alias': return 'Suggested alias'
    case 'name_exact': return 'Exact name'
    case 'core_exact': return 'Base name'
    case 'name_partial': return 'Partial name'
    case 'core_partial': return 'Partial base'
    case 'fuzzy': return 'Similar'
    default: return 'No link'
  }
}

export default function SaveDocumentModal({ doc, open, resumeMode = false, onClose, onSaved }: SaveDocumentModalProps) {
  const [destination, setDestination] = useState<DocumentSaveDestination>('expense')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [paymentStatus, setPaymentStatus] = useState<DocumentPaymentStatus>('pending')
  const [paymentMethodId, setPaymentMethodId] = useState('')
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([])
  const [paidAmount, setPaidAmount] = useState('')
  const [pendingAmount, setPendingAmount] = useState('')
  const [paidAt, setPaidAt] = useState(() => new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [saveMessage, setSaveMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({})
  const [updateStock, setUpdateStock] = useState(false)
  const [lineMatches, setLineMatches] = useState<DocumentLineMatch[]>([])
  const [lineMatchSelection, setLineMatchSelection] = useState<Record<number, string>>({})
  const [persistAliasByLine, setPersistAliasByLine] = useState<Record<number, boolean>>({})
  const [createNewByLine, setCreateNewByLine] = useState<Record<number, boolean>>({})
  const [loadingLineMatches, setLoadingLineMatches] = useState(false)
  const lineItems = useMemo(() => {
    const data = getDocumentData(doc)
    const items = data.line_items as Array<Record<string, unknown>> | undefined
    if (!Array.isArray(items)) return []
    return items
      .filter((item) => item && typeof item === 'object')
      .map((item) => {
        const row = item as Record<string, unknown>
        const quantity = parseMoney(
          row.quantity ?? row.cantidad ?? row.qty ?? row.cant ?? row.amount ?? null,
        )
        const unitPrice = parseMoney(
          row.unit_price ?? row.precio_unitario ?? row['p. unitario'] ?? row.price ?? null,
        )
        return {
          description: getLineItemDescription(row),
          unit: getLineItemUnit(row),
          quantity,
          unitPrice,
        }
      })
      .filter((item) => item.quantity != null || item.description)
  }, [doc])
  const stockPreviewLines = useMemo(() => {
    return lineItems.slice(0, 6).map((item) => ({
      quantity: item.quantity ?? 0,
      unit: item.unit || '',
      description: String(item.description ?? 'Item').trim() || 'Item',
    }))
  }, [lineItems])

  const hasStockItems = lineItems.length > 0
  const hasLoadedCapabilities = Object.keys(capabilities).length > 0
  const canSaveInvoice = hasLoadedCapabilities
    ? Boolean(capabilities.purchases || capabilities.invoicing)
    : true
  const canSaveExpense = capabilities.expenses !== false
  const canUpdateStock = hasStockItems && Boolean(capabilities.inventory)
  const saveDestinationChoices = useMemo(() => {
    const fallbackChoices: Array<DocumentCandidateDestination & { code: DocumentSaveDestination }> = []
    if (canSaveInvoice) {
      fallbackChoices.push({
        code: 'supplier_invoice',
        label: 'Supplier invoice',
        target: 'purchases',
        target_tables: ['purchases', 'expenses'],
        save_api: 'save_document',
        score: 0,
        save_ready: true,
        required_fields_ok: true,
        missing_fields: [],
        needs_human_review: false,
        reason: '',
        confirmation_required: true,
        capabilities: {
          supports_update_stock: true,
          supports_line_matching: true,
          supports_partial_payment: true,
          supports_multi_record_save: true,
        },
      })
    }
    if (canSaveExpense) {
      fallbackChoices.push({
        code: 'expense',
        label: 'Expense',
        target: 'expenses',
        target_tables: ['expenses'],
        save_api: 'save_document',
        score: 0,
        save_ready: true,
        required_fields_ok: true,
        missing_fields: [],
        needs_human_review: false,
        reason: '',
        confirmation_required: true,
        capabilities: {
          supports_update_stock: false,
          supports_line_matching: false,
          supports_partial_payment: true,
          supports_multi_record_save: false,
        },
      })
    }
    fallbackChoices.push({
      code: 'recipe',
      label: 'Recipe',
      target: 'recipes',
      target_tables: ['recipes'],
      save_api: 'save_document',
      score: 0,
      save_ready: true,
      required_fields_ok: true,
      missing_fields: [],
      needs_human_review: false,
      reason: '',
      confirmation_required: false,
      capabilities: {
        supports_update_stock: false,
        supports_line_matching: false,
        supports_partial_payment: false,
        supports_multi_record_save: true,
      },
    })

    const rawChoices = doc ? getCandidateSaveDestinations(doc) : []
    const typedChoices = rawChoices
      .map((choice) => {
        if (choice.code === 'recipe' || choice.code === 'expense' || choice.code === 'supplier_invoice') {
          return choice as DocumentCandidateDestination & { code: DocumentSaveDestination }
        }
        return null
      })
      .filter((choice): choice is DocumentCandidateDestination & { code: DocumentSaveDestination } => Boolean(choice))
      .filter((choice) => {
        if (choice.code === 'supplier_invoice') return canSaveInvoice
        if (choice.code === 'expense') return canSaveExpense
        return true
      })

    return typedChoices.length > 0 ? typedChoices : fallbackChoices
  }, [doc, canSaveExpense, canSaveInvoice])
  const activeDestinationMeta = saveDestinationChoices.find((choice) => choice.code === destination) || null

  const totalAmount = useMemo(() => {
    if (!doc) return null
    if (doc.monto_total != null && !Number.isNaN(Number(doc.monto_total))) return Number(doc.monto_total)
    const data = getDocumentData(doc)
    return parseMoney(getDocumentValue(data, 'monto_total', 'total', 'amount', 'importe', 'grand_total', 'total_general'))
  }, [doc])
  const activePaymentMethods = useMemo(
    () => paymentMethods.filter((method) => method.is_active !== false),
    [paymentMethods],
  )
  const inferredDefaults = useMemo(
    () => buildInferredDefaults(doc, totalAmount, activePaymentMethods),
    [doc, totalAmount, activePaymentMethods],
  )

  useEffect(() => {
    if (!open || !doc) return

    const initialDefaults = buildInferredDefaults(doc, totalAmount, activePaymentMethods)
    const suggested = suggestSaveDestination(doc)

    fetchSaveCapabilities().then(setCapabilities).catch(() => {})
    listPaymentMethods()
      .then((methods) => setPaymentMethods(Array.isArray(methods) ? methods : []))
      .catch(() => setPaymentMethods([]))

    setUpdateStock(false)
    setShowAdvanced(false)
    setSaveMessage('')
    setLineMatches([])
    setLineMatchSelection({})
    setPersistAliasByLine({})
    setCreateNewByLine({})
    setDestination(suggested)
    setPaymentStatus(initialDefaults.paymentStatus)
    setPaymentMethodId(initialDefaults.paymentMethodId)
    setPaidAt(initialDefaults.paidAt)
    setNotes(initialDefaults.notes)
    setError('')

    if (suggested === 'recipe') {
      setPaidAmount('')
      setPendingAmount('')
      return
    }

    setPaidAmount(initialDefaults.paidAmount)
    setPendingAmount(initialDefaults.pendingAmount)
  }, [open, doc?.id])

  useEffect(() => {
    if (!open || saveDestinationChoices.length === 0) return
    if (saveDestinationChoices.some((choice) => choice.code === destination)) return
    setDestination(saveDestinationChoices[0].code)
  }, [open, destination, saveDestinationChoices])

  useEffect(() => {
    if (!open || !doc || activePaymentMethods.length === 0) return

    const nextMethodId = buildInferredDefaults(doc, totalAmount, activePaymentMethods).paymentMethodId
    setPaymentMethodId((current) => {
      if (current && activePaymentMethods.some((method) => method.id === current)) return current
      return nextMethodId
    })
  }, [open, doc?.id, totalAmount, activePaymentMethods])

  useEffect(() => {
    if (!open || !doc?.id || !hasStockItems) return
    let cancelled = false
    setLoadingLineMatches(true)
    fetchDocumentLineMatchCandidates(doc.id)
      .then((rows) => {
        if (cancelled) return
        setLineMatches(rows)
        const nextSelection: Record<number, string> = {}
        const nextPersist: Record<number, boolean> = {}
        for (const row of rows) {
          nextSelection[row.line_index] = row.selected_product_id || ''
          nextPersist[row.line_index] = true
        }
        setLineMatchSelection(nextSelection)
        setPersistAliasByLine(nextPersist)
      })
      .catch(() => {
        if (cancelled) return
        setLineMatches([])
      })
      .finally(() => {
        if (!cancelled) setLoadingLineMatches(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, doc?.id, hasStockItems])

  if (!open || !doc) return null
  if (!canSaveDocument(doc)) return null

  const routingDecision = doc.routing_decision || null
  const reviewHints = Array.isArray(doc.review_hints) ? doc.review_hints : []
  const canSubmit = routingDecision ? routingDecision.required_fields_ok : true
  const reviewIsReady = routingDecision ? routingDecision.required_fields_ok : true
  const reviewTitle = resumeMode
    ? 'Complete pending stock'
    : (reviewIsReady ? 'Ready to save' : 'Review before saving')
  const reviewSummary = resumeMode
    ? 'The purchase already exists. This step only appears if there are still unlinked lines to update stock.'
    : (routingDecision?.reason
      || 'Review the result and use advanced options only if you need to change the destination or complete data.')
  const destinationTitle = activeDestinationMeta?.label || (
    destination === 'supplier_invoice'
      ? 'Supplier invoice'
      : destination === 'recipe'
      ? 'Recipe'
      : 'Expense'
  )
  const destinationSummary = activeDestinationMeta?.target_tables?.length
    ? `It will be saved in ${activeDestinationMeta.target_tables.join(', ')}.`
    : destination === 'supplier_invoice'
      ? 'It will be saved in purchases or accounts payable.'
      : destination === 'recipe'
        ? 'It will be saved as a recipe ready for production.'
        : 'It will be recorded in the expenses module.'
  const effectiveLineMatches = lineMatches.length > 0
    ? lineMatches
    : lineItems.map((item, index) => ({
        line_index: index,
        description: String(item.description ?? ''),
        quantity: item.quantity ?? 0,
        unit_price: item.unitPrice ?? 0,
        selected_product_id: null,
        selected_reason: null,
        inferred_factor: 1,
        candidates: [],
      }))
  const isLineResolved = (lineIndex: number) => {
    const selectedId = lineMatchSelection[lineIndex]
    return (
      (typeof selectedId === 'string' && selectedId.trim().length > 0)
      || createNewByLine[lineIndex] === true
    )
  }
  const matchedLines = effectiveLineMatches.filter((row) => {
    return isLineResolved(row.line_index)
  }).length
  const unmatchedLines = Math.max(effectiveLineMatches.length - matchedLines, 0)
  const hiddenStockPreview = Math.max(lineItems.length - stockPreviewLines.length, 0)

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
      setUpdateStock(false)
      setPaidAmount('')
      setPendingAmount('')
      return
    }
    if (nextDestination !== 'supplier_invoice') {
      setUpdateStock(false)
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
      if (destination === 'supplier_invoice' && updateStock && canUpdateStock) {
        payload.line_matches = effectiveLineMatches
          .map((row) => {
            const selectedId = lineMatchSelection[row.line_index] || null
            const isCreateNew = !selectedId && createNewByLine[row.line_index] === true
            if (!selectedId && !isCreateNew) return null
            return {
              line_index: row.line_index,
              product_id: selectedId || null,
              persist_alias: persistAliasByLine[row.line_index] !== false,
              create_new: isCreateNew,
            }
          })
          .filter(Boolean) as typeof payload.line_matches
      }

      if (destination !== 'recipe') {
        payload.payment_status = paymentStatus
        payload.payment_method_id = paymentMethodId || undefined
        payload.paid_at = paymentStatus === 'paid' ? paidAt : undefined
        payload.notes = notes.trim() || undefined

        if (paymentStatus === 'partial') {
          if (!paidAmount.trim() && !pendingAmount.trim()) {
            throw new Error('You must indicate how much is paid or how much is left.')
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
      if (result.message) {
        setSaveMessage(result.message)
      } else {
        onClose()
      }
    } catch (err: any) {
      const raw = err?.response?.data?.detail
      const detail = Array.isArray(raw)
        ? raw.map((e: any) => e.msg ?? JSON.stringify(e)).join(' | ')
        : typeof raw === 'string' ? raw : null
      setError(detail || err?.message || 'Could not save the document.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={overlay}>
      <div style={modal}>
        <div style={header}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>{resumeMode ? 'Complete pending stock' : 'Save document'}</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{doc.nombre_archivo}</div>
          </div>
          <button onClick={onClose} style={closeBtn} disabled={saving} aria-label="Close modal">Ã—</button>
        </div>

        <div style={body}>
          <div>
            <div style={{ ...heroBox, ...(reviewIsReady ? heroBoxReady : heroBoxReview) }}>
              <div>
                <div style={heroEyebrow}>Final review</div>
                <div style={heroTitle}>{reviewTitle}</div>
                <div style={heroCopy}>{reviewSummary}</div>
                <div style={heroMetaRow}>
                  <span style={heroPill}>{destinationTitle}</span>
                  {!canSubmit && <span style={heroPillWarn}>Missing required fields</span>}
                  {destination === 'supplier_invoice' && hasStockItems && (
                    <span style={heroPillMuted}>
                      {matchedLines}/{effectiveLineMatches.length} lines linked
                    </span>
                  )}
                </div>
                <div style={heroSubCopy}>{destinationSummary}</div>
              </div>
              <button
                type="button"
                onClick={() => setShowAdvanced((current) => !current)}
                style={secondaryBtn}
                disabled={saving}
              >
                {showAdvanced ? 'Hide advanced options' : 'Change destination or options'}
              </button>
            </div>
            {routingDecision && (
              <div style={routingDecision.required_fields_ok ? infoBox : warnBox}>
                {routingDecision.reason || 'Routing decision available.'}
                {!routingDecision.required_fields_ok && routingDecision.missing_fields.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    Missing: {routingDecision.missing_fields.join(', ')}
                  </div>
                )}
              </div>
            )}
            {reviewHints.length > 0 && (
              <div style={{ ...infoBox, marginTop: 10 }}>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>Priority fields before saving</div>
                <div style={{ display: 'grid', gap: 6 }}>
                  {reviewHints.slice(0, 3).map((hint) => (
                    <div key={hint.field} style={{ fontSize: 13, color: '#334155' }}>
                      <strong>{hint.priority}. {hint.field}</strong>
                      {hint.is_missing && <span style={{ marginLeft: 6, color: '#b45309' }}>Missing</span>}
                      {hint.confirmed_examples.length > 0 && (
                        <div style={{ marginTop: 2, color: '#64748b' }}>
                          Examples: {hint.confirmed_examples.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {showAdvanced && (
            <div style={advancedSection}>
              <div style={advancedCard}>
                <div style={label}>Save as</div>
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(saveDestinationChoices.length, 1)}, minmax(0, 1fr))`, gap: 8 }}>
                  {saveDestinationChoices.map((choice) => (
                    <button
                      type="button"
                      key={choice.code}
                      onClick={() => handleDestinationChange(choice.code)}
                      style={{ ...choiceBtn, ...(destination === choice.code ? choiceBtnActive : null) }}
                      disabled={saving}
                    >
                      <div>{choice.label}</div>
                      {choice.target_tables.length > 0 && (
                        <div style={{ marginTop: 4, fontSize: 11, color: destination === choice.code ? '#0f172a' : '#64748b' }}>
                          {choice.target_tables.join(' + ')}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>

          {canUpdateStock && destination === 'supplier_invoice' && (
            <label style={{ ...advancedCard, display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', userSelect: 'none' }}>
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
                <div style={stockChipWrap}>
                  {stockPreviewLines.map((line, i) => (
                    <span key={i} style={stockChip}>
                      +{formatCompactNumber(line.quantity, { maxDecimals: 3 })}
                      {line.unit ? ` ${line.unit}` : ''} - {line.description.slice(0, 34)}
                    </span>
                  ))}
                  {hiddenStockPreview > 0 && (
                    <span style={stockChipMore}>+{hiddenStockPreview} more lines</span>
                  )}
                </div>
              </div>
            </label>
          )}

          {destination === 'supplier_invoice' && hasStockItems && (
            <div style={matchPanel}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>Link lines to products</div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                    Choose the right product for each line. If you link it manually, it will be saved as an alias for future invoices.
                  </div>
                </div>
                <div style={{ fontSize: 12, color: unmatchedLines > 0 ? '#92400e' : '#166534', fontWeight: 600 }}>
                  {matchedLines}/{effectiveLineMatches.length} lines resolved
                </div>
              </div>

              {loadingLineMatches ? (
                <div style={hintBox}>Buscando productos parecidos...</div>
              ) : (
                <div style={matchTableWrap}>
                  <table style={matchTable}>
                    <thead>
                      <tr>
                        <th style={matchTh}>Linea</th>
                        <th style={matchTh}>Detected product</th>
                        <th style={matchTh}>Candidatos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {effectiveLineMatches.map((row) => {
                        const fallbackLine = lineItems[row.line_index]
                        const rowDescription = String(
                          row.description || fallbackLine?.description || `Línea ${row.line_index + 1}`,
                        ).trim()
                        const rowQuantityRaw = Number(row.quantity)
                        const rowQuantity = Number.isFinite(rowQuantityRaw)
                          ? rowQuantityRaw
                          : (fallbackLine?.quantity ?? 0)
                        const rowUnitPriceRaw = Number(row.unit_price)
                        const rowUnitPrice = Number.isFinite(rowUnitPriceRaw)
                          ? rowUnitPriceRaw
                          : (fallbackLine?.unitPrice ?? 0)
                        const rowUnit = fallbackLine?.unit || ''
                        const selectedId = lineMatchSelection[row.line_index] || ''
                        const isCreateNew = !selectedId && createNewByLine[row.line_index] === true
                        const selectedCandidate = row.candidates.find((candidate) => candidate.product_id === selectedId)
                        const selectedReason = selectedId
                          ? (selectedId === row.selected_product_id
                              ? row.selected_reason
                              : selectedCandidate?.reason || 'manual')
                          : (isCreateNew ? 'create_new' : null)
                        return (
                          <tr key={row.line_index}>
                            <td style={matchTdCompact}>
                              <div style={{ fontWeight: 600, color: '#0f172a' }}>#{row.line_index + 1}</div>
                              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                                +{formatCompactNumber(rowQuantity, { maxDecimals: 3 })}
                                {rowUnit ? ` ${rowUnit}` : ''} - {formatCompactNumber(rowUnitPrice, { maxDecimals: 4 })}
                              </div>
                            </td>
                            <td style={matchTd}>
                              <div style={{ fontWeight: 600, color: '#0f172a' }}>{rowDescription}</div>
                              <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                                {selectedReason ? getMatchReasonLabel(selectedReason) : 'No link'} - factor {Number(selectedCandidate?.inferred_factor ?? row.inferred_factor ?? 1).toFixed(2)}
                              </div>
                            </td>
                            <td style={matchTd}>
                              <select
                                value={selectedId}
                                onChange={(e) => {
                                  setLineMatchSelection((prev) => ({ ...prev, [row.line_index]: e.target.value }))
                                  if (e.target.value) {
                                    setCreateNewByLine((prev) => ({ ...prev, [row.line_index]: false }))
                                  }
                                }}
                                style={{ ...input, minWidth: 260 }}
                                disabled={saving}
                              >
                                <option value="">Sin vincular</option>
                                {row.candidates.map((candidate) => (
                                  <option key={candidate.product_id} value={candidate.product_id}>
                                    {candidate.name}{candidate.sku ? ` (${candidate.sku})` : ''} - {candidate.unit} - {Math.round(candidate.score * 100)}%
                                  </option>
                                ))}
                              </select>
                              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                                {!selectedId ? (
                                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: createNewByLine[row.line_index] ? '#166534' : '#475569', fontWeight: createNewByLine[row.line_index] ? 600 : 400, cursor: 'pointer' }}>
                                    <input
                                      type="checkbox"
                                      checked={createNewByLine[row.line_index] === true}
                                      onChange={(e) => setCreateNewByLine((prev) => ({ ...prev, [row.line_index]: e.target.checked }))}
                                      disabled={saving}
                                    />
                                    Create new product (+{formatCompactNumber(rowQuantity, { maxDecimals: 3 })}{rowUnit ? ` ${rowUnit}` : ''} - {rowDescription.slice(0, 28)})
                                  </label>
                                ) : (
                                  <div style={{ fontSize: 12, color: '#64748b' }}>
                                    {row.candidates.slice(0, 3).map((candidate) => candidate.name).join(', ')}
                                  </div>
                                )}
                                {selectedId && (
                                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#475569' }}>
                                    <input
                                      type="checkbox"
                                      checked={persistAliasByLine[row.line_index] !== false}
                                      onChange={(e) => setPersistAliasByLine((prev) => ({ ...prev, [row.line_index]: e.target.checked }))}
                                      disabled={saving}
                                    />
                                    Save alias
                                  </label>
                                )}
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {updateStock && unmatchedLines > 0 && (
                <div style={warnBox}>
                  There are {unmatchedLines} unlinked line(s). The purchase and expense will be saved, but those lines will not enter stock until you choose a product.
                </div>
              )}
            </div>
          )}

          {destination !== 'recipe' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
                <label style={field}>
                  <span style={label}>Payment status</span>
                  <select
                    value={paymentStatus}
                    onChange={(e) => handlePaymentStatusChange(e.target.value as DocumentPaymentStatus)}
                    style={input}
                    disabled={saving}
                  >
                    <option value="pending">Pending</option>
                    <option value="partial">Partial</option>
                    <option value="paid">Paid</option>
                  </select>
                </label>

                <label style={field}>
                  <span style={label}>Method</span>
                  <select
                    value={paymentMethodId}
                    onChange={(e) => setPaymentMethodId(e.target.value)}
                    style={input}
                    disabled={saving}
                  >
                    {activePaymentMethods.length === 0 ? (
                      <option value="">No payment methods configured</option>
                    ) : (
                      activePaymentMethods.map((method) => (
                        <option key={method.id} value={method.id}>
                          {method.name}
                        </option>
                      ))
                    )}
                  </select>
                </label>

                {paymentStatus === 'paid' && (
                  <label style={field}>
                    <span style={label}>Payment date</span>
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
                  <span style={label}>Paid</span>
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
                  <span style={label}>Remaining</span>
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
            </div>
          )}

          {totalAmount != null && (
            <div style={summaryBox}>
              Total detectado: <strong>{doc.moneda || '$'} {totalAmount.toFixed(2)}</strong>
            </div>
          )}

          {error && <div style={errorBox}>{error}</div>}
          {saveMessage && (
            <div style={saveMessage.includes('âš ï¸') ? warnBox : infoBox}>
              {saveMessage}
            </div>
          )}
        </div>

        <div style={footer}>
          <button onClick={onClose} style={secondaryBtn} disabled={saving}>
            {saveMessage ? 'Close' : 'Cancel'}
          </button>
          {!saveMessage && (
            <button onClick={submit} style={primaryBtn} disabled={saving || !canSubmit}>
              {saving ? 'Saving...' : (
                resumeMode && destination === 'supplier_invoice'
                  ? 'Complete stock'
                  : getImportadorSaveActionLabel(destination)
              )}
            </button>
          )}
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
  overflowY: 'auto',
}

const modal: React.CSSProperties = {
  width: '100%',
  maxWidth: 720,
  maxHeight: 'calc(100vh - 2rem)',
  background: '#fff',
  borderRadius: 14,
  boxShadow: '0 22px 48px rgba(15, 23, 42, 0.22)',
  overflow: 'hidden',
  display: 'flex',
  flexDirection: 'column',
}

const header: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  padding: '1rem 1.1rem',
  borderBottom: '1px solid #e2e8f0',
  flexShrink: 0,
  background: '#fff',
}

const body: React.CSSProperties = {
  display: 'grid',
  gap: 16,
  padding: '1rem 1.1rem',
  overflowY: 'auto',
  minHeight: 0,
  flex: '1 1 auto',
  background: '#f8fafc',
}

const footer: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  padding: '0.9rem 1.1rem 1rem',
  borderTop: '1px solid #e2e8f0',
  flexShrink: 0,
  background: '#fff',
  boxShadow: '0 -10px 20px rgba(15, 23, 42, 0.06)',
}

const heroBox: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  flexWrap: 'wrap',
  padding: '0.95rem 1rem',
  borderRadius: 12,
}

const heroBoxReady: React.CSSProperties = {
  background: '#eefaf2',
  border: '1px solid #86efac',
}

const heroBoxReview: React.CSSProperties = {
  background: '#fff7ed',
  border: '1px solid #fdba74',
}

const heroEyebrow: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 800,
  color: '#1d4ed8',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
}

const heroTitle: React.CSSProperties = {
  marginTop: 4,
  fontSize: 20,
  fontWeight: 800,
  color: '#0f172a',
}

const heroCopy: React.CSSProperties = {
  marginTop: 6,
  fontSize: 13,
  color: '#334155',
  maxWidth: 420,
}

const heroMetaRow: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
  marginTop: 8,
}

const heroPill: React.CSSProperties = {
  borderRadius: 999,
  padding: '0.2rem 0.55rem',
  background: '#dbeafe',
  color: '#1e40af',
  fontSize: 11,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.03em',
}

const heroPillWarn: React.CSSProperties = {
  ...heroPill,
  background: '#ffedd5',
  color: '#9a3412',
}

const heroPillMuted: React.CSSProperties = {
  ...heroPill,
  background: '#e2e8f0',
  color: '#334155',
}

const heroSubCopy: React.CSSProperties = {
  marginTop: 7,
  fontSize: 12,
  color: '#475569',
}

const advancedSection: React.CSSProperties = {
  display: 'grid',
  gap: 16,
  paddingTop: 4,
  borderTop: '1px solid #e2e8f0',
}

const advancedCard: React.CSSProperties = {
  border: '1px solid #e2e8f0',
  borderRadius: 12,
  padding: '0.8rem',
  background: '#ffffff',
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

const matchPanel: React.CSSProperties = {
  display: 'grid',
  gap: 12,
  padding: '0.9rem',
  borderRadius: 12,
  border: '1px solid #dbeafe',
  background: '#ffffff',
}

const matchTableWrap: React.CSSProperties = {
  overflowX: 'auto',
}

const matchTable: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
}

const matchTh: React.CSSProperties = {
  textAlign: 'left',
  fontSize: 12,
  color: '#64748b',
  fontWeight: 700,
  padding: '0.55rem 0.5rem',
  borderBottom: '1px solid #dbeafe',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const matchTd: React.CSSProperties = {
  verticalAlign: 'top',
  padding: '0.7rem 0.5rem',
  borderBottom: '1px solid #e2e8f0',
}

const matchTdCompact: React.CSSProperties = {
  ...matchTd,
  width: 84,
  whiteSpace: 'nowrap',
}

const errorBox: React.CSSProperties = {
  padding: '0.75rem 0.85rem',
  borderRadius: 10,
  background: '#fef2f2',
  border: '1px solid #fecaca',
  color: '#b91c1c',
  fontSize: 13,
}

const warnBox: React.CSSProperties = {
  padding: '0.75rem 0.85rem',
  borderRadius: 10,
  background: '#fffbeb',
  border: '1px solid #fcd34d',
  color: '#92400e',
  fontSize: 13,
}

const infoBox: React.CSSProperties = {
  padding: '0.75rem 0.85rem',
  borderRadius: 10,
  background: '#f0fdf4',
  border: '1px solid #86efac',
  color: '#166534',
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

const stockChipWrap: React.CSSProperties = {
  display: 'flex',
  gap: 6,
  flexWrap: 'wrap',
  marginTop: 6,
}

const stockChip: React.CSSProperties = {
  border: '1px solid #dbeafe',
  borderRadius: 999,
  background: '#f8fbff',
  color: '#334155',
  fontSize: 11,
  fontWeight: 600,
  padding: '0.2rem 0.55rem',
}

const stockChipMore: React.CSSProperties = {
  ...stockChip,
  background: '#f1f5f9',
  border: '1px solid #e2e8f0',
  color: '#475569',
}

const closeBtn: React.CSSProperties = {
  border: '1px solid #cbd5e1',
  background: '#fff',
  color: '#475569',
  width: 30,
  height: 30,
  lineHeight: '26px',
  borderRadius: 999,
  textAlign: 'center',
  fontSize: 18,
  cursor: 'pointer',
}
