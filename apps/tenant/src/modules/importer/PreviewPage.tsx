import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/AuthContext'
import ImportadorLayout from './components/ImportadorLayout'
import {
    listBatchesByCompany,
    listCategories,
    listItems,
    listProductItems,
    startExcelImport,
    promoteBatch,
    validateBatch,
    getBatchStatus,
    getBatch,
    patchItem,
    ingestBatch,
    resetBatch,
    deleteBatch,
    cancelBatch,
    setBatchMapping,
    listMappings,
    deleteAllBatches,
} from './services/importsApi'

interface Batch {
    id: string
    status: string
    source_type: string
    created_at: string
    item_count: number
    mapping_id?: string
}

interface ProductoPreview {
    id: string
    idx: number
    status: string
    errors: any[]
    batch_id: string
    sku: string | null
    codigo?: string | null
    name: string | null
    nombre?: string | null
    price: number | null
    precio?: number | string | null
    costo: number | null
    categoria: string | null
    stock: number
    unidad: string
    iva: number
    raw: Record<string, any>
    normalized?: Record<string, any>
}

interface Category {
    id: string
    name: string
    code?: string
}

export default function PreviewPage() {
    const { token, profile } = useAuth()
    const { t } = useTranslation()
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

  const [batches, setBatches] = useState<Batch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null)
  const selectedBatchObj = useMemo(
    () => batches.find((b) => b.id === selectedBatch) || null,
    [batches, selectedBatch]
  )
  const [productos, setProductos] = useState<ProductoPreview[]>([])
  const inferredBatchType = useMemo(() => {
    const sourceType = String(selectedBatchObj?.source_type || '').toLowerCase()
    if (sourceType !== 'generic') return sourceType
    if (!Array.isArray(productos) || productos.length === 0) return sourceType
    const productLike = productos.filter((p: any) => {
      const merged = { ...((p?.raw as any)?.datos || {}), ...(p?.raw || {}), ...(p?.normalized || {}) }
      return Boolean(
        merged.sku ||
        merged.codigo ||
        merged.name ||
        merged.nombre ||
        merged.producto ||
        merged.articulo ||
        merged.stock ||
        merged.existencias
      )
    }).length
    return productLike / Math.max(productos.length, 1) >= 0.6 ? 'products' : sourceType
  }, [selectedBatchObj?.source_type, productos])
  const isProductsBatch = inferredBatchType === 'products'
    const [totalProductos, setTotalProductos] = useState<number>(0)
    const [page, setPage] = useState<number>(1)
    const [pageSize, setPageSize] = useState<number>(1000)
    const [categories, setCategories] = useState<Category[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [categoryAssignment, setCategoryAssignment] = useState<string>('')
  const [promoting, setPromoting] = useState(false)
  const [newCategory, setNewCategory] = useState<string>('')
  const [expandedErrors, setExpandedErrors] = useState<string | null>(null)
  const [expandedDetails, setExpandedDetails] = useState<string | null>(null)
  const [showPromoteModal, setShowPromoteModal] = useState(false)
  const [showRecipePromoteModal, setShowRecipePromoteModal] = useState(false)
  const [recipeAlsoSaveAsProducts, setRecipeAlsoSaveAsProducts] = useState(false)
  const [promotePostAccounting, setPromotePostAccounting] = useState(false)
  const [promotePaymentStatus, setPromotePaymentStatus] = useState<'pending' | 'paid'>('pending')
  const [promotePaymentMethod, setPromotePaymentMethod] = useState<
    'bank' | 'cash' | 'card' | 'transfer' | 'direct_debit' | 'check' | 'other'
  >('bank')
  const [promotePaidAt, setPromotePaidAt] = useState<string>(() => new Date().toISOString().slice(0, 10))
  const [deletingAllProcesses, setDeletingAllProcesses] = useState(false)

    // Detected categories in the batch (by frequency)
    const detectedCategories = useMemo(() => {
        const map = new Map<string, number>()
        for (const p of productos) {
            const c = (p.categoria || '').trim()
            if (!c) continue
            map.set(c, (map.get(c) || 0) + 1)
        }
        return Array.from(map.entries())
            .sort((a, b) => b[1] - a[1])
            .map(([name]) => name)
    }, [productos])

    // Categories loader with products/product-categories fallback
    const fetchCategoriesModern = useCallback(async () => {
        try {
            const data = await listCategories(token || undefined)
            const items = Array.isArray(data)
                ? data.map((c: any) => ({ id: String(c.id ?? c.name ?? c), name: String(c.name ?? c) }))
                : []
            setCategories(items)
        } catch (err) {
            console.error('Error loading categories:', err)
        }
    }, [token])

    // Cargar categorÃ­as
    const fetchCategories = useCallback(async () => {
        try {
            const data = await listCategories(token || undefined)
            setCategories(
                Array.isArray(data)
                    ? data.map((c: any) => ({ id: String(c.id ?? c.name ?? c), name: String(c.name ?? c) }))
                    : []
            )
        } catch (err) {
            console.error('Error loading categories:', err)
        }
    }, [token])

    // Cargar lotes pendientes de validaciÃ³n
    const fetchBatches = useCallback(async () => {
        if (!profile?.tenant_id) {
            setError(t('importerPreviewPage.errors.tenantNotFound'))
            setLoading(false)
            return
        }
        try {
            setLoading(true)
            const data = await listBatchesByCompany(profile.tenant_id, token || undefined)
            const items = Array.isArray(data) ? data : (data as any).items || []

            // If coming from a deep-link (?batch_id=...), ensure that batch exists in the list
            // so source_type-based UI works (products vs other) even if list endpoint is truncated.
            const urlBatchId = searchParams.get('batch_id')
            let nextItems = items
            if (urlBatchId && !items.some((b: any) => String(b?.id) === String(urlBatchId))) {
                try {
                    const b = await getBatch(urlBatchId, token || undefined)
                    if (b && (b as any).id) {
                        nextItems = [b as any, ...items]
                    }
                } catch {
                    // ignore: fallback selection still works for non-products
                }
            }

            setBatches(nextItems)

            // Auto-seleccionar si hay batch_id en URL o priorizar PARSING/PENDING/READY
            if (urlBatchId) {
                setSelectedBatch(urlBatchId)
            } else {
                const arr = nextItems as any[]
                if (Array.isArray(arr) && arr.length > 0) {
                    const prio = (s: string) => (s === 'PARSING' ? 0 : s === 'PENDING' ? 1 : s === 'READY' ? 2 : s === 'EMPTY' ? 3 : 4)
                    const sorted = [...arr].sort((a, b) => prio(a.status) - prio(b.status))
                    setSelectedBatch(sorted[0].id)
                }
            }
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [token, profile?.tenant_id, searchParams])

    // Cargar productos del lote seleccionado
    const fetchProductos = useCallback(async () => {
        if (!selectedBatch) {
            setProductos([])
            return
        }
        try {
            const sourceType = inferredBatchType || selectedBatchObj?.source_type || ''
            if (sourceType === 'products') {
                const limit = pageSize
                const offset = (page - 1) * pageSize
                const data = await listProductItems(selectedBatch, {
                    // Show all non-promoted product items by default (OK + validation errors).
                    limit,
                    offset,
                    authToken: token || undefined,
                })
                const items = (data as any).items || []
                setProductos(items)
                setTotalProductos(Number((data as any).total ?? items.length))
            } else {
                // For non-products, show all rows (OK + ERROR_VALIDATION + ERROR) to avoid partial previews.
                const items = await listItems(selectedBatch, { authToken: token || undefined })
                setProductos((items as any[]) || [])
                setTotalProductos(Array.isArray(items) ? items.length : 0)
            }
        } catch (err: any) {
            console.error(err)
            setProductos([])
        }
    }, [selectedBatch, inferredBatchType, selectedBatchObj?.source_type, token, page, pageSize])

    // Poll batch status until READY to show progress while Celery processes
    const [batchStatus, setBatchStatus] = useState<any | null>(null)
    const [kickStarted, setKickStarted] = useState<string | null>(null)
    const [stuckSince, setStuckSince] = useState<number | null>(null)
    const [etaSeconds, setEtaSeconds] = useState<number | null>(null)
    const lastSampleRef = React.useRef<{ progress: number; serverTime: number } | null>(null)
    useEffect(() => {
        const isTerminalStatus = (s?: string | null) => ['READY', 'ERROR', 'PARTIAL', 'PROMOTED', 'VALIDATED', 'EMPTY'].includes(String(s || ''))
        if (!selectedBatch) return
        const current = batches.find(b => b.id === selectedBatch)
        if (!current) return
        // Solo lanzar start-excel si el batch tiene file_key (lotes creados desde upload)
        const hasFile = Boolean((current as any).file_key)
        // Auto-iniciar importaciÃ³n si el lote estÃ¡ PENDING y aÃºn no lo hemos intentado
        if (current.status === 'PENDING' && kickStarted !== selectedBatch && hasFile) {
            const currentBatchId = selectedBatch
            setKickStarted(currentBatchId)
            ; (async () => {
                try {
                    // start-excel-import solo aplica a lotes con archivo (p.ej. recetas subidas)
                    await startExcelImport(currentBatchId, token || undefined)
                } catch (err: any) {
                    // Ignorar 404 (batch sin archivo) para no romper el polling
                    if (err?.status !== 404) {
                        console.warn('startExcelImport failed', err)
                    }
                    setKickStarted((prev) => (prev === currentBatchId ? null : prev))
                }
            })()
        }
        // Para recipes con archivo: si estÃ¡ PENDING/EMPTY y no hay items, dispara ingest vacÃ­o (fast-path recetas)
        if (
            hasFile &&
            (current as any).source_type === 'recipes' &&
            (current.status === 'PENDING' || current.status === 'EMPTY') &&
            kickStarted === selectedBatch // ya intentamos start-excel
        ) {
            ; (async () => {
                try {
                    await ingestBatch(selectedBatch, { rows: [] }, token || undefined)
                } catch (err) {
                    console.warn('ingestBatch recipes failed', err)
                }
            })()
        }
        if (isTerminalStatus(current.status)) { setBatchStatus(null); return }
        let cancelled = false
        let lastProgress = -1
        const interval = setInterval(async () => {
            try {
                const data = await getBatchStatus(selectedBatch, token || undefined)
                if (!cancelled) {
                    setBatchStatus(data)
                    if (data && isTerminalStatus(data.status)) {
                        clearInterval(interval)
                        await fetchBatches()
                        if (data.status === 'READY') {
                            await fetchProductos()
                        }
                        return
                    }
                    const p = Number(data?.progress ?? 0)
                    const serverTs = Date.parse(String(data?.server_time || '')) || Date.now()
                    const prev = lastSampleRef.current
                    if (prev && p > prev.progress && serverTs > prev.serverTime) {
                        const dp = p - prev.progress
                        const dt = (serverTs - prev.serverTime) / 1000
                        if (dp > 0 && dt > 0 && p < 1) {
                            const remaining = (1 - p) * (dt / dp)
                            setEtaSeconds(Math.max(1, Math.round(remaining)))
                        }
                    }
                    lastSampleRef.current = { progress: p, serverTime: serverTs }
                    if (p !== lastProgress) {
                        lastProgress = p
                        setStuckSince(Date.now())
                    } else if (!stuckSince) {
                        setStuckSince(Date.now())
                    }
                }
            } catch {
                // ignore transient errors
            }
        }, 3000) // poll cada 3s para evitar rate limit
        return () => { cancelled = true; clearInterval(interval) }
    }, [selectedBatch, batches, token, fetchBatches, fetchProductos])

    useEffect(() => {
        fetchBatches()
        fetchCategoriesModern()
    }, [fetchBatches, fetchCategoriesModern])

    useEffect(() => {
        fetchProductos()
    }, [fetchProductos])

    // Reset pagination when batch changes to avoid empty views due to stale offset/page.
    useEffect(() => {
        setPage(1)
    }, [selectedBatch])

    // Asignar categorÃ­a a productos seleccionados
    const handleAssignCategory = async () => {
        if (!categoryAssignment || selectedIds.size === 0 || !selectedBatch) return
        try {
            const promises = Array.from(selectedIds).map(id =>
                patchItem(selectedBatch, id, 'categoria', categoryAssignment)
            )
            await Promise.all(promises)
            fetchProductos()
            setSelectedIds(new Set())
            setCategoryAssignment('')
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        }
    }

    // Promover lote a producciÃ³n
    const handlePromote = async () => {
        if (!selectedBatch) return

        const sourceType = selectedBatchObj?.source_type || ''

        // For recipes, show the special modal
        if (sourceType === 'recipes') {
            setShowRecipePromoteModal(true)
            return
        }

        const needsPayment = sourceType === 'invoices' || sourceType === 'expenses' || sourceType === 'receipts'
        if (needsPayment) {
            setShowPromoteModal(true)
            return
        }
        const targetPath =
            sourceType === 'products'
                ? '../products'
                : sourceType === 'expenses' || sourceType === 'receipts'
                ? '../expenses'
                : sourceType === 'invoices'
                ? '../expenses'
                : null

        const confirmMsg =
            sourceType === 'products'
                ? t('importerPreviewPage.confirm.promoteProducts')
                : sourceType === 'expenses' || sourceType === 'receipts'
                ? t('importerPreviewPage.confirm.promoteExpenses')
                : sourceType === 'invoices'
                ? t('importerPreviewPage.confirm.promoteInvoices')
                : t('importerPreviewPage.confirm.promoteGeneric')

        const confirmed = confirm(confirmMsg)
        if (!confirmed) return

        setPromoting(true)
        try {
            const res = await promoteBatch(selectedBatch)
            alert(t('importerPreviewPage.messages.promoteSuccess', { created: res.created, skipped: res.skipped, failed: res.failed }))
            if (targetPath) {
                navigate(targetPath)
            } else {
                await fetchBatches()
                await fetchProductos()
            }
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        } finally {
            setPromoting(false)
        }
    }

    const confirmPromoteRecipes = async () => {
        if (!selectedBatch) return
        setPromoting(true)
        try {
            const opts: any = {}
            if (recipeAlsoSaveAsProducts) {
                opts['save_as_products'] = 'true'
            }
            const res = await promoteBatch(selectedBatch, opts)
            alert(t('importerPreviewPage.messages.promoteRecipesSuccess', { created: res.created, skipped: res.skipped, failed: res.failed }))
            setShowRecipePromoteModal(false)
            setRecipeAlsoSaveAsProducts(false)
            await fetchBatches()
            await fetchProductos()
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        } finally {
            setPromoting(false)
        }
    }

    const confirmPromoteWithOptions = async () => {
        if (!selectedBatch) return
        setPromoting(true)
        try {
            const res = await promoteBatch(selectedBatch, {
                postAccounting: promotePostAccounting,
                paymentStatus: promotePaymentStatus,
                paymentMethod: promotePaymentStatus === 'paid' ? promotePaymentMethod : undefined,
                paidAt: promotePaymentStatus === 'paid' ? promotePaidAt : undefined,
            })
            alert(t('importerPreviewPage.messages.promoteSuccess', { created: res.created, skipped: res.skipped, failed: res.failed }))
            setShowPromoteModal(false)
            navigate('../expenses')
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        } finally {
            setPromoting(false)
        }
    }

    const handleRevalidate = async () => {
        if (!selectedBatch) return
        try {
            await validateBatch(selectedBatch)
            await fetchProductos()
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        }
    }

    const patchField = async (itemId: string, field: string, value: any) => {
        if (!selectedBatch) return
        try {
            await patchItem(selectedBatch, itemId, field, value)
            await fetchProductos()
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        }
    }

    // Asignar texto libre como categorÃ­a a seleccionados
    const handleAssignFreeCategory = async () => {
        if (!newCategory || selectedIds.size === 0 || !selectedBatch) return
        try {
            const promises = Array.from(selectedIds).map(id =>
                patchItem(selectedBatch, id, 'categoria', newCategory)
            )
            await Promise.all(promises)
            setNewCategory('')
            await fetchProductos()
        } catch (err: any) {
            alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
        }
    }

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedIds(new Set(productos.map(p => p.id)))
        } else {
            setSelectedIds(new Set())
        }
    }

    const handleSelectOne = (id: string, checked: boolean) => {
        const newSet = new Set(selectedIds)
        if (checked) newSet.add(id)
        else newSet.delete(id)
        setSelectedIds(newSet)
    }

    const batch = batches.find(b => b.id === selectedBatch)
    // Excluir filas que parecen encabezados de secciÃ³n (no son productos)
    const visibleProductos = useMemo(() => {
        if (!isProductsBatch) {
            return productos
        }
        const isHeaderLike = (p: ProductoPreview) => {
            const name = (p.nombre || p.name || '').trim()
            if (!name) return false
            const upper = name.replace(/[^A-Z]/g, '').length
            const ratio = upper / name.length
            const hasDigits = /\d/.test(name)
            const tokens = name.split(/\s+/)
            // Mayormente mayÃºsculas, corto, sin dÃ­gitos y sin precio/stock ? encabezado
            const noAmounts = (!p.precio && !p.price) && (!p.stock || Number(p.stock) === 0)
            const banned = /^(total|subtotal|observaciones|nota)$/i.test(name)
            return !banned && ratio >= 0.6 && tokens.length <= 4 && !hasDigits && noAmounts
        }
        return productos.filter(p => !isHeaderLike(p))
    }, [productos, isProductsBatch])
    const sinCategoria = visibleProductos.filter(p => !p.categoria).length
    const categorias = [...new Set(visibleProductos.map(p => p.categoria).filter(Boolean))]

    return (
        <ImportadorLayout
            title={t('importerPreviewPage.title')}
            description={t('importerPreviewPage.description')}
        >
            {loading && <div className="text-slate-600">{t('importerPreviewPage.loadingBatches')}</div>}
            {error && (
                <div className="rounded border border-rose-200 bg-rose-50 p-3 text-rose-800">{error}</div>
            )}
            {etaSeconds != null && etaSeconds > 0 && (
                <div className="mt-1 text-[11px] text-amber-700">ETA ~ {Math.floor(etaSeconds / 60)}m {etaSeconds % 60}s</div>
            )}

            {showPromoteModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
                        <div className="border-b border-slate-200 px-4 py-3">
                            <div className="text-sm font-semibold text-slate-900">{t('importerPreviewPage.promoteModal.title')}</div>
                            <div className="mt-1 text-xs text-slate-500">
                                {t('importerPreviewPage.promoteModal.description')}
                            </div>
                        </div>
                        <div className="space-y-4 px-4 py-4">
                            <label className="flex items-center gap-2 text-sm text-slate-700">
                                <input
                                    type="checkbox"
                                    checked={promotePostAccounting}
                                    onChange={(e) => setPromotePostAccounting(e.target.checked)}
                                />
                                {t('importerPreviewPage.promoteModal.postAccounting')}
                            </label>

                            <div className="grid gap-3 md:grid-cols-2">
                                <div>
                                    <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('importerPreviewPage.promoteModal.status')}</div>
                                    <select
                                        className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                                        value={promotePaymentStatus}
                                        onChange={(e) => setPromotePaymentStatus(e.target.value as any)}
                                    >
                                        <option value="pending">{t('importerPreviewPage.promoteModal.paymentPending')}</option>
                                        <option value="paid">{t('importerPreviewPage.promoteModal.paymentPaid')}</option>
                                    </select>
                                </div>
                                <div>
                                    <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('importerPreviewPage.promoteModal.method')}</div>
                                    <select
                                        className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                                        value={promotePaymentMethod}
                                        onChange={(e) => setPromotePaymentMethod(e.target.value as any)}
                                        disabled={promotePaymentStatus !== 'paid'}
                                    >
                                        <option value="bank">{t('importerPreviewPage.paymentMethods.bank')}</option>
                                        <option value="cash">{t('importerPreviewPage.paymentMethods.cash')}</option>
                                        <option value="card">{t('importerPreviewPage.paymentMethods.card')}</option>
                                        <option value="transfer">{t('importerPreviewPage.paymentMethods.transfer')}</option>
                                        <option value="direct_debit">{t('importerPreviewPage.paymentMethods.directDebit')}</option>
                                        <option value="check">{t('importerPreviewPage.paymentMethods.check')}</option>
                                        <option value="other">{t('importerPreviewPage.paymentMethods.other')}</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{t('importerPreviewPage.promoteModal.paidAt')}</div>
                                <input
                                    type="date"
                                    className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                                    value={promotePaidAt}
                                    onChange={(e) => setPromotePaidAt(e.target.value)}
                                    disabled={promotePaymentStatus !== 'paid'}
                                />
                            </div>
                        </div>
                        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-4 py-3">
                            <button
                                className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                                onClick={() => setShowPromoteModal(false)}
                                disabled={promoting}
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:bg-slate-300 disabled:cursor-not-allowed"
                                onClick={confirmPromoteWithOptions}
                                disabled={promoting}
                            >
                                {promoting ? t('importerPreviewPage.promoting') : t('importerPreviewPage.promote')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showRecipePromoteModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
                        <div className="border-b border-slate-200 px-4 py-3">
                            <div className="text-sm font-semibold text-slate-900">{t('importerPreviewPage.recipeModal.title')}</div>
                            <div className="mt-1 text-xs text-slate-500">
                                {t('importerPreviewPage.recipeModal.description')}
                            </div>
                        </div>
                        <div className="space-y-4 px-4 py-4">
                            <label className="flex items-center gap-2 text-sm text-slate-700">
                                <input
                                    type="checkbox"
                                    checked={recipeAlsoSaveAsProducts}
                                    onChange={(e) => setRecipeAlsoSaveAsProducts(e.target.checked)}
                                />
                                <span>También guardar ingredientes como productos en el inventario</span>
                            </label>
                            <div className="rounded-md bg-blue-50 p-3 text-xs text-blue-700">
                                <strong>{t('importerPreviewPage.recipeModal.noteLabel')}</strong> {t('importerPreviewPage.recipeModal.noteText')}
                            </div>
                        </div>
                        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-4 py-3">
                            <button
                                className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                                onClick={() => {
                                    setShowRecipePromoteModal(false)
                                    setRecipeAlsoSaveAsProducts(false)
                                }}
                                disabled={promoting}
                            >
                                {t('common.cancel')}
                            </button>
                            <button
                                className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:bg-slate-300 disabled:cursor-not-allowed"
                                onClick={confirmPromoteRecipes}
                                disabled={promoting}
                            >
                                {promoting ? t('importerPreviewPage.promoting') : t('importerPreviewPage.promote')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {!loading && batches.length === 0 && (
                <div className="rounded-lg border border-slate-200 bg-white p-6">
                    <p className="text-slate-600">{t('importerPreviewPage.noPendingBatches')}</p>
                    <button
                        onClick={() => navigate('../')}
                        className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
                    >
                        {t('importerPreviewPage.importFiles')}
                    </button>
                </div>
            )}

            {!loading && batches.length > 0 && (
                <>
                    {/* Batch cards */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-slate-700">
                            {t('importerPreviewPage.selectBatch')}
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {batches.map(b => {
                                const isSelected = selectedBatch === b.id
                                const statusColors = {
                                    'PENDING': 'bg-amber-50 border-amber-200 text-amber-700',
                                    'PARSING': 'bg-blue-50 border-blue-200 text-blue-700',
                                    'READY': 'bg-emerald-50 border-emerald-200 text-emerald-700',
                                    'PROMOTED': 'bg-slate-50 border-slate-200 text-slate-500',
                                    'ERROR': 'bg-rose-50 border-rose-200 text-rose-700',
                                    'EMPTY': 'bg-slate-50 border-slate-200 text-slate-500',
                                }
                                const statusLabels: Record<string, string> = {
                                    EMPTY: t('importerPreviewPage.status.empty'),
                                    READY: t('importerPreviewPage.status.ready'),
                                    PARSING: t('importerPreviewPage.status.parsing'),
                                    PENDING: t('importerPreviewPage.status.pending'),
                                    PROMOTED: t('importerPreviewPage.status.promoted'),
                                    ERROR: t('importerPreviewPage.status.error'),
                                }
                                const statusColor = statusColors[b.status as keyof typeof statusColors] || 'bg-slate-50 border-slate-200 text-slate-700'

                                return (
                                    <button
                                        key={b.id}
                                        onClick={() => setSelectedBatch(b.id)}
                                        className={`
                      relative rounded-lg border-2 p-4 text-left transition-all
                      hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500
                      ${isSelected
                                                ? 'border-blue-500 bg-blue-50 shadow-lg'
                                                : 'border-slate-200 bg-white hover:border-blue-300'
                                            }
                    `}
                                    >
                                        {isSelected && (
                                            <div className="absolute top-2 right-2">
                                                <svg className="h-5 w-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                            </div>
                                        )}

                                        <div className="space-y-2">
                                            <div className="flex items-start justify-between">
                                                <span className="font-semibold text-slate-900 capitalize">
                                                    {b.source_type}
                                                </span>
                                            </div>

                                            <div className="flex items-center gap-2 text-xs text-slate-600">
                                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                                </svg>
                                                <span>{t('importerPreviewPage.batchItems', { count: b.item_count })}</span>
                                            </div>

                                            <div className="flex items-center gap-2 text-xs text-slate-600">
                                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                </svg>
                                                <span>{new Date(b.created_at).toLocaleDateString()}</span>
                                            </div>

                                            <div className="pt-1">
                                                <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${statusColor}`}>
                                                    {statusLabels[b.status] || b.status}
                                                </span>
                                            </div>
                                        </div>
                                    </button>
                                )
                            })}
                        </div>
                    </div>

                    {/* Processing indicator for non-ready batches */}
                    {batch && (batch.status === 'PARSING' || batch.status === 'PENDING') && (
                        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900">
                            <div className="flex items-center gap-2">
                                <span className="h-2 w-2 animate-ping rounded-full bg-amber-500" />
                                <span>{t('importerPreviewPage.processing.message')}</span>
                                {typeof batchStatus?.progress === 'number' && (
                                    <span className="ml-auto text-sm font-medium">
                                        {Math.round(Number(batchStatus.progress ?? 0))}%
                                    </span>
                                )}
                            </div>
                            <div className="mt-1 text-[11px] text-amber-700">
{t('importerPreviewPage.processing.lastUpdate')}: {new Date().toLocaleTimeString()}
                            </div>
                            {batchStatus && (
                                <div className="mt-1 text-xs text-amber-800">
                                    {t('importerPreviewPage.processing.stats', { pending: batchStatus.pending ?? 0, processing: batchStatus.processing ?? 0, completed: batchStatus.completed ?? 0 })}
                                </div>
                            )}
                            <div className="mt-2 h-2 w-full rounded bg-amber-100">
                                <div
                                    className="h-2 rounded bg-amber-500 transition-[width] duration-500"
                                    style={{ width: `${Math.min(100, Math.max(0, Number(batchStatus?.progress ?? 0)))}%` }}
                                />
                            </div>
                            {(stuckSince && Date.now() - stuckSince > 60000) && (
                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <span className="text-xs text-amber-700">{t('importerPreviewPage.processing.stuckOptions')}</span>
                                    <button
                                        className="rounded border border-blue-300 px-2 py-1 text-xs text-blue-700 hover:bg-blue-50"
                                        onClick={async () => {
                                            if (!selectedBatch) return
                                            const cur = batches.find(b => b.id === selectedBatch)
                                            if (!cur || !(cur as any).file_key) return
                                            const currentBatchId = selectedBatch
                                            setKickStarted(currentBatchId)
                                            try {
                                                await startExcelImport(currentBatchId, token || undefined)
                                                setStuckSince(Date.now())
                                            } catch (err: any) {
                                                setKickStarted((prev) => (prev === currentBatchId ? null : prev))
                                                if (err?.status !== 404) throw err
                                            }
                                        }}
                                    >{t('importerPreviewPage.actions.retry')}</button>
                                    <button
                                        className="rounded border border-amber-300 px-2 py-1 text-xs text-amber-700 hover:bg-amber-50"
                                        onClick={async () => {
                                            if (!selectedBatch) return
                                            await resetBatch(selectedBatch, { clearItems: true, newStatus: 'PENDING' }, token || undefined)
                                            try {
                                                const cur = batches.find(b => b.id === selectedBatch)
                                                if (!cur || !(cur as any).file_key) return
                                                const currentBatchId = selectedBatch
                                                setKickStarted(currentBatchId)
                                                await startExcelImport(currentBatchId, token || undefined)
                                                setStuckSince(Date.now())
                                            } catch (err: any) {
                                                setKickStarted(null)
                                                if (err?.status !== 404) throw err
                                            }
                                        }}
                                    >{t('importerPreviewPage.actions.resetAndRelaunch')}</button>
                                    <button
                                        className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-700 hover:bg-rose-50"
                                        onClick={async () => {
                                            if (!selectedBatch) return
                                            const ok = confirm(t('importerPreviewPage.confirm.forceDeleteBatch'))
                                            if (!ok) return
                                            await deleteBatch(selectedBatch, token || undefined)
                                            await fetchBatches(); setSelectedBatch(null); setProductos([])
                                        }}
                                    >{t('importerPreviewPage.actions.forceDelete')}</button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* EstadÃ­sticas del lote */}
                    {batch && productos.length > 0 && (
                        <div className="rounded-lg border border-slate-200 bg-white p-4">
                            <h3 className="text-lg font-semibold text-slate-900 mb-3">
                                {t('importerPreviewPage.batchSummary.title')}
                            </h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                    <div className="text-slate-500">{isProductsBatch ? t('importerPreviewPage.batchSummary.totalProducts') : t('importerPreviewPage.batchSummary.totalRecords')}</div>
                                    <div className="text-2xl font-bold text-slate-900">{productos.length}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">{t('importerPreviewPage.batchSummary.withoutCategory')}</div>
                                    <div className="text-2xl font-bold text-amber-600">{sinCategoria}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">{isProductsBatch ? t('importerPreviewPage.batchSummary.uniqueCategories') : t('importerPreviewPage.batchSummary.uniqueLabels')}</div>
                                    <div className="text-2xl font-bold text-blue-600">{categorias.length}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">{t('importerPreview.common.status')}</div>
                                    <div className="text-lg font-semibold text-emerald-600">{batch.status}</div>
                                </div>
                            </div>

                            {categorias.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-slate-200">
                                    <div className="text-xs font-semibold text-slate-500 uppercase mb-2">
                                        {t('importerPreviewPage.batchSummary.detectedCategories')}
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        {categorias.map(cat => (
                                            <span
                                                key={cat}
                                                className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
                                            >
                                                {cat}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* AsignaciÃ³n masiva de categorÃ­as */}
                    {productos.length > 0 && selectedIds.size > 0 && (
                        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                            <div className="flex items-center gap-4">
                                <span className="text-sm font-medium text-blue-900">
                                    {t('importerPreviewPage.selectedProducts', { count: selectedIds.size })}
                                </span>
                                <select
                                    value={categoryAssignment}
                                    onChange={(e) => setCategoryAssignment(e.target.value)}
                                    className="rounded-md border border-blue-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                                >
                                    <option value="">{t('importerPreviewPage.actions.assignCategory')}</option>
                                    {categories.map(cat => (
                                        <option key={cat.id} value={cat.name}>
                                            {cat.name}
                                        </option>
                                    ))}
                                </select>
                                <button
                                    onClick={handleAssignCategory}
                                    disabled={!categoryAssignment}
                                    className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-blue-300"
                                >
                                    Asignar
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Acciones del lote */}
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                        <button
                            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
                            onClick={handleRevalidate}
                            disabled={!selectedBatch}
                        >
                            {t('importerBatchDetail.actions.revalidateBatch')}
                        </button>
                        {selectedBatch && !isProductsBatch && (
                            <button
                                onClick={handlePromote}
                                disabled={promoting}
                                className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:bg-slate-300 disabled:cursor-not-allowed"
                                title={selectedBatchObj?.source_type === 'recipes' ? t('importerPreviewPage.tooltips.promoteRecipes') : t('importerPreviewPage.tooltips.promoteBatch')}
                            >
                                {promoting ? t('importerPreviewPage.promoting') : t('importerPreviewPage.promote')}
                            </button>
                        )}
                        {selectedBatch && (
                            <ReassignMappingInline batchId={selectedBatch} onAfter={() => { fetchBatches(); fetchProductos() }} />
                        )}
                        <button
                            className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50"
                            onClick={async () => {
                                if (!selectedBatch) return
                                const ok = confirm(t('importerPreviewPage.confirm.deleteBatchWithItems'))
                                if (!ok) return
                                try {
                                    await deleteBatch(selectedBatch, token || undefined)
                                    // Refresh lists
                                    await fetchBatches()
                                    setProductos([])
                                    setSelectedBatch(null)
                                } catch (err: any) {
                                    alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
                                }
                            }}
                            disabled={!selectedBatch}
                        >
                            {t('importerPreviewPage.actions.deleteBatch')}
                        </button>
                        <button
                            className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50"
                            onClick={async () => {
                                const ok = confirm(t('importerPreviewPage.confirm.deleteAllProcesses'))
                                if (!ok) return
                                setDeletingAllProcesses(true)
                                try {
                                    await deleteAllBatches(profile?.tenant_id || '', token || undefined)
                                    // Refresh lists
                                    await fetchBatches()
                                    setProductos([])
                                    setSelectedBatch(null)
                                } catch (err: any) {
                                    alert(t('importerPreviewPage.errors.genericWithMessage', { message: err.message }))
                                } finally {
                                    setDeletingAllProcesses(false)
                                }
                            }}
                            disabled={deletingAllProcesses || batches.length === 0}
                        >
                            {deletingAllProcesses ? 'Deleting...' : t('importerPreviewPage.actions.deleteAllProcesses')}
                        </button>
                        {batch && batch.status !== 'READY' && batch.status !== 'ERROR' && (
                            <>
                                <button
                                    className="rounded-md border border-amber-300 px-3 py-2 text-sm text-amber-700 hover:bg-amber-50"
                                    onClick={async () => {
                                        if (!selectedBatch) return
                                        await cancelBatch(selectedBatch, token || undefined)
                                    }}
                                >
                                    {t('importerPreviewPage.actions.cancelTask')}
                                </button>
                                <button
                                    className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50"
                                    onClick={async () => {
                                        if (!selectedBatch) return
                                        const ok = confirm(t('importerPreviewPage.confirm.forceDeleteProcessingBatch'))
                                        if (!ok) return
                                        await deleteBatch(selectedBatch, token || undefined)
                                        await fetchBatches(); setProductos([]); setSelectedBatch(null)
                                    }}
                                >
                                    {t('importerPreviewPage.actions.forceDelete')}
                                </button>
                            </>
                        )}
                    </div>

                    {/* Herramientas de categorizaciÃ³n */}
                    <div className="mb-3 flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-3 md:flex-row md:items-end md:justify-between">
                        <div className="flex items-end gap-2">
                            <div>
                                <label className="block text-xs font-semibold text-slate-600">{t('importerPreviewPage.labels.assignExistingCategory')}</label>
                                <div className="flex items-center gap-2">
                                    <select
                                        className="rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                                        value={categoryAssignment}
                                        onChange={(e) => setCategoryAssignment(e.target.value)}
                                    >
                                        <option value="">(elige categorÃ­a)</option>
                                        {categories.map((c) => (
                                            <option key={c.id} value={c.name}>{c.name}</option>
                                        ))}
                                        <option value="OTROS">{t('importerPreviewPage.actions.others')}</option>
                                    </select>
                                    <button
                                        onClick={handleAssignCategory}
                                        disabled={!categoryAssignment || selectedIds.size === 0}
                                        className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                                    >
                                        {t('importerPreviewPage.actions.assignToSelected')}
                                    </button>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-600">Crear/asignar texto como categorÃ­a</label>
                                <div className="flex items-center gap-2">
                                    <input
                                        value={newCategory}
                                        onChange={(e) => setNewCategory(e.target.value)}
                                        placeholder={t('importerPreviewPage.placeholders.categoryExample')}
                                        className="w-64 rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                                    />
                                    <button
                                        onClick={handleAssignFreeCategory}
                                        disabled={!newCategory || selectedIds.size === 0}
                                        className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                                    >
                                        {t('importerPreviewPage.actions.assignToSelected')}
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="text-xs text-slate-600 flex flex-col gap-2">
                            <div>{t('importerPreviewPage.labels.selectedCount', { count: selectedIds.size })}</div>
                            {detectedCategories.length > 0 && (
                                <div className="flex flex-wrap items-center gap-1">
                                    <span className="mr-1 text-slate-500">{t('importerPreviewPage.batchSummary.detectedCategories')}:</span>
                                    {detectedCategories.map((cat) => (
                                        <button
                                            key={cat}
                                            type="button"
                                            className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-100"
                                            title={t('importerPreviewPage.actions.assignCategoryToSelected', { category: cat })}
                                            onClick={() => {
                                                if (selectedIds.size === 0) {
                                                    setNewCategory(cat)
                                                    return
                                                }
                                                // asignaciÃ³n directa a seleccionados
                                                const doAssign = async () => {
                                                    const promises = Array.from(selectedIds).map(id =>
                                                        patchItem(selectedBatch!, id, 'categoria', cat)
                                                    )
                                                    await Promise.all(promises)
                                                    await fetchProductos()
                                                }
                                                doAssign()
                                            }}
                                        >
                                            {cat}
                                        </button>
                                    ))}
                                    <button
                                        type="button"
                                        className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-100"
                                        title={t('importerPreviewPage.actions.assignCategoryToSelected', { category: t('importerPreviewPage.actions.others') })}
                                        onClick={() => {
                                            if (selectedIds.size === 0) { setNewCategory('OTROS'); return }
                                            const doAssign = async () => {
                                                const promises = Array.from(selectedIds).map(id =>
                                                    patchItem(selectedBatch!, id, 'categoria', 'OTROS')
                                                )
                                                await Promise.all(promises)
                                                await fetchProductos()
                                            }
                                            doAssign()
                                        }}
                                    >
                                        {t('importerPreviewPage.actions.others')}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Tabla de productos */}
                    {productos.length > 0 && isProductsBatch && (
                        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                            {selectedBatchObj && !isProductsBatch && (
                                <div className="bg-amber-50 px-4 py-2 text-xs text-amber-700 border-b border-amber-200">
                                    {t('importerPreviewPage.productTable.batchTypeNotice', { type: inferredBatchType || selectedBatchObj.source_type })}
                                </div>
                            )}
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-slate-200 text-sm">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="px-3 py-3 text-left">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedIds.size === productos.length}
                                                    onChange={(e) => handleSelectAll(e.target.checked)}
                                                />
                                            </th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">#</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">CÃ³digo</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreviewPage.productTable.name')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreviewPage.productTable.price')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreviewPage.productTable.cost')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreviewPage.productTable.category')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreviewPage.productTable.stock')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.common.errors')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.common.status')}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {visibleProductos.map((p, i) => {
                                            const precio = typeof p.price === 'number' ? p.price : parseFloat(p.precio as string) || 0
                                            const costo = Number(p.costo ?? 0)
                                            return (
                                                <React.Fragment key={p.id}>
                                                    <tr key={p.id} className="hover:bg-slate-50">
                                                        <td className="px-3 py-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={selectedIds.has(p.id)}
                                                                onChange={(e) => handleSelectOne(p.id, e.target.checked)}
                                                            />
                                                            <div className="mt-1">
                                                                <select
                                                                    className="rounded-md border border-slate-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                                                                    defaultValue={p.categoria || ''}
                                                                    onChange={(e) => patchField(p.id, 'categoria', e.target.value)}
                                                                >
                                                                    <option value="">{t('importerPreviewPage.batchSummary.withoutCategory')}</option>
                                                                    {categories.map((c) => (
                                                                        <option key={c.id} value={c.name}>{c.name}</option>
                                                                    ))}
                                                                </select>
                                                            </div>
                                                        </td>
                                                        <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                                                        <td className="px-3 py-2 text-slate-900">{p.sku || p.codigo || '-'}</td>
                                                        <td className="px-3 py-2 text-slate-900">
                                                            <input
                                                                defaultValue={p.name || p.nombre || ''}
                                                                className="w-full rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                                                                onBlur={(e) => patchField(p.id, 'nombre', e.target.value)}
                                                            />
                                                            {((p.raw as any)?.ingredients?.length || (p.raw as any)?.materials?.length) ? (
                                                                <button
                                                                    type="button"
                                                                    className="mt-1 text-xs text-blue-600 hover:text-blue-700"
                                                                    onClick={() => setExpandedDetails(expandedDetails === p.id ? null : p.id)}
                                                                >
                                                                    {expandedDetails === p.id ? t('importerPreviewPage.actions.hideSupplies') : t('importerPreviewPage.actions.viewSupplies')}
                                                                </button>
                                                            ) : null}
                                                        </td>
                                                        <td className="px-3 py-2 text-slate-900">
                                                            <input
                                                                type="number"
                                                                step="0.01"
                                                                defaultValue={precio.toFixed(2)}
                                                                className="w-28 rounded-md border border-slate-200 px-2 py-1 text-sm text-right focus:border-blue-400 focus:outline-none"
                                                                onBlur={(e) => patchField(p.id, 'precio', parseFloat(e.target.value || '0'))}
                                                            />
                                                        </td>
                                                        <td className="px-3 py-2 text-slate-600">${costo.toFixed(2)}</td>
                                                        <td className="px-3 py-2">
                                                            {p.categoria ? (
                                                                <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
                                                                    {p.categoria}
                                                                </span>
                                                            ) : (
                                                                <span className="text-xs text-amber-600">{t('importerPreviewPage.productTable.noCategory')}</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2 text-slate-900">
                                                            <input
                                                                type="number"
                                                                step="0.001"
                                                                defaultValue={String(p.stock ?? 0)}
                                                                className="w-24 rounded-md border border-slate-200 px-2 py-1 text-sm text-right focus:border-blue-400 focus:outline-none"
                                                                onBlur={(e) => patchField(p.id, 'stock', parseFloat(e.target.value || '0'))}
                                                            /> {p.unidad}
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            {p.errors && p.errors.length > 0 ? (
                                                                <button
                                                                    className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100"
                                                                    onClick={() => setExpandedErrors(expandedErrors === p.id ? null : p.id)}
                                                                >
                                                                    {t('importerPreview.common.errorCount', { count: p.errors.length })}
                                                                </button>
                                                            ) : (
                                                                <span className="text-xs text-emerald-700">{t('importerPreview.common.noErrors')}</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            {p.status === 'OK' ? (
                                                                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                                                                    OK
                                                                </span>
                                                            ) : (
                                                                <span className="inline-flex items-center rounded-full bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700">
                                                                    {p.status}
                                                                </span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                    {expandedErrors === p.id && (
                                                        <tr>
                                                            <td colSpan={11} className="bg-rose-50 px-6 py-3 text-xs text-rose-700">
                                                                <ul className="list-disc pl-5">
                                                                    {(p.errors || []).map((e: any, idx2: number) => {
                                                                        const msg = typeof e === 'string' ? e : (e?.msg || e?.message || JSON.stringify(e))
                                                                        const field = typeof e === 'string' ? '' : (e?.field ? ` [${e.field}]` : '')
                                                                        return <li key={idx2}>{msg}{field}</li>
                                                                    })}
                                                                </ul>
                                                            </td>
                                                        </tr>
                                                    )}
                                                    {expandedDetails === p.id && (
                                                        <tr>
                                                            <td colSpan={11} className="bg-slate-50 px-6 py-4 text-xs text-slate-700">
                                                                <div className="grid gap-4 md:grid-cols-2">
                                                                    <div>
                                                                        <div className="mb-2 font-semibold text-slate-800">{t('importerPreviewPage.details.ingredients')}</div>
                                                                        {Array.isArray((p.raw as any)?.ingredients) && (p.raw as any).ingredients.length > 0 ? (
                                                                            <div className="overflow-x-auto">
                                                                                <table className="min-w-full divide-y divide-slate-200">
                                                                                    <thead className="bg-white">
                                                                                        <tr>
                                                                                            <th className="px-2 py-1 text-left font-medium text-slate-600">{t('importerPreviewPage.details.ingredient')}</th>
                                                                                            <th className="px-2 py-1 text-right font-medium text-slate-600">{t('importerPreviewPage.details.qty')}</th>
                                                                                            <th className="px-2 py-1 text-left font-medium text-slate-600">{t('importerPreviewPage.details.unit')}</th>
                                                                                            <th className="px-2 py-1 text-right font-medium text-slate-600">{t('importerPreviewPage.details.amount')}</th>
                                                                                        </tr>
                                                                                    </thead>
                                                                                    <tbody className="divide-y divide-slate-100 bg-white">
                                                                                        {(p.raw as any).ingredients.map((it: any, j: number) => (
                                                                                            <tr key={j}>
                                                                                                <td className="px-2 py-1">{String(it?.ingredient ?? '')}</td>
                                                                                                <td className="px-2 py-1 text-right">{it?.quantity ?? ''}</td>
                                                                                                <td className="px-2 py-1">{String(it?.unit ?? '')}</td>
                                                                                                <td className="px-2 py-1 text-right">{typeof it?.amount === 'number' ? `$${it.amount.toFixed(3)}` : ''}</td>
                                                                                            </tr>
                                                                                        ))}
                                                                                    </tbody>
                                                                                </table>
                                                                            </div>
                                                                        ) : (
                                                                            <div className="text-slate-500">{t('importerPreviewPage.details.noIngredients')}</div>
                                                                        )}
                                                                    </div>
                                                                    <div>
                                                                        <div className="mb-2 font-semibold text-slate-800">{t('importerPreviewPage.details.materials')}</div>
                                                                        {Array.isArray((p.raw as any)?.materials) && (p.raw as any).materials.length > 0 ? (
                                                                            <div className="overflow-x-auto">
                                                                                <table className="min-w-full divide-y divide-slate-200">
                                                                                    <thead className="bg-white">
                                                                                        <tr>
                                                                                            <th className="px-2 py-1 text-left font-medium text-slate-600">Descripción</th>
                                                                                            <th className="px-2 py-1 text-right font-medium text-slate-600">{t('importerPreviewPage.details.qty')}</th>
                                                                                            <th className="px-2 py-1 text-left font-medium text-slate-600">{t('importerPreviewPage.details.purchaseUnit')}</th>
                                                                                            <th className="px-2 py-1 text-right font-medium text-slate-600">{t('importerPreviewPage.details.amount')}</th>
                                                                                        </tr>
                                                                                    </thead>
                                                                                    <tbody className="divide-y divide-slate-100 bg-white">
                                                                                        {(p.raw as any).materials.map((it: any, j: number) => (
                                                                                            <tr key={j}>
                                                                                                <td className="px-2 py-1">{String(it?.description ?? '')}</td>
                                                                                                <td className="px-2 py-1 text-right">{it?.quantity ?? ''}</td>
                                                                                                <td className="px-2 py-1">{String(it?.purchase_unit ?? '')}</td>
                                                                                                <td className="px-2 py-1 text-right">{typeof it?.amount === 'number' ? `$${it.amount.toFixed(3)}` : ''}</td>
                                                                                            </tr>
                                                                                        ))}
                                                                                    </tbody>
                                                                                </table>
                                                                            </div>
                                                                        ) : (
                                                                            <div className="text-slate-500">{t('importerPreviewPage.details.noMaterials')}</div>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    )}
                                                </React.Fragment>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>

                            {/* Acciones */}
                            <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 flex items-center justify-between">
                                <span className="text-sm text-slate-600">
                                    {t('importerPreviewPage.productCount', { count: productos.length })}
                                </span>
                                <button
                                    onClick={handlePromote}
                                    disabled={promoting || sinCategoria > 0}
                                    className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:bg-slate-300 disabled:cursor-not-allowed"
                                    title={sinCategoria > 0 ? t('importerPreviewPage.actions.assignCategoriesBeforePromote') : ''}
                                >
                                    {promoting ? t('importerPreviewPage.promoting') : t('importerPreviewPage.actions.promoteToProduction')}
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
                    {/* Tabla alternativa para lotes no-producto */}
                    {productos.length > 0 && selectedBatchObj && !isProductsBatch && (
                        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                            <div className="bg-amber-50 px-4 py-2 text-xs text-amber-700 border-b border-amber-200">
                                {inferredBatchType === 'invoices'
                                    ? t('importerPreview.bannerInvoice', { type: inferredBatchType || selectedBatchObj.source_type || 'unknown' })
                                    : t('importerPreview.bannerGeneric', { type: inferredBatchType || selectedBatchObj.source_type || 'unknown' })}
                            </div>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-slate-200 text-sm">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">#</th>
                                            {inferredBatchType === 'invoices' ? (
                                                <>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.date')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.type')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.invoiceNumber')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.idType')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.idNumber')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.customer')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.productCode')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.product')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.unitPrice')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.quantity')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.subtotal')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.vat')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.total')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.sector')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.observation')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.promotion')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.invoiceHeaders.seller')}</th>
                                                </>
                                            ) : (
                                                <>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.genericHeaders.date')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.genericHeaders.amount')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.genericHeaders.concept')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.genericHeaders.account')}</th>
                                                    <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.genericHeaders.counterparty')}</th>
                                                </>
                                            )}
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.common.errors')}</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">{t('importerPreview.common.status')}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {visibleProductos.map((p, i) => {
                                            const isInvoiceBatch = inferredBatchType === 'invoices'
                                            const merged: Record<string, any> = { ...(p.raw?.datos || {}), ...(p.raw || {}), ...(p.normalized || {}) }
                                            const mergedTotals = (merged.totals || {}) as Record<string, any>
                                            const firstLine =
                                                Array.isArray(merged.lines) && merged.lines.length > 0 ? merged.lines[0] : null
                                            const getAny = (...keys: string[]) => {
                                                for (const key of keys) {
                                                    const value = merged[key]
                                                    if (value !== undefined && value !== null && String(value).trim() !== '') {
                                                        return value
                                                    }
                                                }
                                                return ''
                                            }
                                            const fechaRaw =
                                                merged.expense_date ||
                                                merged.issue_date ||
                                                merged.invoice_date ||
                                                merged.value_date ||
                                                merged.fecha ||
                                                merged.transaction_date ||
                                                '-'
                                            const fecha =
                                                typeof fechaRaw === 'string'
                                                    ? (fechaRaw.split('T')[0] || '').split(' ')[0] || fechaRaw
                                                    : fechaRaw
                                            const importe =
                                                merged.amount ??
                                                merged.total_amount ??
                                                merged.total ??
                                                merged.importe ??
                                                mergedTotals.total ??
                                                firstLine?.total ??
                                                0
                                            const concepto =
                                                merged.description || merged.concept || merged.concepto || firstLine?.desc || '-'
                                            const cuenta = merged.cuenta || merged.account || merged.counterparty || '-'
                                            const cliente =
                                                merged.cliente ||
                                                merged.customer ||
                                                merged.vendor_name ||
                                                merged.vendor?.name ||
                                                '-'
                                            const invoiceNumber =
                                                merged.invoice_number ||
                                                merged.invoice ||
                                                merged.numero_factura ||
                                                merged.number ||
                                                '-'
                                            const isAutoInvoiceNumber =
                                                typeof invoiceNumber === 'string' &&
                                                invoiceNumber.toUpperCase().startsWith('AUTO-')
                                            const tipo = String(getAny('tipo', 'type', 'documentoTipo') || 'Factura')
                                            const tipoIdentificacion =
                                                getAny('tipo_identificacion', 'tipoIdentificacion', 'id_type', 'identification_type') || '-'
                                            const numeroIdentificacion =
                                                getAny(
                                                    'numero_identificacion',
                                                    'numeroIdentificacion',
                                                    'identification_number',
                                                    'tax_id',
                                                    'issuer_tax_id',
                                                    'supplier_tax_id',
                                                    'buyer_tax_id',
                                                ) || '-'
                                            const codProducto =
                                                getAny('codigo_producto', 'cod_producto', 'product_code', 'sku', 'code') || firstLine?.sku || '-'
                                            const producto =
                                                getAny('producto', 'product', 'description', 'concept', 'concepto') || firstLine?.desc || '-'
                                            const precioUnitario =
                                                getAny('precio_unitario', 'unit_price', 'price') || firstLine?.unit_price || '-'
                                            const cantidad = getAny('cantidad', 'qty', 'quantity') || firstLine?.qty || '-'
                                            const subtotal =
                                                getAny('subtotal', 'net_amount', 'amount_subtotal') || mergedTotals.subtotal || '-'
                                            const iva = getAny('iva', 'tax', 'tax_amount', 'amount_tax') || mergedTotals.tax || '-'
                                            const total = getAny('total', 'total_amount', 'amount_total') || mergedTotals.total || importe
                                            const sector = getAny('sector', 'category') || '-'
                                            const observacion = getAny('observacion', 'observation', 'notes') || '-'
                                            const promocion = getAny('promocion', 'promotion') || '-'
                                            const vendedor = getAny('vendedor', 'seller', 'cashier') || '-'
                                            return (
                                                <React.Fragment key={p.id}>
                                                    <tr key={p.id} className="hover:bg-slate-50">
                                                        <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                                                        {isInvoiceBatch ? (
                                                            <>
                                                                <td className="px-3 py-2">{fecha}</td>
                                                                <td className="px-3 py-2">{tipo}</td>
                                                                <td className="px-3 py-2">
                                                                    <div className="flex items-center gap-2">
                                                                        <span>{invoiceNumber}</span>
                                                                        {isAutoInvoiceNumber && (
                                                                            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-800">
                                                                                AUTO
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </td>
                                                                <td className="px-3 py-2">{tipoIdentificacion}</td>
                                                                <td className="px-3 py-2">{numeroIdentificacion}</td>
                                                                <td className="px-3 py-2">{cliente}</td>
                                                                <td className="px-3 py-2">{codProducto}</td>
                                                                <td className="px-3 py-2">{producto}</td>
                                                                <td className="px-3 py-2">{precioUnitario}</td>
                                                                <td className="px-3 py-2">{cantidad}</td>
                                                                <td className="px-3 py-2">{subtotal}</td>
                                                                <td className="px-3 py-2">{iva}</td>
                                                                <td className="px-3 py-2">{total}</td>
                                                                <td className="px-3 py-2">{sector}</td>
                                                                <td className="px-3 py-2">{observacion}</td>
                                                                <td className="px-3 py-2">{promocion}</td>
                                                                <td className="px-3 py-2">{vendedor}</td>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <td className="px-3 py-2">{fecha}</td>
                                                                <td className="px-3 py-2">{importe}</td>
                                                                <td className="px-3 py-2">{concepto}</td>
                                                                <td className="px-3 py-2">{cuenta}</td>
                                                                <td className="px-3 py-2">{cliente}</td>
                                                            </>
                                                        )}
                                                        <td className="px-3 py-2">
                                                            {p.errors && p.errors.length > 0 ? (
                                                                <button
                                                                    className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100"
                                                                    onClick={() => setExpandedErrors(expandedErrors === p.id ? null : p.id)}
                                                                >
                                                                    {t('importerPreview.common.errorCount', { count: p.errors.length })}
                                                                </button>
                                                            ) : (
                                                                <span className="text-xs text-emerald-700">{t('importerPreview.common.noErrors')}</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                                                                {p.status}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                    {expandedErrors === p.id && (
                                                        <tr>
                                                            <td colSpan={isInvoiceBatch ? 21 : 8} className="bg-rose-50 px-6 py-3 text-xs text-rose-700">
                                                                <ul className="list-disc pl-5">
                                                                    {(p.errors || []).map((e: any, idx2: number) => {
                                                                        const msg = typeof e === 'string' ? e : (e?.msg || e?.message || JSON.stringify(e))
                                                                        const field = typeof e === 'string' ? '' : (e?.field ? ` [${e.field}]` : '')
                                                                        return <li key={idx2}>{msg}{field}</li>
                                                                    })}
                                                                </ul>
                                                            </td>
                                                        </tr>
                                                    )}
                                                </React.Fragment>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* PaginaciÃ³n */}
            {totalProductos > pageSize && (
                <div className="mt-4 flex items-center justify-between text-sm text-slate-700">
                    <div>
                        {t('importerPreviewPage.pagination.showing', { from: (page - 1) * pageSize + 1, to: Math.min(page * pageSize, totalProductos), total: totalProductos })}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-50"
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page <= 1}
                        >{t('importerPreviewPage.pagination.previous')}</button>
                        <div>Page {page}</div>
                        <button
                            className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-50"
                            onClick={() => setPage((p) => (p * pageSize < totalProductos ? p + 1 : p))}
                            disabled={page * pageSize >= totalProductos}
                        >{t('importerPreviewPage.pagination.next')}</button>
                    </div>
                </div>
            )}
        </ImportadorLayout>
    )
}

function ReassignMappingInline({ batchId, onAfter }: { batchId: string; onAfter?: () => void }) {
    const { token } = useAuth() as any
    const { t } = useTranslation()
    const [open, setOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const [mappings, setMappings] = useState<{ id: string; name: string }[]>([])
    const [selected, setSelected] = useState<string>('')
    useEffect(() => {
        if (!open) return
        let cancelled = false
            ; (async () => {
                try {
                    const data = await listMappings(token || undefined)
                    if (!cancelled) setMappings((data || []).map((m) => ({ id: m.id, name: m.name })))
                } catch { }
            })()
        return () => { cancelled = true }
    }, [open, token])
    const apply = async () => {
        if (!selected) return
        setLoading(true)
        try {
            await setBatchMapping(batchId, selected, token || undefined)
            await resetBatch(batchId, { clearItems: true, newStatus: 'PENDING' }, token || undefined)
            await startExcelImport(batchId, token || undefined)
            setOpen(false)
            if (onAfter) onAfter()
        } catch (err: any) {
            console.error('Reasignar mapping fallÃ³', err)
            alert(err?.message || t('importerPreviewPage.errors.reassignMappingFailed'))
        } finally {
            setLoading(false)
        }
    }
    return (
        <>
            {!open ? (
                <button
                    className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
                    onClick={() => setOpen(true)}
                >{t('importerPreviewPage.actions.reassignAndReprocess')}</button>
            ) : (
                <div className="flex items-center gap-2">
                    <select className="rounded-md border border-slate-200 px-2 py-1 text-sm" value={selected} onChange={(e) => setSelected(e.target.value)}>
                        <option value="">{t('importerPreviewPage.actions.selectMapping')}</option>
                        {mappings.map((m) => (<option key={m.id} value={m.id}>{m.name}</option>))}
                    </select>
                    <button className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50" onClick={apply} disabled={!selected || loading}>{loading ? t('importerPreviewPage.actions.applying') : t('importerPreviewPage.actions.applyAndReprocess')}</button>
                    <button className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" onClick={() => setOpen(false)}>{t('common.cancel')}</button>
                </div>
            )}
        </>
    )
}
