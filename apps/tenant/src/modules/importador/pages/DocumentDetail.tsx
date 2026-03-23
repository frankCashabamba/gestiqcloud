import React, { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useImportReprocess } from '../hooks/useImportReprocess'
import SaveDocumentModal from '../components/SaveDocumentModal'
import SaveProductsModal from '../components/SaveProductsModal'
import { canSaveDocument, canSaveProductsSheet, fetchDocument, fetchSaveCapabilities, confirmDocument, editDocumentFields, rejectDocument, suggestSaveDestination, syncAllRecipes, syncRecipe, saveDailyLog, getDocCategory, getDocumentData, hasConfirmedDocumentData, type Documento, type LogCambio, type SaveDocumentResult, type SaveDailyLogResult, type SaveProductsFromDocumentResult, type StagingLine, type SyncRecipeResult, type SyncRecipesResult } from '../services'

const REPROCESSABLE_STATES = ['INVALID', 'PENDING', 'REVIEW', 'REPROCESS', 'VALID'] as const

const FIELD_LABELS: Record<string, string> = {
  vendor: 'Proveedor',
  vendor_tax_id: 'RUC proveedor',
  customer: 'Cliente',
  customer_tax_id: 'Documento cliente',
  category: 'Categoria',
  concept: 'Concepto',
  currency: 'Moneda',
  subtotal: 'Subtotal',
  tax_amount: 'Impuesto',
  total_amount: 'Total',
  payment_terms: 'Importe reportado',
  payment_method: 'Forma de pago',
  issue_date: 'Fecha de emision',
  due_date: 'Fecha de vencimiento',
  doc_number: 'Numero de documento',
  invoice_number: 'Numero de factura',
  reference: 'Referencia',
  description: 'Descripcion',
  product: 'Producto',
  quantity: 'Cantidad',
  qty: 'Cantidad',
  unit_price: 'Precio unitario',
  line_total: 'Total de linea',
}

const STATUS_LABELS: Record<string, string> = {
  REVIEW: 'Por revisar',
  CONFIRMED: 'Confirmado',
  FAILED: 'Con error',
  PROCESSING: 'Procesando',
  PENDING: 'En cola',
  INVALID: 'Con error',
  REPROCESS: 'Pendiente de nueva revision',
  VALID: 'Valido',
  IMPORTED: 'Guardado',
}

function toggleStringValue(values: string[], value: string, checked: boolean): string[] {
  if (!value) return values
  return checked
    ? (values.includes(value) ? values : [...values, value])
    : values.filter(item => item !== value)
}

function toggleNumberValue(values: number[], value: number, checked: boolean): number[] {
  return checked
    ? (values.includes(value) ? values : [...values, value])
    : values.filter(item => item !== value)
}

function getObjectKeys(value: unknown): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.keys(value as Record<string, unknown>).filter(Boolean)
}

function getStagingLineColumns(line: StagingLine): string[] {
  return Array.from(new Set([
    ...getObjectKeys(line.raw_data),
    ...getObjectKeys(line.normalized_data),
  ])).sort((a, b) => a.localeCompare(b))
}

function formatSelection(values: Array<string | number>, emptyLabel: string): string {
  if (!values.length) return emptyLabel
  const items = values.map(value => String(value))
  if (items.length <= 4) return items.join(', ')
  return `${items.slice(0, 4).join(', ')} +${items.length - 4}`
}

