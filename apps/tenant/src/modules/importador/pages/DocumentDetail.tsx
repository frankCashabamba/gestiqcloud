import React, { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { canSaveDocument, canSaveProductsSheet, fetchDocument, fetchDocumentLineMatchCandidates, fetchSaveCapabilities, fetchLineItemSlots, confirmDocument, editDocumentFields, rejectDocument, suggestSaveDestination, syncAllRecipes, syncRecipe, saveDailyLog, getDocCategory, getDocumentData, getDocumentDisplayStatus, hasConfirmedDocumentData, isDocumentSaved, type Documento, type LogCambio, type LineItemSlot, type SaveDocumentResult, type SaveDailyLogResult, type SaveProductsFromDocumentResult, type SyncRecipeResult, type SyncRecipesResult } from '../services'
import { IMPORTADOR_FLOW_STEPS, getImportadorSaveActionLabel, getImportadorSavedAsLabel, STATUS_LABELS } from '../constants'
import { fetchCanonicalFields, formatFieldLabel, type CanonicalField } from '../services'

const SaveDocumentModal = lazy(() => import('../components/SaveDocumentModal'))
const SaveProductsModal = lazy(() => import('../components/SaveProductsModal'))
const ReprocessPanel = lazy(() => import('./ReprocessPanel'))

const DETAIL_POLL_INTERVAL_MS = 5000

type ReprocessMode = 'fast' | 'deep'

function ReprocessActions({
  onFast,
  onDeep,
  fastLabel,
  deepLabel,
  title,
  copy,
}: {
  onFast: () => void
  onDeep: () => void
  fastLabel: string
  deepLabel: string
  title: string
  copy: string
}) {
  return (
    <div style={reprocessCard}>
      <div style={reprocessHeaderLayout}>
        <div style={{ minWidth: 0 }}>
          <div style={reprocessEyebrow}>Reprocesado</div>
          <div style={reprocessTitle}>{title}</div>
          <div style={reprocessCopy}>{copy}</div>
        </div>
        <div style={reprocessButtonRow}>
          <button onClick={onFast} style={reprocessFastButton}>
            {fastLabel}
          </button>
          <button onClick={onDeep} style={reprocessDeepButton}>
            {deepLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function getReviewInputType(fieldType: string | undefined): 'text' | 'number' | 'date' {
  const normalized = String(fieldType || '').trim().toLowerCase()
  if (normalized === 'numeric' || normalized === 'number') return 'number'
  if (normalized === 'date') return 'date'
  return 'text'
}

type ActivityItem = {
  id: string
  title: string
  when: string
  note?: string
}

type LineItemPageGroup = {
  source_page: number
  header_index?: number
  headers: string[]
  headers_norm: string[]
  line_items: Record<string, unknown>[]
}

// EditableLineItem es dinÃ¡mico: slot â†’ value
type EditableLineItem = Record<string, string>

function getEditableLineItems(data: Record<string, unknown>, slots: LineItemSlot[]): EditableLineItem[] {
  const raw = data.line_items as unknown
  if (!Array.isArray(raw)) return []
  return raw
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    .map((item) => {
      const editable: EditableLineItem = {}
      for (const s of slots) editable[s.slot] = String(item[s.slot] ?? '')
      return editable
    })
}

function createEmptyEditableLineItem(slots: LineItemSlot[]): EditableLineItem {
  const item: EditableLineItem = {}
  for (const s of slots) item[s.slot] = ''
  return item
}

function formatLineCellValue(value: unknown): string {
  if (value == null) return 'â€”'
  const text = String(value).trim()
  if (!text || text.toLowerCase() === 'nan') return 'â€”'
  return text
}

// Slots numÃ©ricos que se alinean a la derecha
const _NUMERIC_SLOTS = new Set(['quantity', 'unit_price', 'total_price'])
const _MONO_SLOTS = new Set(['supplier_ref'])

function LineItemsPreview({ items, slots, title, subtitle }: {
  items: Record<string, unknown>[]
  slots: LineItemSlot[]
  title: string
  subtitle?: string
}) {
  if (!items.length || !slots.length) return null
  // Solo mostrar columnas que tengan al menos un valor en los datos
  const visibleSlots = slots.filter(s => items.some(i => i[s.slot] != null && String(i[s.slot]).trim() !== ''))
  return (
    <div style={{ marginTop: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 13, color: '#6b7280', fontWeight: 600 }}>{title}</div>
        {subtitle && <div style={{ fontSize: 12, color: '#64748B' }}>{subtitle}</div>}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#f9fafb' }}>
            {visibleSlots.map(s => (
              <th key={s.slot} style={{ padding: '0.3rem 0.5rem', textAlign: _NUMERIC_SLOTS.has(s.slot) ? 'right' : 'left', color: '#374151' }}>
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${index}-${String(item[visibleSlots[0]?.slot] ?? '')}`} style={{ borderTop: '1px solid #e5e7eb' }}>
              {visibleSlots.map(s => (
                <td key={s.slot} style={{
                  padding: '0.3rem 0.5rem',
                  textAlign: _NUMERIC_SLOTS.has(s.slot) ? 'right' : 'left',
                  color: _MONO_SLOTS.has(s.slot) ? '#6b7280' : '#111827',
                  fontFamily: _MONO_SLOTS.has(s.slot) ? 'monospace' : undefined,
                  fontSize: _MONO_SLOTS.has(s.slot) ? 12 : undefined,
                }}>
                  {formatLineCellValue(item[s.slot])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function resolveGroupCellValue(
  item: Record<string, unknown>,
  rawHeader: string,
  canonicalHeader: string,
): unknown {
  const extraColumns = (
    item.extra_columns && typeof item.extra_columns === 'object' && !Array.isArray(item.extra_columns)
      ? item.extra_columns as Record<string, unknown>
      : null
  )

  const canonicalKey = String(canonicalHeader || '').trim()
  if (canonicalKey) {
    const canonicalValue = item[canonicalKey]
    if (canonicalValue != null && String(canonicalValue).trim() !== '') return canonicalValue
  }

  const rawKey = String(rawHeader || '').trim()
  if (rawKey && rawKey in item) {
    const rawValue = item[rawKey]
    if (rawValue != null && String(rawValue).trim() !== '') return rawValue
  }

  if (extraColumns && rawKey && rawKey in extraColumns) {
    const extraValue = extraColumns[rawKey]
    if (extraValue != null && String(extraValue).trim() !== '') return extraValue
  }

  return canonicalKey ? item[canonicalKey] : undefined
}

function isGroupedNumericColumn(rawHeader: string, canonicalHeader: string): boolean {
  const normalized = String(canonicalHeader || rawHeader || '').trim().toLowerCase()
  return ['quantity', 'unit_price', 'total_price'].includes(normalized)
    || /(?:cantidad|precio|importe|total|unitario)/i.test(String(rawHeader || ''))
}

function GroupedLineItemsPreview({ group }: { group: LineItemPageGroup }) {
  const columns = group.headers.map((header, index) => ({
    label: header,
    canonical: group.headers_norm[index] || '',
  }))

  if (group.line_items.length === 0 || columns.length === 0) return null

  return (
    <div style={{ marginTop: '0.75rem' }}>
      <div style={{ fontSize: 13, color: '#6b7280', fontWeight: 600, marginBottom: 6 }}>
        PÃ¡gina {group.source_page} Â· Detalle ({group.line_items.length})
      </div>
      <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8 }}>
        Encabezados: {group.headers.join(' Â· ')}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#f9fafb' }}>
            {columns.map((column) => (
              <th
                key={`${column.label}-${column.canonical}`}
                style={{
                  padding: '0.3rem 0.5rem',
                  textAlign: isGroupedNumericColumn(column.label, column.canonical) ? 'right' : 'left',
                  color: '#374151',
                }}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {group.line_items.map((item, index) => (
            <tr key={`group-${group.source_page}-${index}`} style={{ borderTop: '1px solid #e5e7eb' }}>
              {columns.map((column) => (
                <td
                  key={`${column.label}-${column.canonical}`}
                  style={{
                    padding: '0.3rem 0.5rem',
                    textAlign: isGroupedNumericColumn(column.label, column.canonical) ? 'right' : 'left',
                    color: '#111827',
                  }}
                >
                  {formatLineCellValue(resolveGroupCellValue(item, column.label, column.canonical))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function normalizeLineItemPageGroups(data: Record<string, unknown>): LineItemPageGroup[] {
  const rawGroups = data.line_item_page_groups
  if (Array.isArray(rawGroups)) {
    const groups = rawGroups
      .map((group, index): LineItemPageGroup | null => {
        if (!group || typeof group !== 'object' || Array.isArray(group)) return null
        const payload = group as Record<string, unknown>
        const items = Array.isArray(payload.line_items)
          ? payload.line_items.filter((item): item is Record<string, unknown> => (
              Boolean(item) && typeof item === 'object' && !Array.isArray(item)
            ))
          : []
        if (items.length === 0) return null
        const rawPage = Number(payload.source_page ?? index + 1)
        const sourcePage = Number.isFinite(rawPage) && rawPage > 0 ? Math.floor(rawPage) : index + 1
        return {
          source_page: sourcePage,
          header_index: Number.isFinite(Number(payload.header_index))
            ? Math.max(0, Math.floor(Number(payload.header_index)))
            : undefined,
          headers: Array.isArray(payload.headers)
            ? payload.headers.map((value) => String(value ?? '').trim())
            : [],
          headers_norm: Array.isArray(payload.headers_norm)
            ? payload.headers_norm.map((value) => String(value ?? '').trim())
            : [],
          line_items: items,
        }
      })
      .filter((group): group is LineItemPageGroup => Boolean(group))

    if (groups.length > 0) {
      return groups.sort((left, right) => left.source_page - right.source_page)
    }
  }

  const fallbackItems = Array.isArray(data.line_items)
    ? data.line_items.filter((item): item is Record<string, unknown> => (
        Boolean(item) && typeof item === 'object' && !Array.isArray(item)
      ))
    : []
  if (fallbackItems.length === 0) return []
  return [
    {
      source_page: 1,
      headers: [],
      headers_norm: [],
      line_items: fallbackItems,
    },
  ]
}

function summarizeLogDetail(action: string, detail: Record<string, unknown> | null | undefined): string | undefined {
  if (!detail || typeof detail !== 'object') return undefined
  if (action === 'UPLOAD') {
    const filename = typeof detail.filename === 'string' ? detail.filename : null
    return filename ? `File: ${filename}` : undefined
  }
  if (action === 'CONFIRM') {
    const mode = typeof detail.confirmation_mode === 'string' ? detail.confirmation_mode : null
    if (mode === 'corrected_by_user') return 'Confirmed with user changes.'
    if (mode === 'accepted_as_detected') return 'Confirmed as detected.'
    return 'The document data was confirmed.'
  }
  if (action === 'REPROCESS') {
    const reason = typeof detail.reason === 'string' ? detail.reason : null
    if (reason === 'learning_update') return 'Reanalyzed to apply recent confirmed learning.'
    const mode = typeof detail.mode === 'string' ? detail.mode : null
    return mode === 'async' || mode === 'in_place' ? 'Se volviÃ³ a procesar el documento.' : undefined
  }
  if (action === 'EDIT') {
    const fields = Array.isArray(detail.changed_fields) ? detail.changed_fields.map(String).filter(Boolean) : []
    return fields.length ? `Campos actualizados: ${fields.join(', ')}` : 'Se actualizaron los datos del documento.'
  }
  if (action === 'SAVE_DESTINATION') {
    const target = typeof detail.target === 'string' ? detail.target : null
    const status = typeof detail.status === 'string' ? detail.status : null
    if (target && status === 'created') return `Se guardÃ³ en ${target}.`
    if (target) return `Destino: ${target}.`
  }
  return undefined
}

function buildUserActivity(logs: LogCambio[] | undefined): ActivityItem[] {
  if (!logs?.length) return []
  return logs
    .filter((log) => ['UPLOAD', 'EDIT', 'CONFIRM', 'REJECT', 'REPROCESS', 'SAVE_DESTINATION'].includes(log.accion))
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .map((log) => ({
      id: log.id,
      title: (() => {
        if (log.accion === 'CONFIRM') {
          const detail = log.detalle && typeof log.detalle === 'object'
            ? log.detalle as Record<string, unknown>
            : null
          const mode = typeof detail?.confirmation_mode === 'string' ? detail.confirmation_mode : null
          if (mode === 'corrected_by_user') return 'Document confirmed with corrections'
          if (mode === 'accepted_as_detected') return 'Document confirmed as detected'
        }
        if (log.accion === 'UPLOAD') return 'Document uploaded'
        if (log.accion === 'EDIT') return 'Datos editados'
        if (log.accion === 'CONFIRM') return 'Document confirmed'
        if (log.accion === 'REJECT') return 'Document rejected'
        if (log.accion === 'REPROCESS') return 'Reprocesado solicitado'
        return 'Document saved'
      })(),
      when: new Date(log.created_at).toLocaleString(),
      note: summarizeLogDetail(log.accion, log.detalle as Record<string, unknown> | null | undefined),
    }))
}

function latestLogByAction(logs: LogCambio[] | undefined, actions: string[]): LogCambio | undefined {
  if (!logs?.length) return undefined
  const actionSet = new Set(actions)
  return logs
    .filter((log) => actionSet.has(log.accion))
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())[0]
}

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation('importer')
  const [doc, setDoc] = useState<Documento | null>(null)
  const [loading, setLoading] = useState(true)
  const [lineItemSlots, setLineItemSlots] = useState<LineItemSlot[]>([])
  const [canonicalFields, setCanonicalFields] = useState<CanonicalField[]>([])
  const [editMode, setEditMode] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})
  const [editLineItems, setEditLineItems] = useState<EditableLineItem[]>([])
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncingAll, setSyncingAll] = useState(false)
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [saveProductsOpen, setSaveProductsOpen] = useState(false)
  const [savingDailyLog, setSavingDailyLog] = useState(false)
  const [dailyLogResult, setDailyLogResult] = useState<SaveDailyLogResult | null>(null)
  const [saveProductsResult, setSaveProductsResult] = useState<SaveProductsFromDocumentResult | null>(null)
  const [error, setError] = useState('')
  const [rawSyncResult, setSyncResult] = useState<SyncRecipeResult | null>(null)
  const [batchSyncResult, setBatchSyncResult] = useState<SyncRecipesResult | null>(null)
  const [rejectPending, setRejectPending] = useState(false)
  const syncResult = rawSyncResult
    ? {
        ...rawSyncResult,
        total_cost: Number(rawSyncResult.total_cost ?? 0),
        ingredients_count: Number(rawSyncResult.ingredients_count ?? 0),
      }
    : null
  const [activeSheet, setActiveSheet] = useState<string | null>(null)
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({})
  const [lastRefresh, setLastRefresh] = useState(0)
  const [savedInvoiceHasPendingStock, setSavedInvoiceHasPendingStock] = useState(false)
  const lastVisibilityReloadRef = useRef(0)
  const loadRequestSeqRef = useRef(0)

  useEffect(() => {
    fetchSaveCapabilities().then(setCapabilities).catch(() => {
      setError(t('docDetail.errorLoading'))
    })
    fetchLineItemSlots().then(setLineItemSlots).catch(() => {})
    fetchCanonicalFields().then(setCanonicalFields).catch(() => {})
  }, [])
  const load = useCallback(async ({ silent = false, clearCurrent = false }: { silent?: boolean; clearCurrent?: boolean } = {}) => {
    if (!id) return
    const requestSeq = ++loadRequestSeqRef.current
    if (!silent) {
      setLoading(true)
      if (clearCurrent) {
        setDoc(null)
      }
    }
    try {
      const nextDoc = await fetchDocument(id)
      if (requestSeq !== loadRequestSeqRef.current) return
      setDoc(nextDoc)
      setError('')
    } catch {
      if (requestSeq !== loadRequestSeqRef.current) return
      setError(t('docDetail.errorLoading'))
    } finally {
      if (requestSeq === loadRequestSeqRef.current) {
        setLoading(false)
      }
    }
    setLastRefresh(n => n + 1)
  }, [id, t])

  useEffect(() => {
    setEditMode(false)
    setEditFields({})
    setEditLineItems([])
    setSyncResult(null)
    setBatchSyncResult(null)
    setDailyLogResult(null)
    setSaveProductsResult(null)
    setSaveModalOpen(false)
    setSaveProductsOpen(false)
    void load({ clearCurrent: true })
  }, [id, load])

  useEffect(() => {
    const reloadOnVisibility = () => {
      if (document.hidden) return
      const now = Date.now()
      if (now - lastVisibilityReloadRef.current < 15000) return
      lastVisibilityReloadRef.current = now
      void load({ silent: true })
    }
    document.addEventListener('visibilitychange', reloadOnVisibility)
    return () => {
      document.removeEventListener('visibilitychange', reloadOnVisibility)
    }
  }, [load])

  useEffect(() => {
    if (!doc || (doc.estado !== 'PENDING' && doc.estado !== 'PROCESSING')) return

    const intervalId = window.setInterval(() => {
      void load({ silent: true })
    }, DETAIL_POLL_INTERVAL_MS)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [doc?.estado, load])

  // SelecciÃ³n automÃ¡tica de hoja cuando llega un documento nuevo
  useEffect(() => {
    const datos = getDocumentData(doc)
    const sheetMap = datos?.filas_por_hoja && typeof datos.filas_por_hoja === 'object'
      ? Object.keys(datos.filas_por_hoja as Record<string, unknown>)
      : []
    if (sheetMap.length > 0) {
      const preferred = (datos.sheet_usada as string) || sheetMap[0]
      setActiveSheet(preferred)
    } else {
      setActiveSheet(null)
    }
  }, [doc?.id])

  const latestSaveLog = latestLogByAction(doc?.logs, ['SAVE_DESTINATION', 'SAVE_PRODUCTS'])
  const latestReprocessLog = latestLogByAction(doc?.logs, ['REPROCESS'])
  const saveLogIsCurrent = Boolean(
    latestSaveLog
    && (
      !latestReprocessLog
      || new Date(latestSaveLog.created_at).getTime() > new Date(latestReprocessLog.created_at).getTime()
    )
  )
  const savedAsLog = saveLogIsCurrent ? latestSaveLog : undefined
  const _logDest = savedAsLog?.detalle?.['destination'] as string | undefined
  const inferredSavedAs: string | undefined = doc?.saved_as
    ?? (savedAsLog?.accion === 'SAVE_PRODUCTS' ? 'products'
      : _logDest === 'supplier_invoice' ? 'supplier_invoice'
      : _logDest === 'expense' ? 'expense'
      : savedAsLog ? 'supplier_invoice'
      : undefined)
  const isSaved = Boolean(doc && (isDocumentSaved(doc) || saveLogIsCurrent))
  const hasAnySaveModule = Boolean(capabilities.purchases || capabilities.invoicing || capabilities.expenses)
  const saveDestination = doc ? suggestSaveDestination(doc) : 'expense'
  const requiresConfirmedSave = saveDestination !== 'recipe'
  const routingReadyForSave = doc?.routing_decision ? doc.routing_decision.required_fields_ok : true
  const confirmedDataReady = hasConfirmedDocumentData(doc ?? { datos_confirmados: undefined })
  const baseCanResumeSavedInvoice = isSaved && inferredSavedAs === 'supplier_invoice' && hasAnySaveModule && routingReadyForSave && confirmedDataReady

  useEffect(() => {
    let cancelled = false

    if (!baseCanResumeSavedInvoice || !doc?.id) {
      setSavedInvoiceHasPendingStock(false)
      return () => {
        cancelled = true
      }
    }

    fetchDocumentLineMatchCandidates(doc.id)
      .then((rows) => {
        if (cancelled) return
        const hasPending = rows.some((row) => !row.selected_product_id)
        setSavedInvoiceHasPendingStock(hasPending)
      })
      .catch(() => {
        if (!cancelled) setSavedInvoiceHasPendingStock(false)
      })

    return () => {
      cancelled = true
    }
  }, [baseCanResumeSavedInvoice, doc?.id])

  const handleConfirm = async () => {
    if (!id || !doc) return
    setSaving(true)
    try {
      await confirmDocument(id, doc.datos_extraidos || {})
      const updated = await fetchDocument(id)
      setDoc(updated)
      setLastRefresh(n => n + 1)

      const updatedRoutingReady = updated.routing_decision ? updated.routing_decision.required_fields_ok : true
      const updatedSaveDestination = suggestSaveDestination(updated)
      const updatedRequiresConfirmedSave = updatedSaveDestination !== 'recipe'
      const updatedCanSave = !(
        updated.estado === 'IMPORTED'
        || updated.saved_as != null
      ) && canSaveDocument(updated)
        && hasAnySaveModule
        && updated.estado !== 'FAILED'
        && updatedRoutingReady
        && (!updatedRequiresConfirmedSave || hasConfirmedDocumentData(updated))

      if (updatedCanSave) {
        setSaveModalOpen(true)
      }
    } catch { setError(t('docDetail.errorConfirming')) }
    setSaving(false)
  }

  const handleSyncSheet = async () => {
    if (!id) return
    if (activeSheetIsSynced) return
    setSyncing(true)
    setError('')
    setSyncResult(null)
    setBatchSyncResult(null)
    try {
      const result = await syncRecipe(id, activeSheet || undefined)
      setSyncResult({
        ...result,
        total_cost: Number(result.total_cost ?? 0),
        ingredients_count: Number(result.ingredients_count ?? 0),
      })
      load()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || t('docDetail.errorSaving')
      setError(msg)
    }
    setSyncing(false)
  }

  const handleSyncAll = async () => {
    if (!id || !hasMultiSheetDocument || unsyncedSheets.length === 0) return
    setSyncingAll(true)
    setError('')
    setSyncResult(null)
    setBatchSyncResult(null)
    try {
      const result = await syncAllRecipes(id)
      setBatchSyncResult(result)
      load()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || t('docDetail.errorSaving')
      setError(msg)
    }
    setSyncingAll(false)
  }

  const handleReject = async () => {
    if (!id) return
    setRejectPending(false)
    try { await rejectDocument(id); load() } catch { setError(t('docDetail.errorRejecting')) }
  }

  const openReimport = (mode: ReprocessMode = 'fast') => {
    if (!doc?.id) return
    const recipeSnapshotParam = mode === 'fast' && doc.recipe_snapshot_id
      ? `&recipeSnapshotId=${encodeURIComponent(doc.recipe_snapshot_id)}`
      : ''
    navigate(`../importar?reimport=${mode}${recipeSnapshotParam}`)
  }

  const handleSaveDailyLog = async () => {
    if (!id) return
    setSavingDailyLog(true)
    setError('')
    setDailyLogResult(null)
    try {
      const result = await saveDailyLog(id)
      setDailyLogResult(result)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || t('docDetail.errorSaving')
      setError(msg)
    }
    setSavingDailyLog(false)
  }

  const startEdit = () => {
    const data = (doc?.datos_extraidos || {}) as Record<string, unknown>
    // No editar tablas (tipo inventario/nomina) â€” solo campos escalares
    if (data.filas && Array.isArray(data.filas)) {
      setError('This type of document cannot be edited manually. Use "Re-import" to redo the analysis.')
      return
    }
    const flat: Record<string, string> = {}
    Object.entries(data).forEach(([k, v]) => {
      if (!k.startsWith('_') && k !== 'line_items' && (typeof v !== 'object' || v === null)) flat[k] = String(v ?? '')
    })
    setEditFields(flat)
    setEditLineItems(getEditableLineItems(data, lineItemSlots))
    setEditMode(true)
  }

  const saveEdit = async () => {
    if (!id) return
    setSaving(true)
    try {
      const normalizedLineItems = editLineItems
        .map((item) => {
          const normalized: Record<string, string | undefined> = {}
          for (const s of lineItemSlots) {
            const val = (item[s.slot] ?? '').trim()
            normalized[s.slot] = val || undefined
          }
          return normalized
        })
        .filter((item) => Object.values(item).some(Boolean))
      await editDocumentFields(id, {
        ...editFields,
        line_items: normalizedLineItems,
      })
      setEditMode(false)
      setEditLineItems([])
      load()
    } catch { setError(t('docDetail.errorSaving')) }
    setSaving(false)
  }

  if (loading) return <div style={{ padding: '1.5rem' }}>{t('docDetail.loading')}</div>
  if (!doc) return <div style={{ padding: '1.5rem' }}>{t('docDetail.notFound')}</div>

  const datos = getDocumentData(doc)
  const assistedReview = doc.assisted_review && doc.assisted_review.mode === 'assisted_lines'
    ? doc.assisted_review
    : null
  const isAssistedLines = Boolean(assistedReview)
  const detectedLineItems = Array.isArray(datos.line_items)
    ? datos.line_items.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    : []
  const filasPorHoja = (datos.filas_por_hoja || {}) as Record<string, Record<string, unknown>[]>
  const sheets = Object.keys(filasPorHoja || {})
  const sheetCounts = (datos.filas_por_hoja_count || {}) as Record<string, number>
  const routingDecision = doc.routing_decision || null
  const effectiveConfidence = routingDecision?.confidence ?? doc.confianza_clasificacion
  const confPct = effectiveConfidence != null ? Math.round(effectiveConfidence * 100) : null
  const needsHumanReview = routingDecision?.needs_human_review ?? doc.requiere_revision
  const missingFieldLabels = (routingDecision?.missing_fields || []).map(formatFieldLabel)
  const reviewHints = Array.isArray(doc.review_hints) ? doc.review_hints : []
  const reviewHintMap = reviewHints.reduce<Record<string, typeof reviewHints[number]>>((acc, hint) => {
    if (hint?.field) acc[hint.field] = hint
    return acc
  }, {})
  const syncedSheets = Object.entries(doc.synced_sheets || {}).reduce<Record<string, { recipeId?: string; recipeName?: string; createdAt?: string }>>((acc, [sheetName, value]) => {
    const recipeId = typeof value?.recipe_id === 'string' ? value.recipe_id.trim() : ''
    if (!sheetName || !recipeId) return acc
    acc[sheetName] = {
      recipeId,
      recipeName: typeof value?.recipe_name === 'string' ? value.recipe_name : undefined,
      createdAt: typeof value?.created_at === 'string' ? value.created_at : undefined,
    }
    return acc
  }, {})
  const syncedSheetNames = Object.keys(syncedSheets)
  const syncedCount = syncedSheetNames.length
  const activeSheetSync = activeSheet ? syncedSheets[activeSheet] : undefined
  const activeSheetIsSynced = Boolean(activeSheet && activeSheetSync?.recipeId)
  const hasMultiSheetDocument = sheets.length > 0
  const unsyncedSheets = sheets.filter(sheet => !syncedSheets[sheet]?.recipeId)
  const syncedRecipeId = activeSheetSync?.recipeId || doc.synced_recipe_id
  const isSynced = syncedCount > 0
  const displayStatus = getDocumentDisplayStatus(doc)
  const canResumeSavedInvoice = baseCanResumeSavedInvoice && savedInvoiceHasPendingStock
  const saveEnabled = !isSaved && canSaveDocument(doc) && hasAnySaveModule && doc.estado !== 'FAILED' && routingReadyForSave && (!requiresConfirmedSave || confirmedDataReady)
  const docCategory = getDocCategory(doc, sheets)
  const simpleFlowEnabled = canSaveDocument(doc) && docCategory !== 'recipe' && docCategory !== 'daily_log'
  const advancedActionsVisible = !simpleFlowEnabled
  const canEditScalars = !Array.isArray((doc.datos_extraidos as Record<string, unknown> | undefined)?.filas)
  const isProcessingDocument = doc.estado === 'PENDING' || doc.estado === 'PROCESSING'
  const flowCurrentStep = isSaved
    ? 4
    : isProcessingDocument
      ? 2
    : saveEnabled
        ? 4
        : 3
  const flowTitle = isSaved
    ? 'Step 4. Saved'
    : isProcessingDocument
      ? 'Step 2. Wait'
      : saveEnabled || canResumeSavedInvoice
        ? 'Step 4. Save'
        : 'Step 3. Confirm or reprocess'
  const flowDescription = isSaved
    ? (canResumeSavedInvoice
        ? 'The document is already saved. If stock or products still need completion, you can save it again.'
        : 'The document is already saved.')
    : isProcessingDocument
      ? 'You do not need to do anything now. Wait for the automatic analysis to finish.'
      : isAssistedLines && doc.estado === 'REVIEW'
        ? (assistedReview?.message || 'Fix only what is needed, confirm if it is correct, or reprocess if it is not useful.')
      : saveEnabled || canResumeSavedInvoice
        ? 'If it is correct, save it. If not, reprocess it.'
        : !routingReadyForSave
          ? 'Fix the required data before saving or reprocess if the result is not useful.'
          : 'Confirm if the result is correct. If not, reprocess it.'
  const flowBlockingSummary = missingFieldLabels.length === 1
    ? `1 required field is missing: ${missingFieldLabels[0]}.`
    : missingFieldLabels.length > 1
      ? `${missingFieldLabels.length} required fields are missing: ${missingFieldLabels.join(', ')}.`
      : isAssistedLines
        ? 'Prioritize the detected lines and leave empty the data that does not appear in the document.'
      : 'Fix the required data before the final save.'
  const flowSupportLabel = confPct != null
    ? `Confidence ${confPct}%`
    : 'Provisional result'
  const flowPrimaryAction = canResumeSavedInvoice
    ? {
        label: 'Save',
        onClick: () => setSaveModalOpen(true),
        style: { ...actionBtn, background: '#0f766e' },
      }
    : !isSaved && saveEnabled
      ? {
        label: 'Save',
          onClick: () => setSaveModalOpen(true),
          style: { ...actionBtn, background: '#0f766e' },
        }
      : !isSaved && doc.estado === 'REVIEW' && !saveEnabled && routingReadyForSave
        ? {
            label: saving ? t('docDetail.buttons.confirming') : 'Confirm',
            onClick: handleConfirm,
            style: { ...actionBtn, background: '#10B981' },
            disabled: saving,
          }
        : !isSaved && canEditScalars && (isAssistedLines || !routingReadyForSave)
          ? {
              label: 'Fix',
              onClick: startEdit,
              style: { ...actionBtn, background: '#F59E0B' },
            }
          : null
  const activeSheetRows = (() => {
    if (activeSheet && Array.isArray(filasPorHoja[activeSheet])) {
      return filasPorHoja[activeSheet]
    }
    return Array.isArray(datos.filas) ? (datos.filas as Record<string, unknown>[]) : []
  })()
  const lineItemFieldNames = new Set<string>([
    ...lineItemSlots.map(slot => slot.slot),
    ...canonicalFields
      .filter(field => Boolean(field.line_item_slot))
      .map(field => field.name),
  ])
  const activeNormKeys: string[] = (() => {
    if (
      activeSheet &&
      activeSheet === (datos.sheet_usada as string) &&
      Array.isArray(datos.columnas_norm) &&
      (datos.columnas_norm as string[]).length > 0
    ) {
      return datos.columnas_norm as string[]
    }
    return activeSheetRows.length > 0
      ? Object.keys(activeSheetRows[0]).filter(key => key !== '_sheet')
      : []
  })()
  const activeDisplayNames: string[] = (() => {
    if (
      activeSheet &&
      activeSheet === (datos.sheet_usada as string) &&
      Array.isArray(datos.columnas)
    ) {
      return datos.columnas as string[]
    }
    return activeNormKeys
  })()
  const canSaveProducts = !isSaved
    && activeSheetRows.length > 0
    && canSaveProductsSheet(docCategory, activeSheet, activeNormKeys)
  const activityItems = buildUserActivity(doc?.logs)
  const orderedEditEntries = Object.entries(editFields).sort(([leftKey], [rightKey]) => {
    const leftHint = reviewHintMap[leftKey]
    const rightHint = reviewHintMap[rightKey]
    const leftPriority = leftHint?.priority ?? 999
    const rightPriority = rightHint?.priority ?? 999
    if (leftPriority !== rightPriority) return leftPriority - rightPriority
    return formatFieldLabel(leftKey).localeCompare(formatFieldLabel(rightKey))
  })

  const handleSaved = (_result: SaveDocumentResult) => {
    void load()
  }

  const updateEditLineItem = (index: number, key: string, value: string) => {
    setEditLineItems((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, [key]: value } : item
    )))
  }

  const addEditLineItem = () => {
    setEditLineItems((current) => [...current, createEmptyEditableLineItem(lineItemSlots)])
  }

  const removeEditLineItem = (index: number) => {
    setEditLineItems((current) => current.filter((_, itemIndex) => itemIndex !== index))
  }

  const handleProductsSaved = (result: SaveProductsFromDocumentResult) => {
    setSaveProductsResult(result)
    void load()
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 5, background: '#f9fafb', paddingBottom: '0.75rem' }}>
        <button
          onClick={() => navigate('../documents')}
          style={{
            cursor: 'pointer',
            border: '1px solid #e5e7eb',
            background: '#fff',
            fontSize: 14,
            color: '#111827',
            padding: '0.45rem 0.75rem',
            borderRadius: 10,
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          }}
        >
          {t('docDetail.back')}
        </button>
      </div>
      {error && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem',
          padding: '0.75rem 1rem', borderRadius: 10, border: '1px solid #fecaca',
          background: '#fef2f2', color: '#991b1b', fontSize: 13, marginBottom: '0.75rem',
        }}>
          <span>{error}</span>
          <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'inherit', opacity: 0.6, lineHeight: 1, padding: 0 }} aria-label="Cerrar">Ã—</button>
        </div>
      )}

      {syncResult && (
        <div style={{ padding: '0.75rem', background: syncResult.was_new ? '#F0FDF4' : '#EFF6FF', border: '1px solid ' + (syncResult.was_new ? '#BBF7D0' : '#BFDBFE'), borderRadius: 8, marginBottom: '0.75rem', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            {syncResult.was_new ? 'âœ…' : 'ðŸ”„'} <strong>{syncResult.recipe_name}</strong>
            {' Â· '}{t('docDetail.recipeSynced', { name: '', count: syncResult.ingredients_count, cost: syncResult.total_cost.toFixed(4) })}
          </span>
          <button onClick={() => setSyncResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}>Ã—</button>
        </div>
      )}

      {batchSyncResult && (
        <div style={{ padding: '0.75rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14 }}>
          <div style={{ fontWeight: 600, color: '#1d4ed8', marginBottom: 6 }}>
            {t('docDetail.batchSynced', { processed: batchSyncResult.processed_count, skipped: batchSyncResult.skipped_count })}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {batchSyncResult.results.map(result => (
              <span
                key={result.sheet_name}
                style={{
                  padding: '4px 8px',
                  borderRadius: 999,
                  fontSize: 12,
                  background: result.status === 'skipped' ? '#E5E7EB' : result.status === 'error' ? '#FEE2E2' : '#DBEAFE',
                  color: result.status === 'error' ? '#B91C1C' : '#1F2937',
                }}
              >
                {result.sheet_name}: {result.status === 'skipped' ? t('docDetail.buttons.synced').toLowerCase() : result.status === 'error' ? 'error' : 'ok'}
              </span>
            ))}
          </div>
        </div>
      )}

      {dailyLogResult && (
        <div style={{ padding: '0.75rem', background: '#F5F3FF', border: '1px solid #DDD6FE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <strong style={{ color: '#5b21b6' }}>âœ… {t('docDetail.dailyLogSaved', { date: dailyLogResult.log_date })}</strong>
            <span style={{ marginLeft: 12, color: '#374151' }}>
              {t('docDetail.dailyLogStats', { inserted: dailyLogResult.inserted, matched: dailyLogResult.matched_recipes })}
            </span>
            {dailyLogResult.unmatched_products.length > 0 && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#6b7280' }}>
                {t('docDetail.dailyLogUnmatched', { products: dailyLogResult.unmatched_products.join(', ') })}
              </div>
            )}
          </div>
          <button onClick={() => setDailyLogResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}>Ã—</button>
        </div>
      )}

      {saveProductsResult && (
        <div style={{ padding: '0.75rem', background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <strong style={{ color: '#047857' }}>Saved products</strong>
            <span style={{ marginLeft: 12, color: '#374151' }}>
              {saveProductsResult.created} creados Â· {saveProductsResult.updated ?? 0} actualizados Â· {saveProductsResult.skipped_invalid} omitidos por invÃ¡lidos
            </span>
            {(saveProductsResult.sheet_name || saveProductsResult.category_name) && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#065f46' }}>
                {saveProductsResult.sheet_name ? `Sheet: ${saveProductsResult.sheet_name}` : ''}
                {saveProductsResult.sheet_name && saveProductsResult.category_name ? ' Â· ' : ''}
                {saveProductsResult.category_name ? `Category: ${saveProductsResult.category_name}` : ''}
              </div>
            )}
            {saveProductsResult.skipped_names.length > 0 && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#6b7280' }}>
                Ya existentes: {saveProductsResult.skipped_names.join(', ')}
              </div>
            )}
          </div>
          <button onClick={() => setSaveProductsResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}>x</button>
        </div>
      )}

      {isSynced && !syncResult && !batchSyncResult && (
        <div style={{ padding: '0.6rem 0.9rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 13, color: '#1e40af' }}>
          {t('docDetail.alreadySynced', { count: syncedCount })}
        </div>
      )}

      {isSaved && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0.9rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, marginBottom: '0.75rem', fontSize: 13, color: '#166534' }}>
          <span>
            âœ… {getImportadorSavedAsLabel(inferredSavedAs)}
            {doc.saved_at && <span style={{ marginLeft: 8, opacity: 0.75 }}>Â· {new Date(doc.saved_at).toLocaleString()}</span>}
          </span>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ marginBottom: 4, fontSize: 28, lineHeight: 1.1 }}>{doc.nombre_archivo}</h2>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: 13, color: '#6b7280' }}>
            <span>{doc.tipo_archivo}</span>
            <span>{Math.round(Number(doc.tamanio_bytes ?? 0) / 1024)} KB</span>
            <span>{new Date(doc.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {canSaveProducts && (
            <button onClick={() => setSaveProductsOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>
              Save products
            </button>
          )}

          {/* DAILY LOG */}
          {docCategory === 'daily_log' && (
            <>
              <button onClick={handleSaveDailyLog} disabled={savingDailyLog} style={{ ...actionBtn, background: '#7c3aed' }}>
                {savingDailyLog ? t('docDetail.buttons.savingDailyLog') : dailyLogResult ? t('docDetail.buttons.resaveDailyLog') : t('docDetail.buttons.saveDailyLog')}
              </button>
              <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
            </>
          )}

          {/* RECIPE / COSTEO */}
          {docCategory === 'recipe' && (
            <>
              {isSynced && syncedRecipeId && (
                <button
                  onClick={() => navigate('../../../manufacturing/recetas')}
                  style={{ ...actionBtn, background: '#059669' }}
                >
                  {t('docDetail.buttons.viewRecipe')}
                </button>
              )}
              {hasMultiSheetDocument && unsyncedSheets.length > 0 && (
                <button onClick={handleSyncAll} disabled={syncingAll || syncing} style={{ ...actionBtn, background: '#0f766e' }}>
                  {syncingAll ? t('docDetail.buttons.saving') : t('docDetail.buttons.saveSheets', { count: unsyncedSheets.length })}
                </button>
              )}
              <button onClick={handleSyncSheet} disabled={syncingAll || syncing || activeSheetIsSynced} style={{ ...actionBtn, background: activeSheetIsSynced ? '#94a3b8' : '#2563eb' }}>
                {syncing ? t('docDetail.buttons.saving') : activeSheetIsSynced ? t('docDetail.buttons.synced') : t('docDetail.buttons.saveSheet')}
              </button>
              <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
            </>
          )}

          {/* EXPENSE */}
          {docCategory === 'expense' && (
            <>
              {advancedActionsVisible && saveEnabled && <button onClick={() => setSaveModalOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>{t('docDetail.buttons.saveExpense')}</button>}
              {advancedActionsVisible && doc.estado === 'REVIEW' && (
                <>
                  <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>{t('docDetail.buttons.edit')}</button>
                  <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>
                    {saving ? t('docDetail.buttons.confirming') : t('docDetail.buttons.confirm')}
                  </button>
                  <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
                </>
              )}
            </>
          )}

          {/* SUPPLIER INVOICE */}
          {docCategory === 'supplier_invoice' && (
            <>
              {advancedActionsVisible && saveEnabled && <button onClick={() => setSaveModalOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>{t('docDetail.buttons.saveInvoice')}</button>}
              {advancedActionsVisible && doc.estado === 'REVIEW' && (
                <>
                  <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>{t('docDetail.buttons.edit')}</button>
                  <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>
                    {saving ? t('docDetail.buttons.confirming') : t('docDetail.buttons.confirm')}
                  </button>
                  <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
                </>
              )}
            </>
          )}

          {/* BANK / INVENTORY / PAYROLL / OTHER â€” confirm + reject */}
          {(docCategory === 'bank' || docCategory === 'inventory' || docCategory === 'payroll' || docCategory === 'other') && (
            <>
              {advancedActionsVisible && docCategory === 'other' && saveEnabled && (
                <button onClick={() => setSaveModalOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>
                  {saveDestination === 'supplier_invoice' ? t('docDetail.buttons.saveInvoice') : t('docDetail.buttons.saveExpense')}
                </button>
              )}
              {advancedActionsVisible && doc.estado === 'REVIEW' && (
                <>
                  {!((doc.datos_extraidos as any)?.filas) && (
                    <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>{t('docDetail.buttons.edit')}</button>
                  )}
                  <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>
                    {saving ? t('docDetail.buttons.confirming') : 'Use this result'}
                  </button>
                </>
              )}
              {advancedActionsVisible && <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>}
            </>
          )}
        </div>
      </div>

      {simpleFlowEnabled && (
        <div style={flowCard}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div style={{ minWidth: 260, flex: '1 1 320px' }}>
              <div style={flowEyebrow}>Simple flow</div>
              <h3 style={{ margin: '0.35rem 0 0', fontSize: 22, lineHeight: 1.15 }}>{flowTitle}</h3>
              <p style={{ margin: '0.5rem 0 0', fontSize: 14, color: '#334155' }}>
                {!routingReadyForSave
                  ? flowBlockingSummary
                  : ((saveEnabled || !routingReadyForSave) && routingDecision?.reason ? routingDecision.reason : flowDescription)}
              </p>
              {!isSaved && doc.estado !== 'PENDING' && doc.estado !== 'PROCESSING' && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#64748b', fontWeight: 600 }}>
                  {flowSupportLabel}
                </div>
              )}
              {!isAssistedLines && !routingReadyForSave && reviewHints.length > 0 && (
                <div style={{ marginTop: 12, padding: '0.75rem', borderRadius: 10, border: '1px solid #FDE68A', background: '#FFFBEB' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#92400e', marginBottom: 6 }}>
                    Fix only this to be able to save
                  </div>
                  <div style={{ display: 'grid', gap: 6 }}>
                    {reviewHints.slice(0, 3).map((hint) => (
                      <div key={hint.field} style={{ fontSize: 13, color: '#78350f' }}>
                        <strong>{hint.priority}. {formatFieldLabel(hint.field)}</strong>
                        {hint.confirmed_examples.length > 0 && (
                          <span> · Examples: {hint.confirmed_examples.join(', ')}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div style={{ display: 'grid', gap: 8, justifyItems: 'end' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {flowPrimaryAction && (
                  <button
                    onClick={flowPrimaryAction.onClick}
                    disabled={flowPrimaryAction.disabled}
                    style={flowPrimaryAction.style}
                  >
                    {flowPrimaryAction.label}
                  </button>
                )}
              </div>
            </div>
          </div>
          <div style={flowStepsWrap}>
            {IMPORTADOR_FLOW_STEPS.map((item) => {
              const isActive = item.step === flowCurrentStep
              const isDone = item.step < flowCurrentStep || (isSaved && item.step <= flowCurrentStep)
              return (
                <div
                  key={item.step}
                  style={{
                    ...flowStepChip,
                    borderColor: isActive ? '#2563eb' : isDone ? '#86efac' : '#cbd5e1',
                    background: isActive ? '#dbeafe' : isDone ? '#f0fdf4' : '#fff',
                    color: isActive ? '#1d4ed8' : isDone ? '#166534' : '#475569',
                  }}
                >
                  <span style={flowStepIndex}>{item.step}</span>
                  {item.label}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {isAssistedLines && detectedLineItems.length > 0 && !editMode && (
        <div style={{ ...section, marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
            <div>
              <h3 style={{ margin: 0 }}>Lineas detectadas</h3>
              <div style={{ marginTop: 4, fontSize: 13, color: '#64748B' }}>
                This document is better reviewed by lines than by general fields.
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#0F766E', fontWeight: 700 }}>
              {assistedReview?.line_items_count ?? detectedLineItems.length} suggested lines
            </div>
          </div>
          <LineItemsPreview
            items={detectedLineItems}
            slots={lineItemSlots}
            title="Detalle detectado"
            subtitle={assistedReview?.can_derive_total ? 'The total can be derived from these lines.' : 'Review quantities, prices, and the total before saving.'}
          />
        </div>
      )}

      {/* Confidence warning */}
      {!simpleFlowEnabled && needsHumanReview && confPct != null && confPct < 85 && (
        <div style={{ padding: '0.75rem', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8, marginBottom: '1rem', fontSize: 14 }}>
          Warning: <strong>{t('docDetail.confidenceWarning', { pct: confPct })}</strong>
          {routingDecision?.reason && <span style={{ display: 'block', marginTop: 6, fontWeight: 400 }}>{routingDecision.reason}</span>}
        </div>
      )}

      {/* Status badge */}
      <div style={{ marginBottom: '1rem' }}>
        <span style={{ ...statusBadge, background: statusColor[displayStatus] || '#9CA3AF' }}>{STATUS_LABELS[displayStatus] || displayStatus}</span>
        {isSaved && (
          <span style={{ marginLeft: 8, background: '#dcfce7', padding: '3px 10px', borderRadius: 999, fontSize: 13, color: '#166534', fontWeight: 700 }}>
            Saved
          </span>
        )}
        {doc.tipo_documento_detectado && <span style={{ marginLeft: 8, background: '#e0e7ff', padding: '3px 10px', borderRadius: 999, fontSize: 13, color: '#334155', fontWeight: 700 }}>{doc.tipo_documento_detectado}</span>}
        {confPct != null && <span style={{ marginLeft: 8, fontSize: 13, color: confPct >= 85 ? '#10B981' : '#F59E0B' }}>Confianza: {confPct}%</span>}
      </div>

      {!isProcessingDocument && (
        <ReprocessActions
          onFast={() => openReimport('fast')}
          onDeep={() => openReimport('deep')}
          fastLabel={t('reprocessPage.fastTitle')}
          deepLabel={t('reprocessPage.deepTitle')}
          title="Choose the reprocess level"
          copy="Fast keeps the current flow. Deep ignores OCR and AI caches and starts over to improve extraction."
        />
      )}

      {/* Split view */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Left: Document info */}
        <div style={{ flex: 1, minWidth: 300 }}>
          <div style={section}>
            <h3 style={{ marginTop: 0 }}>{isAssistedLines ? 'Assisted review' : 'Document summary'}</h3>
            {routingDecision && (
              <div style={{ marginBottom: '0.9rem', padding: '0.75rem', borderRadius: 10, border: `1px solid ${routingDecision.required_fields_ok ? '#BBF7D0' : '#FDE68A'}`, background: routingDecision.required_fields_ok ? '#F0FDF4' : '#FFFBEB' }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#334155', background: '#fff', border: '1px solid #cbd5e1', borderRadius: 999, padding: '2px 8px' }}>
                    Tipo interno: {routingDecision.document_type}
                  </span>
                  {routingDecision.suggested_destination && (
                    <span style={{ fontSize: 12, color: '#0f172a' }}>
                      Destino sugerido: <strong>{routingDecision.suggested_destination}</strong>
                    </span>
                  )}
                </div>
                {routingDecision.reason && routingReadyForSave && (
                  <div style={{ fontSize: 13, color: '#334155' }}>{routingDecision.reason}</div>
                )}
                {isAssistedLines && (
                  <div style={{ marginTop: 6, fontSize: 13, color: '#334155' }}>
                    Prioritize products, quantities, and the total. The other fields can stay empty if they do not appear.
                  </div>
                )}
              </div>
            )}
            {!isAssistedLines && reviewHints.length > 0 && (
              <div style={{ marginBottom: '0.9rem', padding: '0.75rem', borderRadius: 10, border: '1px solid #DBEAFE', background: '#EFF6FF' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#1d4ed8', marginBottom: 6 }}>
                  Suggested priority review
                </div>
                <div style={{ display: 'grid', gap: 8 }}>
                  {reviewHints.slice(0, 3).map((hint) => (
                    <div key={hint.field} style={{ fontSize: 13, color: '#334155' }}>
                      <strong>{hint.priority}. {formatFieldLabel(hint.field)}</strong>
                      {hint.is_missing && <span style={{ marginLeft: 6, color: '#b45309' }}>Missing</span>}
                      {hint.confirmed_examples.length > 0 && (
                        <div style={{ marginTop: 2, color: '#475569' }}>
                          Confirmed examples: {hint.confirmed_examples.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {doc.proveedor_detectado && <p><strong>Proveedor:</strong> {doc.proveedor_detectado}</p>}
            {doc.ruc_detectado && <p><strong>RUC:</strong> {doc.ruc_detectado}</p>}
            {doc.monto_total != null && (
              <p>
                <strong>Monto:</strong>{' '}
                {(() => {
                  const currency = [
                    doc.moneda,
                    typeof datos.currency === 'string' ? datos.currency : null,
                    typeof datos.moneda === 'string' ? datos.moneda : null,
                  ].find((value) => typeof value === 'string' && value.trim())
                  return `${currency ? `${String(currency).trim()} ` : ''}${doc.monto_total.toFixed(2)}`
                })()}
              </p>
            )}
            {doc.fecha_documento && <p><strong>Date:</strong> {doc.fecha_documento}</p>}
          </div>
          {doc.error_detalle && (
            <div style={{ ...section, background: '#FEF2F2', border: '1px solid #FECACA' }}>
              <h3 style={{ marginTop: 0, color: '#991B1B' }}>Detected issue</h3>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{doc.error_detalle}</pre>
            </div>
          )}
        </div>

        {/* Right: Extracted fields / Table rows */}
        <div style={{ flex: 1, minWidth: 300 }}>
          <div style={section}>
            {datos.filas && Array.isArray(datos.filas) ? (
              // Vista de tabla para INVENTARIO, NOMINA, COSTEO, etc.
              (() => {
                const allRows = activeSheetRows
                const normKeys = activeNormKeys
                const displayNames = activeDisplayNames
                // Filtrar columnas que no tienen ningÃºn dato real en las primeras 30 filas
                const visibleIdxs = normKeys.reduce<number[]>((acc, key, i) => {
                  const vals = allRows.slice(0, 30).map(r => r[key])
                  if (vals.some(v => v !== null && v !== undefined && v !== '' && v !== 0)) acc.push(i)
                  return acc
                }, [])
                const totalFilasSheet = activeSheet && sheetCounts[activeSheet] ? sheetCounts[activeSheet] : (datos.total_filas as number)
                return (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <h3 style={{ margin: 0 }}>Contenido detectado</h3>
                        {sheets.length > 0 && (
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {sheets.map(s => {
                              const isSheetSynced = Boolean(syncedSheets[s]?.recipeId)
                              return (
                                <button
                                  key={s}
                                  onClick={() => setActiveSheet(s)}
                                  style={{
                                    padding: '6px 10px',
                                    borderRadius: 10,
                                    border: '1px solid ' + (activeSheet === s ? '#0ea5e9' : isSheetSynced ? '#10b981' : '#e5e7eb'),
                                    background: activeSheet === s ? '#e0f2fe' : isSheetSynced ? '#ecfdf5' : '#fff',
                                    color: '#0f172a',
                                    fontSize: 12,
                                    cursor: 'pointer',
                                  }}
                                >
                                  {s} <span style={{ color: '#64748b' }}>({sheetCounts[s] ?? '-'})</span>
                                  {isSheetSynced && <span style={{ marginLeft: 6, color: '#047857', fontWeight: 600 }}>Guardada</span>}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{totalFilasSheet} filas Â· {visibleIdxs.length} columnas visibles</span>
                    </div>
                    <div style={{ overflowX: 'auto', maxHeight: 460, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 10 }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                        <thead>
                          <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb', position: 'sticky', top: 0 }}>
                            {visibleIdxs.map(i => (
                              <th key={i} style={{ padding: '0.4rem 0.5rem', textAlign: 'left', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap', background: '#f9fafb' }}>
                                {displayNames[i] ?? normKeys[i]}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {allRows.slice(0, 150).map((row, ri) => (
                            <tr key={ri} style={{ borderBottom: '1px solid #f3f4f6' }}
                              onMouseEnter={e => (e.currentTarget.style.background = '#f9fafb')}
                              onMouseLeave={e => (e.currentTarget.style.background = '')}
                            >
                              {visibleIdxs.map(i => {
                                const val = row[normKeys[i]]
                                const isNum = typeof val === 'number'
                                return (
                                  <td key={i} style={{ padding: '0.3rem 0.5rem', whiteSpace: 'nowrap', textAlign: isNum ? 'right' : 'left' }}>
                                    {val == null || val === '' ? '' : isNum ? (val as number).toLocaleString('es-ES', { maximumFractionDigits: 4 }) : String(val)}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {totalFilasSheet > 150 && (
                      <p style={{ fontSize: 12, color: '#9ca3af', marginTop: '0.5rem', textAlign: 'center' }}>
                        Mostrando 150 de {totalFilasSheet} filas
                      </p>
                    )}
                    {datos.metadata && typeof datos.metadata === 'object' && (!activeSheet || activeSheet === (datos.sheet_usada as string)) && (
                      <div style={{ marginTop: '0.75rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '0.75rem', fontSize: 13 }}>
                        <strong style={{ color: '#0f172a' }}>Additional information</strong>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: '6px 12px', marginTop: 8 }}>
                          {Object.entries(datos.metadata as Record<string, unknown>).map(([k, v]) => (
                            <div key={k} style={{ color: '#475569' }}><span style={{ fontWeight: 600 }}>{k}:</span> {String(v ?? 'â€”')}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )
              })()
            ) : (
              // Vista de campos para FACTURA, RECIBO, etc.
              <>
                <h3 style={{ marginTop: 0 }}>{isAssistedLines ? 'Optional document data' : 'Document data'}</h3>
                {editMode ? (
                  <div>
                    {!isAssistedLines && reviewHints.length > 0 && (
                      <div style={{ marginBottom: '0.75rem', padding: '0.75rem', borderRadius: 10, border: '1px solid #DBEAFE', background: '#EFF6FF', fontSize: 13, color: '#334155' }}>
                        Edita primero los campos prioritarios sugeridos por documentos similares confirmados.
                      </div>
                    )}
                    {isAssistedLines && (
                      <div style={{ marginBottom: '0.75rem', padding: '0.75rem', borderRadius: 10, border: '1px solid #DBEAFE', background: '#EFF6FF', fontSize: 13, color: '#334155' }}>
                        Fix the lines and the total first. The upper fields are optional if they do not appear in the image.
                      </div>
                    )}
                    {orderedEditEntries.map(([key, val]) => {
                      const hint = reviewHintMap[key]
                      const inputType = getReviewInputType(hint?.field_type)
                      return (
                      <label key={key} style={{ display: 'flex', flexDirection: 'column', marginBottom: '0.5rem', fontSize: 13 }}>
                        <span style={{ color: '#6b7280', fontWeight: 600 }}>
                          {formatFieldLabel(key)}
                          {hint?.priority ? <span style={{ marginLeft: 6, color: '#2563eb' }}>Prioridad {hint.priority}</span> : null}
                        </span>
                        <input
                          type={inputType}
                          step={inputType === 'number' ? '0.01' : undefined}
                          value={val}
                          onChange={e => setEditFields(f => ({ ...f, [key]: e.target.value }))}
                          style={{ padding: '0.4rem', border: '1px solid #d1d5db', borderRadius: 6 }}
                        />
                        {hint?.reason && (
                          <span style={{ marginTop: 4, color: '#64748b', fontSize: 12 }}>{hint.reason}</span>
                        )}
                        {hint?.confirmed_examples?.length ? (
                          <span style={{ marginTop: 2, color: '#64748b', fontSize: 12 }}>
                            Examples: {hint.confirmed_examples.join(', ')}
                          </span>
                        ) : null}
                      </label>
                      )
                    })}
                    <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <div>
                          <div style={{ color: '#111827', fontWeight: 600, fontSize: 14 }}>Line details</div>
                          <div style={{ color: '#6b7280', fontSize: 12 }}>Add or fix the detected products.</div>
                        </div>
                        <button onClick={addEditLineItem} type="button" style={{ ...actionBtn, background: '#e5e7eb', color: '#374151' }}>
                          Add line
                        </button>
                      </div>
                      {editLineItems.length === 0 ? (
                        <div style={{ padding: '0.75rem', border: '1px dashed #d1d5db', borderRadius: 8, color: '#6b7280', fontSize: 13 }}>
                          There are no loaded lines. You can add them manually.
                        </div>
                      ) : (
                        <div style={{ display: 'grid', gap: '0.75rem' }}>
                          {editLineItems.map((item, index) => (
                            <div key={`line-${index}`} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: '0.75rem', background: '#f9fafb' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                <strong style={{ fontSize: 13, color: '#111827' }}>Linea {index + 1}</strong>
                                <button onClick={() => removeEditLineItem(index)} type="button" style={{ background: 'none', border: 'none', color: '#b91c1c', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                                  Remove
                                </button>
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: `repeat(${lineItemSlots.length}, minmax(110px,1fr))`, gap: '0.5rem' }}>
                                {lineItemSlots.map(s => (
                                  <label key={s.slot} style={{ display: 'flex', flexDirection: 'column', fontSize: 13 }}>
                                    <span style={{ color: '#6b7280', fontWeight: 600 }}>{s.label}</span>
                                    <input
                                      type={_NUMERIC_SLOTS.has(s.slot) ? 'number' : 'text'}
                                      step={_NUMERIC_SLOTS.has(s.slot) ? '0.01' : undefined}
                                      value={item[s.slot] ?? ''}
                                      onChange={(e) => updateEditLineItem(index, s.slot, e.target.value)}
                                      style={{ padding: '0.4rem', border: '1px solid #d1d5db', borderRadius: 6, fontFamily: _MONO_SLOTS.has(s.slot) ? 'monospace' : undefined }}
                                    />
                                  </label>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                      <button onClick={saveEdit} disabled={saving} style={{ ...actionBtn, background: '#6366F1' }}>{t('docDetail.buttons.saveEdit')}</button>
                      <button onClick={() => { setEditMode(false); setEditLineItems([]) }} style={{ ...actionBtn, background: '#e5e7eb', color: '#374151' }}>{t('docDetail.buttons.cancelEdit')}</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <tbody>
                        {Object.entries(datos).filter(([k, v]) => !k.startsWith('_') && !lineItemFieldNames.has(k) && (typeof v !== 'object' || v === null)).map(([key, val]) => (
                          <tr key={key} style={{ borderBottom: '1px solid #f3f4f6' }}>
                            <td style={{ padding: '0.4rem 0.5rem', fontSize: 13, color: '#6b7280', fontWeight: 600 }}>{formatFieldLabel(key)}</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontSize: 14 }}>{String(val ?? 'â€”')}</td>
                          </tr>
                        ))}
                        {Object.keys(datos).filter(k => !k.startsWith('_') && !lineItemFieldNames.has(k) && (typeof datos[k] !== 'object' || datos[k] === null)).length === 0 && (
                          <tr><td colSpan={2} style={{ padding: '1rem', textAlign: 'center', color: '#9ca3af' }}>
                            {doc.error_detalle
                              ? 'Could not extract data. Use "Re-import" to try again.'
                              : 'â€”'}
                          </td></tr>
                        )}
                      </tbody>
                    </table>
                    {(() => {
                      if (isAssistedLines) return null
                      const pageGroups = normalizeLineItemPageGroups(datos as Record<string, unknown>)
                      if (pageGroups.length === 0) return null
                      const hasExplicitGroups = Array.isArray((datos as Record<string, unknown>).line_item_page_groups)
                      if (!hasExplicitGroups && pageGroups.length === 1) {
                        const items = pageGroups[0].line_items
                        return (
                          <LineItemsPreview
                            items={items}
                            slots={lineItemSlots}
                            title={`Detalle (${items.length})`}
                          />
                        )
                      }
                      return (
                        <div style={{ display: 'grid', gap: '0.75rem' }}>
                          {pageGroups.map((group) => (
                            <GroupedLineItemsPreview
                              key={`page-${group.source_page}`}
                              group={group}
                            />
                          ))}
                        </div>
                      )
                    })()}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {activityItems.length > 0 && (
        <div style={{ ...section, marginTop: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>Recent activity</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {activityItems.map((item) => (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 12,
                  padding: '0.75rem 0.9rem',
                  border: '1px solid #E5E7EB',
                  borderRadius: 10,
                  background: '#F9FAFB',
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{item.title}</div>
                  {item.note && <div style={{ marginTop: 4, fontSize: 12, color: '#6B7280' }}>{item.note}</div>}
                </div>
                <div style={{ fontSize: 12, color: '#6B7280', whiteSpace: 'nowrap' }}>{item.when}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {doc.version_links && doc.version_links.length > 0 && (
        <div style={{ ...section, marginTop: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>Related versions</h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {doc.version_links.map(link => (
              <button
                key={`${link.relation_direction}-${link.id}`}
                onClick={() => navigate(`../documents/${link.id}`)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 12,
                  padding: '0.65rem 0.8rem',
                  border: '1px solid #E5E7EB',
                  borderRadius: 8,
                  background: '#F9FAFB',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                    <strong>{link.relation_direction === 'predecessor' ? 'Previous' : 'Next'}</strong>
                    <span style={{ color: '#6B7280' }}>{link.estado}</span>
                    {link.relation_reason && <span style={{ color: '#6B7280' }}>{link.relation_reason}</span>}
                  </div>
                  <div style={{ color: '#111827' }}>{link.nombre_archivo}</div>
                  <div style={{ fontSize: 12, color: '#6B7280' }}>
                    {new Date(link.created_at).toLocaleString()}
                    {link.hash_sha256 ? ` Â· ${link.hash_sha256.slice(0, 12)}...` : ''}
                  </div>
                </div>
                <span style={{ color: '#2563EB', fontWeight: 600 }}>Open</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <Suspense fallback={null}>
        <ReprocessPanel documentId={id ?? ''} activeSheet={activeSheet} lastRefresh={lastRefresh} />
      </Suspense>


      {saveModalOpen && (
        <Suspense fallback={null}>
          <SaveDocumentModal
            doc={doc}
            open={saveModalOpen}
            resumeMode={canResumeSavedInvoice}
            onClose={() => setSaveModalOpen(false)}
            onSaved={handleSaved}
          />
        </Suspense>
      )}
      {saveProductsOpen && (
        <Suspense fallback={null}>
          <SaveProductsModal
            doc={doc}
            open={saveProductsOpen}
            onClose={() => setSaveProductsOpen(false)}
            onSaved={handleProductsSaved}
            sheetName={activeSheet}
            rows={activeSheetRows}
            columnKeys={activeNormKeys}
            columnLabels={activeDisplayNames}
          />
        </Suspense>
      )}
      {rejectPending && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">{t('docDetail.buttons.reject')}</h3>
            <p className="text-sm text-slate-600 mb-4">{t('docDetail.confirmReject')}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setRejectPending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancelar</button>
              <button onClick={handleReject} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">{t('docDetail.buttons.reject')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const section: React.CSSProperties = { border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#fff' }
const actionBtn: React.CSSProperties = { padding: '0.5rem 1rem', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 600 }
const flowCard: React.CSSProperties = { marginBottom: '1rem', border: '1px solid #bfdbfe', borderRadius: 14, padding: '1rem 1.1rem', background: 'linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%)' }
const flowEyebrow: React.CSSProperties = { fontSize: 11, fontWeight: 800, color: '#1d4ed8', textTransform: 'uppercase', letterSpacing: '0.06em' }
const flowStepsWrap: React.CSSProperties = { display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: '0.9rem' }
const flowStepChip: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 8, padding: '0.45rem 0.75rem', border: '1px solid #cbd5e1', borderRadius: 999, fontSize: 13, fontWeight: 700 }
const flowStepIndex: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 22, height: 22, borderRadius: 999, background: '#fff', fontSize: 12, color: '#0f172a' }
const statusBadge: React.CSSProperties = { color: '#fff', padding: '3px 12px', borderRadius: 12, fontSize: 13, fontWeight: 600 }
const statusColor: Record<string, string> = { CONFIRMED: '#10B981', REVIEW: '#3B82F6', PROCESSING: '#F59E0B', PENDING: '#9CA3AF', FAILED: '#EF4444', INVALID: '#EF4444', REPROCESS: '#8B5CF6', VALID: '#10B981', IMPORTED: '#0EA5E9' }
const reprocessCard: React.CSSProperties = {
  marginBottom: '1rem',
  border: '1px solid #bfdbfe',
  borderRadius: 14,
  padding: '0.95rem 1rem',
  background: 'linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%)',
}
const reprocessHeaderLayout: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  alignItems: 'flex-start',
  flexWrap: 'wrap',
}
const reprocessEyebrow: React.CSSProperties = { fontSize: 11, fontWeight: 800, color: '#1d4ed8', textTransform: 'uppercase', letterSpacing: '0.06em' }
const reprocessTitle: React.CSSProperties = { marginTop: 4, fontSize: 16, lineHeight: 1.2, fontWeight: 800, color: '#0f172a' }
const reprocessCopy: React.CSSProperties = { marginTop: 6, fontSize: 13, color: '#475569', maxWidth: 620 }
const reprocessButtonRow: React.CSSProperties = { display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }
const reprocessFastButton: React.CSSProperties = {
  padding: '0.5rem 0.95rem',
  borderRadius: 10,
  border: '1px solid #0f766e',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 700,
  background: '#0f766e',
  color: '#fff',
  boxShadow: '0 1px 0 rgba(15, 118, 110, 0.08)',
}
const reprocessDeepButton: React.CSSProperties = {
  padding: '0.5rem 0.95rem',
  borderRadius: 10,
  border: '1px solid #bfdbfe',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 700,
  background: '#fff',
  color: '#1d4ed8',
}
