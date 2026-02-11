import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import ImportadorLayout from './components/ImportadorLayout'
import {
    listBatchesByCompany,
    listCategories,
    listProductItems,
    startExcelImport,
    promoteBatch,
    validateBatch,
    getBatchStatus,
    patchItem,
    ingestBatch,
    resetBatch,
    deleteBatch,
    cancelBatch,
    setBatchMapping,
    listMappings,
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
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

  const [batches, setBatches] = useState<Batch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<string | null>(null)
  const selectedBatchObj = useMemo(
    () => batches.find((b) => b.id === selectedBatch) || null,
    [batches, selectedBatch]
  )
    const [productos, setProductos] = useState<ProductoPreview[]>([])
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

    // Cargar categorías
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

    // Cargar lotes pendientes de validación
    const fetchBatches = useCallback(async () => {
        if (!profile?.tenant_id) {
            setError('tenant_id not found')
            setLoading(false)
            return
        }
        try {
            setLoading(true)
            const data = await listBatchesByCompany(profile.tenant_id, token || undefined)
            const items = Array.isArray(data) ? data : (data as any).items || []
            setBatches(items)

            // Auto-seleccionar si hay batch_id en URL o priorizar PARSING/PENDING/READY
            const urlBatchId = searchParams.get('batch_id')
            if (urlBatchId) {
                setSelectedBatch(urlBatchId)
            } else {
                const arr = items as any[]
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
            const limit = pageSize
            const offset = (page - 1) * pageSize
            const data = await listProductItems(selectedBatch, {
                status: 'ERROR_VALIDATION',
                limit,
                offset,
                authToken: token || undefined,
            })
            setProductos((data as any).items || [])
            setTotalProductos(Number((data as any).total ?? ((data as any).items ? (data as any).items.length : 0)))
        } catch (err: any) {
            console.error(err)
            setProductos([])
        }
    }, [selectedBatch, token, page, pageSize])

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
        // Auto-iniciar importación si el lote está PENDING y aún no lo hemos intentado
        if (current.status === 'PENDING' && kickStarted !== selectedBatch && hasFile) {
            ; (async () => {
                try {
                    // start-excel-import solo aplica a lotes con archivo (p.ej. recetas subidas)
                    await startExcelImport(selectedBatch, token || undefined)
                    setKickStarted(selectedBatch)
                } catch (err: any) {
                    // Ignorar 404 (batch sin archivo) para no romper el polling
                    if (err?.status !== 404) {
                        console.warn('startExcelImport failed', err)
                    }
                }
            })()
        }
        // Para recipes con archivo: si está PENDING/EMPTY y no hay items, dispara ingest vacío (fast-path recetas)
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

    // Asignar categoría a productos seleccionados
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
            alert(`Error: ${err.message}`)
        }
    }

    // Promover lote a producción
    const handlePromote = async () => {
        if (!selectedBatch) return
        const confirmed = confirm('Promote this batch to production? This will create/update products in the system.')
        if (!confirmed) return

        setPromoting(true)
        try {
            await promoteBatch(selectedBatch)
            alert('Batch promoted successfully')
            navigate('../products')
        } catch (err: any) {
            alert(`Error: ${err.message}`)
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
            alert(`Error: ${err.message}`)
        }
    }

    const patchField = async (itemId: string, field: string, value: any) => {
        if (!selectedBatch) return
        try {
            await patchItem(selectedBatch, itemId, field, value)
            await fetchProductos()
        } catch (err: any) {
            alert(`Error: ${err.message}`)
        }
    }

    // Asignar texto libre como categoría a seleccionados
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
            alert(`Error: ${err.message}`)
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
    // Excluir filas que parecen encabezados de sección (no son productos)
    const visibleProductos = useMemo(() => {
        const isHeaderLike = (p: ProductoPreview) => {
            const name = (p.nombre || p.name || '').trim()
            if (!name) return false
            const upper = name.replace(/[^A-Z]/g, '').length
            const ratio = upper / name.length
            const hasDigits = /\d/.test(name)
            const tokens = name.split(/\s+/)
            // Mayormente mayúsculas, corto, sin dígitos y sin precio/stock ? encabezado
            const noAmounts = (!p.precio && !p.price) && (!p.stock || Number(p.stock) === 0)
            const banned = /^(total|subtotal|observaciones|nota)$/i.test(name)
            return !banned && ratio >= 0.6 && tokens.length <= 4 && !hasDigits && noAmounts
        }
        return productos.filter(p => !isHeaderLike(p))
    }, [productos])
    const sinCategoria = visibleProductos.filter(p => !p.categoria).length
    const categorias = [...new Set(visibleProductos.map(p => p.categoria).filter(Boolean))]

    return (
        <ImportadorLayout
            title="Preview"
            description="Validate, categorize, and promote product batches to production."
        >
            {loading && <div className="text-slate-600">Loading batches...</div>}
            {error && (
                <div className="rounded border border-rose-200 bg-rose-50 p-3 text-rose-800">{error}</div>
            )}
            {etaSeconds != null && etaSeconds > 0 && (
                <div className="mt-1 text-[11px] text-amber-700">ETA ~ {Math.floor(etaSeconds / 60)}m {etaSeconds % 60}s</div>
            )}

            {!loading && batches.length === 0 && (
                <div className="rounded-lg border border-slate-200 bg-white p-6">
                    <p className="text-slate-600">No pending batches to validate.</p>
                    <button
                        onClick={() => navigate('../')}
                        className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
                    >
                        Import files
                    </button>
                </div>
            )}

            {!loading && batches.length > 0 && (
                <>
                    {/* Batch cards */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-slate-700">
                            Select a batch to validate
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
                                    EMPTY: 'VACÍO',
                                    READY: 'READY',
                                    PARSING: 'PARSING',
                                    PENDING: 'PENDING',
                                    PROMOTED: 'PROMOTED',
                                    ERROR: 'ERROR',
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
                                                <span>{b.item_count} items</span>
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
                                <span>Procesando lote, esto puede tardar unos minutos...</span>
                                {typeof batchStatus?.progress === 'number' && (
                                    <span className="ml-auto text-sm font-medium">
                                        {Math.round(Number(batchStatus.progress ?? 0))}%
                                    </span>
                                )}
                            </div>
                            <div className="mt-1 text-[11px] text-amber-700">
                                Última actualización: {new Date().toLocaleTimeString()}
                            </div>
                            {batchStatus && (
                                <div className="mt-1 text-xs text-amber-800">
                                    Pendientes: {batchStatus.pending ?? 0} · En proceso: {batchStatus.processing ?? 0} · Completados: {batchStatus.completed ?? 0}
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
                                    <span className="text-xs text-amber-700">Parece atascado. Opciones de recuperación:</span>
                                    <button
                                        className="rounded border border-blue-300 px-2 py-1 text-xs text-blue-700 hover:bg-blue-50"
                                        onClick={async () => {
                                            if (!selectedBatch) return
                                            const cur = batches.find(b => b.id === selectedBatch)
                                            if (!cur || !(cur as any).file_key) return
                                            try {
                                                await startExcelImport(selectedBatch, token || undefined)
                                                setKickStarted(selectedBatch)
                                                setStuckSince(Date.now())
                                            } catch (err: any) {
                                                if (err?.status !== 404) throw err
                                            }
                                        }}
                                    >Reintentar</button>
                                    <button
                                        className="rounded border border-amber-300 px-2 py-1 text-xs text-amber-700 hover:bg-amber-50"
                                        onClick={async () => {
                                            if (!selectedBatch) return
                                            await resetBatch(selectedBatch, { clearItems: true, newStatus: 'PENDING' }, token || undefined)
                                            try {
                                                const cur = batches.find(b => b.id === selectedBatch)
                                                if (!cur || !(cur as any).file_key) return
                                                await startExcelImport(selectedBatch, token || undefined)
                                                setKickStarted(selectedBatch)
                                                setStuckSince(Date.now())
                                            } catch (err: any) {
                                                if (err?.status !== 404) throw err
                                            }
                                        }}
                                    >Resetear y relanzar</button>
                                    <button
                                        className="rounded border border-rose-300 px-2 py-1 text-xs text-rose-700 hover:bg-rose-50"
                                        onClick={async () => {
                                            if (!selectedBatch) return
                                            const ok = confirm('¿Eliminar lote forzado?')
                                            if (!ok) return
                                            await deleteBatch(selectedBatch, token || undefined)
                                            await fetchBatches(); setSelectedBatch(null); setProductos([])
                                        }}
                                    >Eliminar forzado</button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Estadísticas del lote */}
                    {batch && productos.length > 0 && (
                        <div className="rounded-lg border border-slate-200 bg-white p-4">
                            <h3 className="text-lg font-semibold text-slate-900 mb-3">
                                Resumen del lote
                            </h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                <div>
                                    <div className="text-slate-500">Total productos</div>
                                    <div className="text-2xl font-bold text-slate-900">{productos.length}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">Sin categoría</div>
                                    <div className="text-2xl font-bold text-amber-600">{sinCategoria}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">Categorías únicas</div>
                                    <div className="text-2xl font-bold text-blue-600">{categorias.length}</div>
                                </div>
                                <div>
                                    <div className="text-slate-500">Estado</div>
                                    <div className="text-lg font-semibold text-emerald-600">{batch.status}</div>
                                </div>
                            </div>

                            {categorias.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-slate-200">
                                    <div className="text-xs font-semibold text-slate-500 uppercase mb-2">
                                        Categorías detectadas
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

                    {/* Asignación masiva de categorías */}
                    {productos.length > 0 && selectedIds.size > 0 && (
                        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                            <div className="flex items-center gap-4">
                                <span className="text-sm font-medium text-blue-900">
                                    {selectedIds.size} producto{selectedIds.size === 1 ? '' : 's'} seleccionado{selectedIds.size === 1 ? '' : 's'}
                                </span>
                                <select
                                    value={categoryAssignment}
                                    onChange={(e) => setCategoryAssignment(e.target.value)}
                                    className="rounded-md border border-blue-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                                >
                                    <option value="">Asignar categoría...</option>
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
                            Revalidar lote
                        </button>
                        {selectedBatch && (
                            <ReassignMappingInline batchId={selectedBatch} onAfter={() => { fetchBatches(); fetchProductos() }} />
                        )}
                        <button
                            className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50"
                            onClick={async () => {
                                if (!selectedBatch) return
                                const ok = confirm('¿Eliminar este lote y todos sus items? Esta acción no se puede deshacer.')
                                if (!ok) return
                                try {
                                    await deleteBatch(selectedBatch, token || undefined)
                                    // Refresh lists
                                    await fetchBatches()
                                    setProductos([])
                                    setSelectedBatch(null)
                                } catch (err: any) {
                                    alert(`Error: ${err.message}`)
                                }
                            }}
                            disabled={!selectedBatch}
                        >
                            Eliminar lote
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
                                    Cancel task
                                </button>
                                <button
                                    className="rounded-md border border-rose-300 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50"
                                    onClick={async () => {
                                        if (!selectedBatch) return
                                        const ok = confirm('¿Eliminar forzado este lote en procesamiento?')
                                        if (!ok) return
                                        await deleteBatch(selectedBatch, token || undefined)
                                        await fetchBatches(); setProductos([]); setSelectedBatch(null)
                                    }}
                                >
                                    Eliminar forzado
                                </button>
                            </>
                        )}
                    </div>

                    {/* Herramientas de categorización */}
                    <div className="mb-3 flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-3 md:flex-row md:items-end md:justify-between">
                        <div className="flex items-end gap-2">
                            <div>
                                <label className="block text-xs font-semibold text-slate-600">Asignar categoría existente</label>
                                <div className="flex items-center gap-2">
                                    <select
                                        className="rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                                        value={categoryAssignment}
                                        onChange={(e) => setCategoryAssignment(e.target.value)}
                                    >
                                        <option value="">(elige categoría)</option>
                                        {categories.map((c) => (
                                            <option key={c.id} value={c.name}>{c.name}</option>
                                        ))}
                                        <option value="OTROS">OTROS</option>
                                    </select>
                                    <button
                                        onClick={handleAssignCategory}
                                        disabled={!categoryAssignment || selectedIds.size === 0}
                                        className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                                    >
                                        Asignar a seleccionados
                                    </button>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-600">Crear/asignar texto como categoría</label>
                                <div className="flex items-center gap-2">
                                    <input
                                        value={newCategory}
                                        onChange={(e) => setNewCategory(e.target.value)}
                                        placeholder="p. ej. LECHES Y QUESOS"
                                        className="w-64 rounded-md border border-slate-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                                    />
                                    <button
                                        onClick={handleAssignFreeCategory}
                                        disabled={!newCategory || selectedIds.size === 0}
                                        className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-slate-300"
                                    >
                                        Asignar a seleccionados
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="text-xs text-slate-600 flex flex-col gap-2">
                            <div>Seleccionados: {selectedIds.size}</div>
                            {detectedCategories.length > 0 && (
                                <div className="flex flex-wrap items-center gap-1">
                                    <span className="mr-1 text-slate-500">Categorías detectadas:</span>
                                    {detectedCategories.map((cat) => (
                                        <button
                                            key={cat}
                                            type="button"
                                            className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-100"
                                            title={`Asignar "${cat}" a seleccionados`}
                                            onClick={() => {
                                                if (selectedIds.size === 0) {
                                                    setNewCategory(cat)
                                                    return
                                                }
                                                // asignación directa a seleccionados
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
                                        title="Asignar 'OTROS' a seleccionados"
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
                                        OTROS
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Tabla de productos */}
                    {productos.length > 0 && selectedBatchObj?.source_type === 'products' && (
                        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                            {selectedBatchObj && selectedBatchObj.source_type !== 'products' && (
                                <div className="bg-amber-50 px-4 py-2 text-xs text-amber-700 border-b border-amber-200">
                                    Lote de tipo {selectedBatchObj.source_type}. La vista de tabla se muestra en formato producto solo para editar/visualizar; la promoción debería usarse para productos.
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
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Código</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Nombre</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Precio</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Costo</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Categoría</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Stock</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Errores</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Estado</th>
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
                                                                    <option value="">Sin categoría</option>
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
                                                                <span className="text-xs text-amber-600">No category</span>
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
                                                                    {p.errors.length} error{p.errors.length === 1 ? '' : 's'}
                                                                </button>
                                                            ) : (
                                                                <span className="text-xs text-emerald-700">No errors</span>
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
                                                </React.Fragment>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>

                            {/* Acciones */}
                            <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 flex items-center justify-between">
                                <span className="text-sm text-slate-600">
                                    {productos.length} product{productos.length === 1 ? '' : 's'}
                                </span>
                                <button
                                    onClick={handlePromote}
                                    disabled={promoting || sinCategoria > 0}
                                    className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:bg-slate-300 disabled:cursor-not-allowed"
                                    title={sinCategoria > 0 ? 'Assign categories to all products before promoting' : ''}
                                >
                                    {promoting ? 'Promoting...' : `Promote to production`}
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
                    {/* Tabla alternativa para lotes no-producto */}
                    {productos.length > 0 && selectedBatchObj && selectedBatchObj.source_type !== 'products' && (
                        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
                            <div className="bg-amber-50 px-4 py-2 text-xs text-amber-700 border-b border-amber-200">
                                Lote de tipo {selectedBatchObj.source_type || 'desconocido'}: vista bancaria/gastos.
                            </div>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-slate-200 text-sm">
                                    <thead className="bg-slate-50">
                                        <tr>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">#</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Fecha</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Importe</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Concepto</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Cuenta</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Cliente</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Errores</th>
                                            <th className="px-3 py-3 text-left font-medium text-slate-600">Estado</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {visibleProductos.map((p, i) => {
                                            const merged = { ...(p.raw?.datos || {}), ...(p.raw || {}), ...(p.normalized || {}) }
                                            return (
                                                <React.Fragment key={p.id}>
                                                    <tr key={p.id} className="hover:bg-slate-50">
                                                        <td className="px-3 py-2 text-slate-500">{i + 1}</td>
                                                        <td className="px-3 py-2">{merged.fecha || merged.transaction_date || '-'}</td>
                                                        <td className="px-3 py-2">{merged.importe || merged.amount || 0}</td>
                                                        <td className="px-3 py-2">{merged.concepto || merged.concept || '-'}</td>
                                                        <td className="px-3 py-2">{merged.cuenta || merged.account || '-'}</td>
                                                        <td className="px-3 py-2">{merged.cliente || merged.customer || '-'}</td>
                                                        <td className="px-3 py-2">
                                                            {p.errors && p.errors.length > 0 ? (
                                                                <button
                                                                    className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-100"
                                                                    onClick={() => setExpandedErrors(expandedErrors === p.id ? null : p.id)}
                                                                >
                                                                    {p.errors.length} error{p.errors.length === 1 ? '' : 's'}
                                                                </button>
                                                            ) : (
                                                                <span className="text-xs text-emerald-700">No errors</span>
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
                                                            <td colSpan={8} className="bg-rose-50 px-6 py-3 text-xs text-rose-700">
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

                    {/* Paginación */}
            {totalProductos > pageSize && (
                <div className="mt-4 flex items-center justify-between text-sm text-slate-700">
                    <div>
                        Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, totalProductos)} of {totalProductos}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-50"
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page <= 1}
                        >Previous</button>
                        <div>Page {page}</div>
                        <button
                            className="rounded-md border border-slate-200 px-2 py-1 disabled:opacity-50"
                            onClick={() => setPage((p) => (p * pageSize < totalProductos ? p + 1 : p))}
                            disabled={page * pageSize >= totalProductos}
                        >Next</button>
                    </div>
                </div>
            )}
        </ImportadorLayout>
    )
}

function ReassignMappingInline({ batchId, onAfter }: { batchId: string; onAfter?: () => void }) {
    const { token } = useAuth() as any
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
            console.error('Reasignar mapping falló', err)
            alert(err?.message || 'No se pudo reasignar el mapping. Revisa la consola para más detalles.')
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
                >Reassign mapping + Reprocess</button>
            ) : (
                <div className="flex items-center gap-2">
                    <select className="rounded-md border border-slate-200 px-2 py-1 text-sm" value={selected} onChange={(e) => setSelected(e.target.value)}>
                        <option value="">Select a mapping…</option>
                        {mappings.map((m) => (<option key={m.id} value={m.id}>{m.name}</option>))}
                    </select>
                    <button className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50" onClick={apply} disabled={!selected || loading}>{loading ? 'Applying…' : 'Apply and reprocess'}</button>
                    <button className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" onClick={() => setOpen(false)}>Cancel</button>
                </div>
            )}
        </>
    )
}