function formatFieldLabel(key: string): string {
  if (!key) return ''
  if (FIELD_LABELS[key]) return FIELD_LABELS[key]
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

type ActivityItem = {
  id: string
  title: string
  when: string
  note?: string
}

function summarizeLogDetail(action: string, detail: Record<string, unknown> | null | undefined): string | undefined {
  if (!detail || typeof detail !== 'object') return undefined
  if (action === 'UPLOAD') {
    const filename = typeof detail.filename === 'string' ? detail.filename : null
    return filename ? `Archivo: ${filename}` : undefined
  }
  if (action === 'REPROCESS') {
    const mode = typeof detail.mode === 'string' ? detail.mode : null
    return mode === 'async' || mode === 'in_place' ? 'Se volvió a procesar el documento.' : undefined
  }
  if (action === 'EDIT') {
    const fields = Array.isArray(detail.changed_fields) ? detail.changed_fields.map(String).filter(Boolean) : []
    return fields.length ? `Campos actualizados: ${fields.join(', ')}` : 'Se actualizaron los datos del documento.'
  }
  if (action === 'SAVE_DESTINATION') {
    const target = typeof detail.target === 'string' ? detail.target : null
    const status = typeof detail.status === 'string' ? detail.status : null
    if (target && status === 'created') return `Se guardó en ${target}.`
    if (target) return `Destino: ${target}.`
  }
  return undefined
}

function buildUserActivity(logs: LogCambio[] | undefined): ActivityItem[] {
  if (!logs?.length) return []
  const visibleActions: Record<string, string> = {
    UPLOAD: 'Documento subido',
    EDIT: 'Datos editados',
    CONFIRM: 'Documento confirmado',
    REJECT: 'Documento rechazado',
    REPROCESS: 'Reprocesado solicitado',
    SAVE_DESTINATION: 'Documento guardado',
  }

  return logs
    .filter((log) => Boolean(visibleActions[log.accion]))
    .map((log) => ({
      id: log.id,
      title: visibleActions[log.accion],
      when: new Date(log.created_at).toLocaleString(),
      note: summarizeLogDetail(log.accion, log.detalle as Record<string, unknown> | null | undefined),
    }))
}

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation('importer')
  const [doc, setDoc] = useState<Documento | null>(null)
  const [loading, setLoading] = useState(true)
  const [editMode, setEditMode] = useState(false)
  const [editFields, setEditFields] = useState<Record<string, string>>({})
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
  const reprocess = useImportReprocess(id ?? '')
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [selectedErrorCodes, setSelectedErrorCodes] = useState<string[]>([])
  const [selectedLineNumbers, setSelectedLineNumbers] = useState<number[]>([])
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const lastVisibilityReloadRef = useRef(0)

  useEffect(() => {
    fetchSaveCapabilities().then(setCapabilities).catch(() => {
      setError(t('docDetail.errorLoading'))
    })
  }, [])
  useEffect(() => { if (id) void reprocess.loadIterations() }, [id])

  const load = async () => {
    if (!id) return
    setLoading(true)
    try { setDoc(await fetchDocument(id)) } catch { setError(t('docDetail.errorLoading')) }
    setLoading(false)
    void reprocess.refreshSummary()
  }

  useEffect(() => { load() }, [id])

  useEffect(() => {
    const reloadOnVisibility = () => {
      if (document.hidden) return
      const now = Date.now()
      if (now - lastVisibilityReloadRef.current < 15000) return
      lastVisibilityReloadRef.current = now
      void load()
    }
    document.addEventListener('visibilitychange', reloadOnVisibility)
    return () => {
      document.removeEventListener('visibilitychange', reloadOnVisibility)
    }
  }, [id])

  // Selección automática de hoja cuando llega un documento nuevo
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

  useEffect(() => {
    setSelectedFields([])
    setSelectedErrorCodes([])
    setSelectedLineNumbers([])
    setSelectedColumns([])
  }, [doc?.id])

  const resetSelectiveFilters = () => {
    setSelectedFields([])
    setSelectedErrorCodes([])
    setSelectedLineNumbers([])
    setSelectedColumns([])
  }

  const handleInspectReprocess = async () => {
    await Promise.all([
      reprocess.inspectFields([...REPROCESSABLE_STATES], [], activeSheet || undefined),
      reprocess.loadLines({
        estado: [...REPROCESSABLE_STATES],
        sheet: activeSheet || undefined,
        limit: 200,
      }),
    ])
  }

  const handleConfirm = async () => {
    if (!id || !doc) return
    setSaving(true)
    try {
      await confirmDocument(id, doc.datos_extraidos || {})
      load()
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
    // No editar tablas (tipo inventario/nomina) — solo campos escalares
    if (data.filas && Array.isArray(data.filas)) {
      setError('Este tipo de documento no se puede editar manualmente. Usa "Volver a procesar" para corregir los datos.')
      return
    }
    const flat: Record<string, string> = {}
    Object.entries(data).forEach(([k, v]) => {
      if (!k.startsWith('_') && (typeof v !== 'object' || v === null)) flat[k] = String(v ?? '')
    })
    setEditFields(flat)
    setEditMode(true)
  }

  const saveEdit = async () => {
    if (!id) return
    setSaving(true)
    try {
      await editDocumentFields(id, editFields)
      setEditMode(false)
      load()
    } catch { setError(t('docDetail.errorSaving')) }
    setSaving(false)
  }

  if (loading) return <div style={{ padding: '1.5rem' }}>{t('docDetail.loading')}</div>
  if (!doc) return <div style={{ padding: '1.5rem' }}>{t('docDetail.notFound')}</div>

  const datos = getDocumentData(doc)
  const filasPorHoja = (datos.filas_por_hoja || {}) as Record<string, Record<string, unknown>[]>
  const sheets = Object.keys(filasPorHoja || {})
  const sheetCounts = (datos.filas_por_hoja_count || {}) as Record<string, number>
  const confPct = doc.confianza_clasificacion != null ? Math.round(doc.confianza_clasificacion * 100) : null
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
  const savedAsLog = (doc.logs ?? []).find(l => l.accion === 'SAVE_DESTINATION' || l.accion === 'SAVE_PRODUCTS')
  const _logDest = savedAsLog?.detalle?.['destination'] as string | undefined
  const inferredSavedAs: string | undefined = doc.saved_as
    ?? (savedAsLog?.accion === 'SAVE_PRODUCTS' ? 'products'
      : _logDest === 'supplier_invoice' ? 'supplier_invoice'
      : _logDest === 'expense' ? 'expense'
      : savedAsLog ? 'supplier_invoice'
      : undefined)
  const isSaved = doc.estado === 'IMPORTED' || doc.saved_as != null || savedAsLog != null
  const hasAnySaveModule = Boolean(capabilities.purchases || capabilities.invoicing || capabilities.expenses)
  const saveDestination = suggestSaveDestination(doc)
  const requiresConfirmedSave = saveDestination !== 'recipe'
  const saveEnabled = !isSaved && canSaveDocument(doc) && hasAnySaveModule && doc.estado !== 'FAILED' && (!requiresConfirmedSave || hasConfirmedDocumentData(doc))
  const docCategory = getDocCategory(doc, sheets)
  const activeSheetRows = (() => {
    if (activeSheet && Array.isArray(filasPorHoja[activeSheet])) {
      return filasPorHoja[activeSheet]
    }
    return Array.isArray(datos.filas) ? (datos.filas as Record<string, unknown>[]) : []
  })()
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
  const reprocessableLines = reprocess.lines.filter(line => REPROCESSABLE_STATES.includes(line.estado as (typeof REPROCESSABLE_STATES)[number]))
  const availableErrorCodes = Array.from(new Set([
    ...Object.keys(reprocess.fieldAnalysis?.error_summary || {}),
    ...reprocessableLines
      .map(line => line.error_code)
      .filter((code): code is string => Boolean(code)),
  ])).sort((a, b) => a.localeCompare(b))
  const isDocumentScopedReprocess = reprocessableLines.length > 0
    && reprocessableLines.every(line => (line.sheet_name || '__document__') === '__document__')
  const availableColumns = isDocumentScopedReprocess
    ? []
    : Array.from(new Set(
        reprocessableLines.flatMap(line => getStagingLineColumns(line))
      )).sort((a, b) => a.localeCompare(b))
  const hasSelectiveFilters = selectedFields.length > 0
    || selectedErrorCodes.length > 0
    || selectedLineNumbers.length > 0
    || selectedColumns.length > 0
  const effectiveSelectedFields = Array.from(new Set([
    ...selectedFields,
    ...(isDocumentScopedReprocess ? selectedColumns : []),
  ])).sort((a, b) => a.localeCompare(b))
  const reviewSessionLabel = [
    `Datos: ${formatSelection(effectiveSelectedFields, 'todos')}`,
    `Columnas: ${formatSelection(selectedColumns, 'todas')}`,
    `Problemas: ${formatSelection(selectedErrorCodes, 'todos')}`,
    `Elementos: ${formatSelection(selectedLineNumbers, 'todos')}`,
  ].join(' · ')
  const activityItems = buildUserActivity(doc?.logs)

  const handleSaved = (_result: SaveDocumentResult) => {
    void load()
  }

  const handleProductsSaved = (result: SaveProductsFromDocumentResult) => {
    setSaveProductsResult(result)
    void load()
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 5, background: '#f9fafb', paddingBottom: '0.75rem' }}>
        <button
          onClick={() => navigate(-1)}
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
          <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'inherit', opacity: 0.6, lineHeight: 1, padding: 0 }} aria-label="Cerrar">×</button>
        </div>
      )}

      {syncResult && (
        <div style={{ padding: '0.75rem', background: syncResult.was_new ? '#F0FDF4' : '#EFF6FF', border: '1px solid ' + (syncResult.was_new ? '#BBF7D0' : '#BFDBFE'), borderRadius: 8, marginBottom: '0.75rem', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            {syncResult.was_new ? '✅' : '🔄'} <strong>{syncResult.recipe_name}</strong>
            {' · '}{t('docDetail.recipeSynced', { name: '', count: syncResult.ingredients_count, cost: syncResult.total_cost.toFixed(4) })}
          </span>
          <button onClick={() => setSyncResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}>×</button>
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
            <strong style={{ color: '#5b21b6' }}>✅ {t('docDetail.dailyLogSaved', { date: dailyLogResult.log_date })}</strong>
            <span style={{ marginLeft: 12, color: '#374151' }}>
              {t('docDetail.dailyLogStats', { inserted: dailyLogResult.inserted, matched: dailyLogResult.matched_recipes })}
            </span>
            {dailyLogResult.unmatched_products.length > 0 && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#6b7280' }}>
                {t('docDetail.dailyLogUnmatched', { products: dailyLogResult.unmatched_products.join(', ') })}
              </div>
            )}
          </div>
          <button onClick={() => setDailyLogResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#6b7280' }}>×</button>
        </div>
      )}

      {saveProductsResult && (
        <div style={{ padding: '0.75rem', background: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <strong style={{ color: '#047857' }}>Productos guardados</strong>
            <span style={{ marginLeft: 12, color: '#374151' }}>
              {saveProductsResult.created} creados · {saveProductsResult.updated ?? 0} actualizados · {saveProductsResult.skipped_invalid} omitidos por inválidos
            </span>
            {(saveProductsResult.sheet_name || saveProductsResult.category_name) && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#065f46' }}>
                {saveProductsResult.sheet_name ? `Hoja: ${saveProductsResult.sheet_name}` : ''}
                {saveProductsResult.sheet_name && saveProductsResult.category_name ? ' · ' : ''}
                {saveProductsResult.category_name ? `Categoria: ${saveProductsResult.category_name}` : ''}
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
            ✅ {inferredSavedAs === 'products' ? 'Productos guardados' : inferredSavedAs === 'supplier_invoice' ? 'Guardado como factura de compra' : inferredSavedAs === 'expense' ? 'Guardado como gasto' : 'Documento guardado'}
            {doc.saved_at && <span style={{ marginLeft: 8, opacity: 0.75 }}>· {new Date(doc.saved_at).toLocaleString()}</span>}
          </span>
          <button
            onClick={() => navigate(`../upload?reimport=clean&documentId=${doc.id}`)}
            style={{ background: 'none', border: '1px solid #86efac', borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#166534', padding: '2px 8px' }}
          >
            Volver a procesar
          </button>
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
              Guardar productos
            </button>
          )}

          {/* DAILY LOG */}
          {docCategory === 'daily_log' && (
            <>
              <button onClick={handleSaveDailyLog} disabled={savingDailyLog} style={{ ...actionBtn, background: '#7c3aed' }}>
                {savingDailyLog ? t('docDetail.buttons.savingDailyLog') : dailyLogResult ? t('docDetail.buttons.resaveDailyLog') : t('docDetail.buttons.saveDailyLog')}
              </button>
              <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
              <button onClick={() => navigate(`../upload?reimport=clean&documentId=${doc.id}`)} style={{ ...actionBtn, background: '#6b7280' }}>{t('docDetail.buttons.reimport')}</button>
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
              <button onClick={() => navigate(`../upload?reimport=clean&documentId=${doc.id}`)} style={{ ...actionBtn, background: '#6b7280', opacity: 0.85 }}>{t('docDetail.buttons.reimport')}</button>
            </>
          )}

          {/* EXPENSE */}
          {docCategory === 'expense' && (
            <>
              {saveEnabled && <button onClick={() => setSaveModalOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>{t('docDetail.buttons.saveExpense')}</button>}
              {doc.estado === 'REVIEW' && (
                <>
                  <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>{t('docDetail.buttons.edit')}</button>
                  <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>
                    {saving ? t('docDetail.buttons.confirming') : t('docDetail.buttons.confirm')}
                  </button>
                  <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
                </>
              )}
              <button onClick={() => navigate(`../upload?reimport=clean&documentId=${doc.id}`)} style={{ ...actionBtn, background: '#6b7280', opacity: 0.85 }}>{t('docDetail.buttons.reimport')}</button>
            </>
          )}

          {/* SUPPLIER INVOICE */}
          {docCategory === 'supplier_invoice' && (
            <>
              {saveEnabled && <button onClick={() => setSaveModalOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>{t('docDetail.buttons.saveInvoice')}</button>}
              {doc.estado === 'REVIEW' && (
                <>
                  <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>{t('docDetail.buttons.edit')}</button>
                  <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>
                    {saving ? t('docDetail.buttons.confirming') : t('docDetail.buttons.confirm')}
                  </button>
                  <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
                </>
              )}
              <button onClick={() => navigate(`../upload?reimport=clean&documentId=${doc.id}`)} style={{ ...actionBtn, background: '#6b7280', opacity: 0.85 }}>{t('docDetail.buttons.reimport')}</button>
            </>
          )}

          {/* BANK / INVENTORY / PAYROLL / OTHER — confirm + reject */}
          {(docCategory === 'bank' || docCategory === 'inventory' || docCategory === 'payroll' || docCategory === 'other') && (
            <>
              {docCategory === 'other' && saveEnabled && (
                <button onClick={() => setSaveModalOpen(true)} style={{ ...actionBtn, background: '#0f766e' }}>
                  {saveDestination === 'supplier_invoice' ? t('docDetail.buttons.saveInvoice') : t('docDetail.buttons.saveExpense')}
                </button>
              )}
              {doc.estado === 'REVIEW' && (
                <>
                  {!((doc.datos_extraidos as any)?.filas) && (
                    <button onClick={startEdit} style={{ ...actionBtn, background: '#F59E0B' }}>{t('docDetail.buttons.edit')}</button>
                  )}
                  <button onClick={handleConfirm} disabled={saving} style={{ ...actionBtn, background: '#10B981' }}>
                    {saving ? t('docDetail.buttons.confirming') : t('docDetail.buttons.confirm')}
                  </button>
                </>
              )}
              <button onClick={() => setRejectPending(true)} style={{ ...actionBtn, background: '#EF4444' }}>{t('docDetail.buttons.reject')}</button>
              <button onClick={() => navigate(`../upload?reimport=clean&documentId=${doc.id}`)} style={{ ...actionBtn, background: '#6b7280', opacity: 0.85 }}>{t('docDetail.buttons.reimport')}</button>
            </>
          )}
        </div>
      </div>

      {/* Confidence warning */}
      {doc.requiere_revision && confPct != null && confPct < 85 && (
        <div style={{ padding: '0.75rem', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8, marginBottom: '1rem', fontSize: 14 }}>
          ⚠️ <strong>{t('docDetail.confidenceWarning', { pct: confPct })}</strong>
        </div>
      )}

      {/* Status badge */}
      <div style={{ marginBottom: '1rem' }}>
        <span style={{ ...statusBadge, background: statusColor[doc.estado] || '#9CA3AF' }}>{STATUS_LABELS[doc.estado] || doc.estado}</span>
        {doc.tipo_documento_detectado && <span style={{ marginLeft: 8, background: '#e0e7ff', padding: '3px 10px', borderRadius: 999, fontSize: 13, color: '#334155', fontWeight: 700 }}>{doc.tipo_documento_detectado}</span>}
        {confPct != null && <span style={{ marginLeft: 8, fontSize: 13, color: confPct >= 85 ? '#10B981' : '#F59E0B' }}>Revision sugerida: {confPct}%</span>}
      </div>

      {/* Split view */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Left: Document info */}
        <div style={{ flex: 1, minWidth: 300 }}>
          <div style={section}>
            <h3 style={{ marginTop: 0 }}>Resumen del documento</h3>
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
            {doc.fecha_documento && <p><strong>Fecha:</strong> {doc.fecha_documento}</p>}
          </div>
          {doc.error_detalle && (
            <div style={{ ...section, background: '#FEF2F2', border: '1px solid #FECACA' }}>
              <h3 style={{ marginTop: 0, color: '#991B1B' }}>Incidencia detectada</h3>
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
                // Filtrar columnas que no tienen ningún dato real en las primeras 30 filas
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
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{totalFilasSheet} filas · {visibleIdxs.length} columnas visibles</span>
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
                        <strong style={{ color: '#0f172a' }}>Informacion adicional</strong>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: '6px 12px', marginTop: 8 }}>
                          {Object.entries(datos.metadata as Record<string, unknown>).map(([k, v]) => (
                            <div key={k} style={{ color: '#475569' }}><span style={{ fontWeight: 600 }}>{k}:</span> {String(v ?? '—')}</div>
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
                <h3 style={{ marginTop: 0 }}>Datos del documento</h3>
                {editMode ? (
                  <div>
                    {Object.entries(editFields).map(([key, val]) => (
                      <label key={key} style={{ display: 'flex', flexDirection: 'column', marginBottom: '0.5rem', fontSize: 13 }}>
                        <span style={{ color: '#6b7280', fontWeight: 600 }}>{formatFieldLabel(key)}</span>
                        <input value={val} onChange={e => setEditFields(f => ({ ...f, [key]: e.target.value }))} style={{ padding: '0.4rem', border: '1px solid #d1d5db', borderRadius: 6 }} />
                      </label>
                    ))}
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                      <button onClick={saveEdit} disabled={saving} style={{ ...actionBtn, background: '#6366F1' }}>{t('docDetail.buttons.saveEdit')}</button>
                      <button onClick={() => setEditMode(false)} style={{ ...actionBtn, background: '#e5e7eb', color: '#374151' }}>{t('docDetail.buttons.cancelEdit')}</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <tbody>
                        {Object.entries(datos).filter(([k, v]) => !k.startsWith('_') && (typeof v !== 'object' || v === null)).map(([key, val]) => (
                          <tr key={key} style={{ borderBottom: '1px solid #f3f4f6' }}>
                            <td style={{ padding: '0.4rem 0.5rem', fontSize: 13, color: '#6b7280', fontWeight: 600 }}>{formatFieldLabel(key)}</td>
                            <td style={{ padding: '0.4rem 0.5rem', fontSize: 14 }}>{String(val ?? '—')}</td>
                          </tr>
                        ))}
                        {Object.keys(datos).filter(k => !k.startsWith('_') && (typeof datos[k] !== 'object' || datos[k] === null)).length === 0 && (
                          <tr><td colSpan={2} style={{ padding: '1rem', textAlign: 'center', color: '#9ca3af' }}>—</td></tr>
                        )}
                      </tbody>
                    </table>
                    {(() => {
                      const items = (datos['lineas'] as unknown[] | undefined) || (datos['line_items'] as unknown[] | undefined)
                      if (!Array.isArray(items) || items.length === 0) return null
                      return (
                        <div style={{ marginTop: '0.75rem' }}>
                          <div style={{ fontSize: 13, color: '#6b7280', fontWeight: 600, marginBottom: 4 }}>Detalle ({items.length})</div>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                            <thead>
                              <tr style={{ background: '#f9fafb' }}>
                                <th style={{ padding: '0.3rem 0.5rem', textAlign: 'left', color: '#374151' }}>Descripción</th>
                                <th style={{ padding: '0.3rem 0.5rem', textAlign: 'right', color: '#374151' }}>Cant.</th>
                                <th style={{ padding: '0.3rem 0.5rem', textAlign: 'right', color: '#374151' }}>P. Unit.</th>
                                <th style={{ padding: '0.3rem 0.5rem', textAlign: 'right', color: '#374151' }}>Total</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(items as Array<Record<string, unknown>>).map((line, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                                  <td style={{ padding: '0.3rem 0.5rem' }}>{String(line.descripcion ?? line.description ?? line.producto ?? '—')}</td>
                                  <td style={{ padding: '0.3rem 0.5rem', textAlign: 'right' }}>{String(line.cantidad ?? line.qty ?? line.quantity ?? '—')}</td>
                                  <td style={{ padding: '0.3rem 0.5rem', textAlign: 'right' }}>{(line.precio_unitario ?? line.unit_price) != null ? Number(line.precio_unitario ?? line.unit_price).toFixed(2) : '—'}</td>
                                  <td style={{ padding: '0.3rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>{(line.precio_total ?? line.total_price) != null ? Number(line.precio_total ?? line.total_price).toFixed(2) : '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
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
          <h3 style={{ marginTop: 0 }}>Actividad reciente</h3>
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
          <h3 style={{ marginTop: 0 }}>Versiones relacionadas</h3>
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
                    <strong>{link.relation_direction === 'predecessor' ? 'Anterior' : 'Posterior'}</strong>
                    <span style={{ color: '#6B7280' }}>{link.estado}</span>
                    {link.relation_reason && <span style={{ color: '#6B7280' }}>{link.relation_reason}</span>}
                  </div>
                  <div style={{ color: '#111827' }}>{link.nombre_archivo}</div>
                  <div style={{ fontSize: 12, color: '#6B7280' }}>
                    {new Date(link.created_at).toLocaleString()}
                    {link.hash_sha256 ? ` · ${link.hash_sha256.slice(0, 12)}...` : ''}
                  </div>
                </div>
                <span style={{ color: '#2563EB', fontWeight: 600 }}>Abrir</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Mejora de datos */}
      {reprocess.summary && (
        (reprocess.summary.pending + reprocess.summary.invalid + reprocess.summary.review + reprocess.summary.reprocess + reprocess.summary.valid + reprocess.summary.imported) > 0
      ) && (
        <div style={{ ...section, marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <div>
              <h3 style={{ margin: 0 }}>Mejorar datos detectados</h3>
              <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
                Usa esta seccion para volver a revisar solo las partes dudosas del documento.
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {reprocess.summary.pending > 0 && (
                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#E5E7EB', color: '#374151' }}>
                  Pendientes: {reprocess.summary.pending}
                </span>
              )}
              {reprocess.summary.invalid > 0 && (
                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#FEE2E2', color: '#991B1B' }}>
                  Con problema: {reprocess.summary.invalid}
                </span>
              )}
              {reprocess.summary.review > 0 && (
                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#FEF3C7', color: '#92400E' }}>
                  En revision: {reprocess.summary.review}
                </span>
              )}
              {reprocess.summary.reprocess > 0 && (
                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#FFEDD5', color: '#9A3412' }}>
                  Pendientes de nueva revision: {reprocess.summary.reprocess}
                </span>
              )}
              {reprocess.summary.valid > 0 && (
                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#DCFCE7', color: '#166534' }}>
                  Correctas: {reprocess.summary.valid}
                </span>
              )}
              {reprocess.summary.imported > 0 && (
                <span style={{ padding: '2px 10px', borderRadius: 999, fontSize: 12, background: '#14532D', color: '#fff' }}>
                  Guardadas: {reprocess.summary.imported}
                </span>
              )}
            </div>
          </div>

          {reprocess.error && (
            <div style={{ padding: '0.5rem 0.75rem', background: '#FEE2E2', border: '1px solid #FECACA', borderRadius: 6, marginBottom: '0.75rem', fontSize: 13, color: '#991B1B' }}>
              {reprocess.error}
            </div>
          )}

          {(reprocess.summary.pending + reprocess.summary.invalid + reprocess.summary.review + reprocess.summary.reprocess) > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <button
                disabled={reprocess.isLoading}
                onClick={() => { void handleInspectReprocess() }}
                style={{
                  padding: '0.45rem 1rem',
                  background: reprocess.isLoading ? '#94A3B8' : '#6366F1',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: reprocess.isLoading ? 'not-allowed' : 'pointer',
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                {reprocess.isLoading ? 'Revisando...' : 'Ver sugerencias de mejora'}
              </button>
            </div>
          )}

          {reprocess.fieldAnalysis && (
            <div style={{ marginBottom: '0.75rem' }}>
              {reprocess.fieldAnalysis.error_summary && Object.keys(reprocess.fieldAnalysis.error_summary).length > 0 && (
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 6 }}>
                  Problemas detectados: {Object.entries(reprocess.fieldAnalysis.error_summary).map(([k, v]) => `${k} (${v})`).join(', ')}
                </div>
              )}
              {availableErrorCodes.length > 0 && (
                <div style={{ marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Filtrar por problema</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {availableErrorCodes.map(code => {
                      const checked = selectedErrorCodes.includes(code)
                      const errorCount = reprocess.fieldAnalysis?.error_summary?.[code]
                        ?? reprocessableLines.filter(line => line.error_code === code).length
                      return (
                        <label
                          key={code}
                          style={{
                            ...selectionChip,
                            background: checked ? '#FEE2E2' : '#fff',
                            borderColor: checked ? '#EF4444' : '#E5E7EB',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={e => {
                              setSelectedErrorCodes(prev => toggleStringValue(prev, code, e.target.checked))
                            }}
                          />
                          <span>{code}</span>
                          <span style={{ color: '#6B7280' }}>({errorCount})</span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}
              {availableColumns.length > 0 && (
                <div style={{ marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Columnas disponibles</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {availableColumns.map(column => {
                      const checked = selectedColumns.includes(column)
                      return (
                        <label
                          key={column}
                          style={{
                            ...selectionChip,
                            background: checked ? '#E0F2FE' : '#fff',
                            borderColor: checked ? '#0EA5E9' : '#E5E7EB',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={e => {
                              setSelectedColumns(prev => toggleStringValue(prev, column, e.target.checked))
                            }}
                          />
                          <span>{column}</span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}
              <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#374151', fontWeight: 600 }}>Dato</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#374151', fontWeight: 600, minWidth: 120 }}>Cobertura</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'right', color: '#374151', fontWeight: 600 }}>Sin valor</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'right', color: '#374151', fontWeight: 600 }}>Con problema</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: '#374151', fontWeight: 600 }}>Ejemplo</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'center', color: '#374151', fontWeight: 600 }}>Revisar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reprocess.fieldAnalysis.fields.map(field => {
                      const fillPct = Math.round((field.fill_rate ?? 0) * 100)
                      return (
                        <tr
                          key={field.field}
                          style={{
                            borderBottom: '1px solid #f3f4f6',
                            background: field.suggested_for_reprocess ? '#FEFCE8' : undefined,
                          }}
                        >
                          <td style={{ padding: '0.35rem 0.6rem', fontWeight: 600, color: '#111827' }}>{formatFieldLabel(field.field)}</td>
                          <td style={{ padding: '0.35rem 0.6rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <div style={{ flex: 1, background: '#E5E7EB', borderRadius: 999, height: 8, minWidth: 60 }}>
                                <div style={{ width: `${fillPct}%`, background: fillPct >= 80 ? '#10B981' : fillPct >= 50 ? '#F59E0B' : '#EF4444', height: '100%', borderRadius: 999 }}></div>
                              </div>
                              <span style={{ fontSize: 11, color: '#6B7280', whiteSpace: 'nowrap' }}>{fillPct}%</span>
                            </div>
                          </td>
                          <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', color: field.empty > 0 ? '#92400E' : '#9CA3AF' }}>{field.empty}</td>
                          <td style={{ padding: '0.35rem 0.6rem', textAlign: 'right', color: field.with_error > 0 ? '#991B1B' : '#9CA3AF' }}>{field.with_error}</td>
                          <td style={{ padding: '0.35rem 0.6rem', color: '#6B7280', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {field.sample_values[0] ?? '—'}
                          </td>
                          <td style={{ padding: '0.35rem 0.6rem', textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={selectedFields.includes(field.field)}
                              onChange={e => {
                                setSelectedFields(prev => toggleStringValue(prev, field.field, e.target.checked))
                              }}
                            />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {reprocessableLines.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                    Elementos disponibles ({reprocessableLines.length})
                  </div>
                  <div style={{ display: 'grid', gap: 6, maxHeight: 220, overflowY: 'auto', padding: '0.5rem', border: '1px solid #E5E7EB', borderRadius: 8, background: '#F9FAFB' }}>
                    {reprocessableLines.map(line => {
                      const checked = selectedLineNumbers.includes(line.line_number)
                      const preview = Object.entries(line.normalized_data || line.raw_data || {})
                        .slice(0, 3)
                        .map(([key, value]) => `${key}: ${String(value)}`)
                        .join(' · ')
                      return (
                        <label
                          key={line.id}
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: 8,
                            padding: '0.45rem 0.55rem',
                            borderRadius: 6,
                            border: `1px solid ${checked ? '#38BDF8' : '#E5E7EB'}`,
                            background: checked ? '#F0F9FF' : '#fff',
                            cursor: 'pointer',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={e => {
                              setSelectedLineNumbers(prev => toggleNumberValue(prev, line.line_number, e.target.checked))
                            }}
                          />
                          <div style={{ minWidth: 0 }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 2 }}>
                              <strong>Elemento {line.line_number}</strong>
                              <span style={{ color: '#6B7280' }}>{line.sheet_name || '__document__'}</span>
                              <span style={{ color: line.error_code ? '#B91C1C' : '#6B7280' }}>
                                {line.error_code || line.estado}
                              </span>
                            </div>
                            <div style={{ fontSize: 12, color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {preview || 'Sin vista previa'}
                            </div>
                          </div>
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}
              <div style={{ marginTop: '0.6rem' }}>
                <button
                  disabled={!hasSelectiveFilters || reprocess.isLoading}
                  onClick={() => {
                    void reprocess.buildReviewSession({
                      filter_estados: [],
                      filter_error_codes: selectedErrorCodes,
                      filter_campos: effectiveSelectedFields,
                      filter_columns: isDocumentScopedReprocess ? [] : selectedColumns,
                      filter_lines: selectedLineNumbers,
                      filter_sheet: activeSheet || null,
                    })
                  }}
                  style={{
                    padding: '0.45rem 1rem',
                    background: !hasSelectiveFilters ? '#D1D5DB' : '#0EA5E9',
                    color: !hasSelectiveFilters ? '#9CA3AF' : '#fff',
                    border: 'none',
                    borderRadius: 6,
                    cursor: !hasSelectiveFilters || reprocess.isLoading ? 'not-allowed' : 'pointer',
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  Crear revision enfocada
                </button>
                <div style={{ marginTop: 8, fontSize: 12, color: '#6B7280' }}>
                  {reviewSessionLabel}
                </div>
              </div>
            </div>
          )}

          {/* Sesión activa */}
          {reprocess.activeSession && (
            <div style={{ padding: '0.75rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, marginBottom: '0.75rem', fontSize: 14 }}>
              <div style={{ color: '#1D4ED8', fontWeight: 600, marginBottom: 6 }}>
                Revision creada · {reprocess.activeSession.preview_count} elemento(s) se veran afectados
              </div>
              <div style={{ fontSize: 12, color: '#1E3A8A', marginBottom: 8 }}>
                Datos: {formatSelection(reprocess.activeSession.filter_campos ?? [], 'todos')}
                {' · '}Columnas: {formatSelection(reprocess.activeSession.filter_columns ?? [], 'todas')}
                {' · '}Problemas: {formatSelection(reprocess.activeSession.filter_error_codes ?? [], 'todos')}
                {' · '}Elementos: {formatSelection(reprocess.activeSession.filter_lines ?? [], 'todos')}
              </div>
              <button
                disabled={reprocess.isRunning}
                onClick={() => { void reprocess.executeSession(reprocess.activeSession!.id) }}
                style={{
                  padding: '0.45rem 1rem',
                  background: reprocess.isRunning ? '#94A3B8' : '#10B981',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: reprocess.isRunning ? 'not-allowed' : 'pointer',
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                {reprocess.isRunning ? 'Aplicando revision...' : 'Aplicar esta revision'}
              </button>
            </div>
          )}

          {/* Resultado de la última iteración */}
          {reprocess.lastResult && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{
                padding: '0.75rem',
                background: reprocess.lastResult.improvement ? '#DCFCE7' : '#FFEDD5',
                border: `1px solid ${reprocess.lastResult.improvement ? '#86EFAC' : '#FED7AA'}`,
                borderRadius: 8,
                fontSize: 14,
              }}>
                <div style={{ fontWeight: 600, color: reprocess.lastResult.improvement ? '#166534' : '#9A3412', marginBottom: 4 }}>
                  {reprocess.lastResult.improvement ? 'Mejora detectada' : 'No hubo cambio util; revisa los datos manualmente'}
                </div>
                <div style={{ color: '#374151', fontSize: 13, marginBottom: 4 }}>
                  Revisados: {reprocess.lastResult.lines_attempted} · Correctos: {reprocess.lastResult.lines_imported} · Con problema: {reprocess.lastResult.lines_errored}
                </div>
                {reprocess.lastResult.estado === 'DONE' && (
                  <div style={{ color: '#166534', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>Todos los elementos seleccionados fueron revisados</div>
                )}
                {reprocess.lastResult.message && (
                  <div style={{ color: '#6B7280', fontSize: 12 }}>{reprocess.lastResult.message}</div>
                )}
                {reprocess.lastResult.can_retry && (
                  <button
                    onClick={() => {
                      void reprocess.refreshSummary()
                      resetSelectiveFilters()
                    }}
                    style={{
                      marginTop: 8,
                      padding: '0.35rem 0.75rem',
                      background: '#6B7280',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      cursor: 'pointer',
                      fontSize: 13,
                      fontWeight: 600,
                    }}
                  >
                    Volver a inspeccionar
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Botón rápido — reprocesar todo pendiente */}
          {reprocess.iterations.length > 0 && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                Revisiones anteriores
              </div>
              <div style={{ display: 'grid', gap: 6 }}>
                {reprocess.iterations.slice(0, 6).map(iteration => (
                  <div
                    key={iteration.id}
                    style={{
                      padding: '0.55rem 0.7rem',
                      border: '1px solid #E5E7EB',
                      borderRadius: 8,
                      background: '#F9FAFB',
                      fontSize: 12,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                      <strong>Revision {iteration.iteration_num}</strong>
                      <span style={{ color: '#6B7280' }}>{STATUS_LABELS[iteration.estado] || iteration.estado}</span>
                    </div>
                    <div style={{ color: '#374151', marginTop: 4 }}>
                      Revisados: {iteration.lines_attempted} · Correctos: {iteration.lines_imported} · Con problema: {iteration.lines_errored}
                    </div>
                    <div style={{ color: '#6B7280', marginTop: 4 }}>
                      {new Date(iteration.started_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {reprocess.totalResolvable > 0 && (
            <div style={{ borderTop: '1px solid #F3F4F6', paddingTop: '0.75rem' }}>
              <button
                disabled={reprocess.isRunning || reprocess.isLoading}
                onClick={() => { void reprocess.iterate() }}
                style={{
                  padding: '0.4rem 0.9rem',
                  background: reprocess.isRunning || reprocess.isLoading ? '#94A3B8' : '#64748B',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  cursor: reprocess.isRunning || reprocess.isLoading ? 'not-allowed' : 'pointer',
                  fontSize: 13,
                  fontWeight: 500,
                  opacity: 0.85,
                }}
              >
                Revisar todo lo pendiente ({reprocess.totalResolvable} elementos)
              </button>
            </div>
          )}
        </div>
      )}

      <SaveDocumentModal
        doc={doc}
        open={saveModalOpen}
        onClose={() => setSaveModalOpen(false)}
        onSaved={handleSaved}
      />
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
const selectionChip: React.CSSProperties = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '0.35rem 0.55rem', border: '1px solid #E5E7EB', borderRadius: 999, cursor: 'pointer', fontSize: 12 }
const statusBadge: React.CSSProperties = { color: '#fff', padding: '3px 12px', borderRadius: 12, fontSize: 13, fontWeight: 600 }
const statusColor: Record<string, string> = { CONFIRMED: '#10B981', REVIEW: '#3B82F6', PROCESSING: '#F59E0B', PENDING: '#9CA3AF', FAILED: '#EF4444', INVALID: '#EF4444', REPROCESS: '#8B5CF6', VALID: '#10B981', IMPORTED: '#0EA5E9' }
