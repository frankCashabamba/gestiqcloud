import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Link, useParams, useNavigate, useLocation } from 'react-router-dom'

import ImportadorLayout from './components/ImportadorLayout'

import { useAuth } from '../../auth/AuthContext'

import { procesarDocumento, pollOcrJob, guardarPendiente, type DatosImportadosCreate } from './services'

import { autoMapeoColumnas } from './services/autoMapeoColumnas'

import { createBatch, ingestBatch, listMappings, type ImportMapping, uploadExcelViaChunks } from './services/importsApi'
import MappingSuggestModal from './components/MappingSuggestModal'

import { getAliasSugeridos } from './utils/aliasCampos'

import { detectarTipoDocumento } from './utils/detectarTipoDocumento'

import { normalizarDocumento } from './utils/normalizarDocumento'

import { parseExcelFile } from './services/parseExcelFile'



const MAX_PREVIEW_ROWS = 5

const OCR_RECHECK_DELAY_MS = Number(import.meta.env.VITE_IMPORTS_JOB_RECHECK_INTERVAL ?? 4000)


const statusConfig: Record<ItemStatus, { label: string; tone: string }> = {

    pending: { label: 'Pendiente', tone: 'bg-neutral-100 text-neutral-700' },

    processing: { label: 'Procesando...', tone: 'bg-blue-50 text-blue-700' },

    ready: { label: 'Listo para guardar', tone: 'bg-emerald-50 text-emerald-700' },

    saving: { label: 'Guardando...', tone: 'bg-blue-50 text-blue-700' },

    saved: { label: 'Guardado', tone: 'bg-emerald-100 text-emerald-800' },

    duplicate: { label: 'Duplicado', tone: 'bg-amber-100 text-amber-800' },

    error: { label: 'Error', tone: 'bg-rose-100 text-rose-800' },

}



type Row = Record<string, string>

type ItemStatus = 'pending' | 'processing' | 'ready' | 'saving' | 'saved' | 'duplicate' | 'error'

type QueueItem = {

    id: string

    file: File

    name: string

    type: string

    size: number

    status: ItemStatus

    error?: string | null

    info?: string | null

    headers?: string[]

    rows?: Row[]

    docType?: string

    mappingId?: string

    jobId?: string

    batchId?: string

}



function parseCSV(text: string): { headers: string[]; rows: Row[] } {

    const lines = text.split(/\r?\n/).filter(Boolean)

    if (lines.length === 0) return { headers: [], rows: [] }

    const headers = lines[0].split(',').map((h) => h.trim())

    const rows = lines.slice(1).map((line) => {

        const cols = line.split(',')

        const row: Row = {}

        headers.forEach((h, i) => {

            row[h] = (cols[i] ?? '').trim()

        })

        return row

    })

    return { headers, rows }

}



function formatBytes(bytes: number) {

    const units = ['B', 'KB', 'MB', 'GB']

    let value = bytes

    let unitIndex = 0

    while (value >= 1024 && unitIndex < units.length - 1) {

        value /= 1024

        unitIndex += 1

    }

    const decimals = value >= 10 || unitIndex === 0 ? 0 : 1

    return `${value.toFixed(decimals)} ${units[unitIndex]}`

}



function StatusBadge({ status }: { status: ItemStatus }) {

    const { label, tone } = statusConfig[status]

    return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${tone}`}>{label}</span>

}



function PreviewTable({ headers, rows }: { headers?: string[]; rows?: Row[] }) {

    if (!headers || headers.length === 0 || !rows || rows.length === 0) return null

    const preview = rows.slice(0, MAX_PREVIEW_ROWS)

    return (

        <div className="overflow-auto rounded border border-neutral-200">

            <table className="min-w-full text-xs">

                <thead className="bg-neutral-50">

                    <tr>

                        {headers.map((header) => (

                            <th key={header} className="px-3 py-2 text-left font-medium text-neutral-600">

                                {header}

                            </th>

                        ))}

                    </tr>

                </thead>

                <tbody>

                    {preview.map((row, idx) => (

                        <tr key={idx} className="border-t border-neutral-100">

                            {headers.map((header) => (

                                <td key={header} className="px-3 py-2 text-neutral-800">

                                    {row[header] || '-'}

                                </td>

                            ))}

                        </tr>

                    ))}

                </tbody>

            </table>

            {rows.length > preview.length && (

                <div className="border-t border-neutral-100 px-3 py-2 text-right text-[11px] text-neutral-500">

                    Mostrando {preview.length} de {rows.length} filas procesadas

                </div>

            )}

        </div>

    )

}



export default function ImportadorPage() {

    const { token } = useAuth() as { token: string | null }

    const [queue, setQueue] = useState<QueueItem[]>([])
    const queueRef = useRef<QueueItem[]>([])

    const [globalError, setGlobalError] = useState<string | null>(null)

    const [savingAll, setSavingAll] = useState(false)

    const [savedSummary, setSavedSummary] = useState<{ saved: number; errors: number; lastBatchId?: string; lastDocType?: string } | null>(null)

    const [expandedId, setExpandedId] = useState<string | null>(null)

    const [mappings, setMappings] = useState<ImportMapping[]>([])

    const [defaultMappingId, setDefaultMappingId] = useState<string>('')

    const [loadingMappings, setLoadingMappings] = useState(false)

    const [mappingsError, setMappingsError] = useState<string | null>(null)

    // Modal de sugerencia de mapping
    const [mappingModalOpen, setMappingModalOpen] = useState(false)
    const [mappingFile, setMappingFile] = useState<File | null>(null)
    const [mappingTargetId, setMappingTargetId] = useState<string | null>(null)

    const cameraInputRef = useRef<HTMLInputElement | null>(null)
    const videoRef = useRef<HTMLVideoElement | null>(null)
    const streamRef = useRef<MediaStream | null>(null)

    // Aviso no intrusivo cuando se guarda un archivo pero hay más en cola
    const [recentSaved, setRecentSaved] = useState<{ batchId: string; name?: string } | null>(null)

    const [cameraAvailable, setCameraAvailable] = useState(false)
    const [cameraModalOpen, setCameraModalOpen] = useState(false)
    const [cameraInitializing, setCameraInitializing] = useState(false)
    const [cameraError, setCameraError] = useState<string | null>(null)

    const { empresa } = useParams()
    const navigate = useNavigate()
    const location = useLocation()
    const basePath = (location?.pathname || '').replace(/\/$/, '')

    useEffect(() => {
        queueRef.current = queue
    }, [queue])

    useEffect(() => {
        if (typeof navigator !== 'undefined' && typeof navigator.mediaDevices?.getUserMedia === 'function') {
            setCameraAvailable(true)
        } else {
            setCameraAvailable(false)
        }
    }, [])

    useEffect(() => {

        if (!token) {

            setMappings([])

            setDefaultMappingId('')

            setLoadingMappings(false)

            setMappingsError(null)

            return

        }

        let cancelled = false

        const fetchMappings = async () => {

            setLoadingMappings(true)

            setMappingsError(null)

            try {

                const data = await listMappings(token)

                if (!cancelled) {

                    setMappings(data)

                }

            } catch (err: any) {

                if (!cancelled) {

                    setMappingsError(err?.message || 'No se pudieron cargar las plantillas')

                }

            } finally {

                if (!cancelled) {

                    setLoadingMappings(false)

                }

            }

        }

        fetchMappings()

        return () => {

            cancelled = true

        }

    }, [token])



    useEffect(() => {

        if (!defaultMappingId && mappings.length > 0) {

            setDefaultMappingId(mappings[0].id)

        }

    }, [mappings, defaultMappingId])



    const enqueueFiles = useCallback((files: File[]) => {
        if (!files.length) return
        const timestamp = Date.now()
        const items: QueueItem[] = files.map((file, idx) => ({
            id: `${timestamp}-${idx}`,
            file,
            name: file.name,
            type: file.type,
            size: file.size,
            status: 'pending',
            mappingId: defaultMappingId || undefined,
            info: null,
            jobId: undefined,
        }))
        setQueue((prev) => [...items, ...prev])
        setGlobalError(null)
        setSavedSummary(null)
    }, [defaultMappingId])

    const onFiles: React.ChangeEventHandler<HTMLInputElement> = (e) => {
        const files = Array.from(e.target.files || [])
        enqueueFiles(files)
        e.target.value = ''
    }

    const onCameraCapture: React.ChangeEventHandler<HTMLInputElement> = (e) => {
        const files = Array.from(e.target.files || [])
        enqueueFiles(files)
        e.target.value = ''
    }

    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop())
            streamRef.current = null
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null
        }
    }, [])

    const closeCameraModal = useCallback(() => {
        stopCamera()
        setCameraInitializing(false)
        setCameraModalOpen(false)
        setCameraError(null)
    }, [stopCamera])

    const openCameraModal = useCallback(async () => {
        if (!cameraAvailable) {
            cameraInputRef.current?.click()
            return
        }
        setCameraError(null)
        setCameraModalOpen(true)
        setCameraInitializing(true)
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' },
                audio: false,
            })
            streamRef.current = stream
            if (videoRef.current) {
                videoRef.current.srcObject = stream
                await videoRef.current.play().catch(() => { })
            }
        } catch (err: any) {
            setCameraError(err?.message || 'No se pudo acceder a la c�mara')
            stopCamera()
        } finally {
            setCameraInitializing(false)
        }
    }, [cameraAvailable, stopCamera])

    const capturePhoto = useCallback(async () => {
        if (!videoRef.current) {
            setCameraError('La c�mara a�n no est� lista')
            return
        }
        const video = videoRef.current
        const width = video.videoWidth || 1280
        const height = video.videoHeight || 720
        if (!width || !height) {
            setCameraError('La c�mara a�n no est� lista')
            return
        }
        setCameraInitializing(true)
        try {
            const canvas = document.createElement('canvas')
            canvas.width = width
            canvas.height = height
            const ctx = canvas.getContext('2d')
            if (!ctx) throw new Error('No se pudo procesar la imagen')
            ctx.drawImage(video, 0, 0, width, height)
            const blob: Blob | null = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92))
            if (!blob) throw new Error('No se pudo capturar la foto')
            const file = new File([blob], `captura_${Date.now()}.jpeg`, { type: blob.type || 'image/jpeg' })
            enqueueFiles([file])
            closeCameraModal()
        } catch (err: any) {
            setCameraError(err?.message || 'No se pudo capturar la foto')
        } finally {
            setCameraInitializing(false)
        }
    }, [closeCameraModal, enqueueFiles])

    const triggerCameraCapture = () => {
        if (cameraAvailable) {
            openCameraModal()
        } else {
            cameraInputRef.current?.click()
        }
    }

    useEffect(() => {
        return () => {
            stopCamera()
        }
    }, [stopCamera])

    const updateQueue = useCallback((id: string, changes: Partial<QueueItem>) => {
        setQueue((prev) => {
            const next = prev.map((item) => (item.id === id ? { ...item, ...changes } : item))
            queueRef.current = next
            return next
        })
    }, [])




    const processItem = useCallback(
        async (item: QueueItem) => {
            const ext = item.name.toLowerCase()
            const isCSV = ext.endsWith('.csv')
            const isExcel = ext.endsWith('.xlsx') || ext.endsWith('.xls') || item.type.includes('spreadsheet')
            const isDoc = ext.endsWith('.pdf') || item.type.startsWith('image/')

            updateQueue(item.id, { status: 'processing', error: null, info: null })

            try {
                if (isCSV) {
                    const textContent = await item.file.text()
                    const { headers, rows } = parseCSV(textContent)
                    const docType = detectarTipoDocumento(headers)
                    updateQueue(item.id, { status: 'ready', headers, rows, docType, error: null, info: null, jobId: undefined })
                    // Guardar y navegar siempre a vista previa si hay batch_id, sin importar docType
                    {
                        const ok = await saveItem({ ...item, headers, rows, docType })
                        if (ok && item.batchId) {
                            navigate(`preview?batch_id=${item.batchId}`)
                        }
                    }
                    return
                }

                if (isExcel) {
                    // Si no hay mapping seleccionado, intentar auto-reutilizar por patrón del nombre de archivo
                    let effectiveMappingId = item.mappingId || defaultMappingId || ''
                    if (!effectiveMappingId && mappings && mappings.length) {
                        const matched = mappings.find((m) => {
                            try {
                                if (!m.file_pattern) return false
                                const rx = new RegExp(m.file_pattern, 'i')
                                return rx.test(item.name)
                            } catch { return false }
                        })
                        if (matched) {
                            effectiveMappingId = matched.id
                            updateQueue(item.id, { mappingId: matched.id, info: `Usando mapping: ${matched.name}` })
                        }
                    }
                    // Si no hay mapping, continuar sin él (el backend hará auto-mapeo)
                    if (!effectiveMappingId) {
                        updateQueue(item.id, { info: 'Procesando sin plantilla de mapeo' })
                    }
                    // For very large Excel files, use chunked upload + Celery processing
                    const thresholdMb = Number(import.meta.env.VITE_IMPORTS_CHUNK_THRESHOLD_MB ?? 8)
                    if (item.size > thresholdMb * 1024 * 1024) {
                        updateQueue(item.id, { status: 'processing', error: null, info: 'Subiendo archivo por partes...' })
                        const res = await uploadExcelViaChunks(item.file, {
                            sourceType: 'products',
                            mappingId: effectiveMappingId || undefined,
                            onProgress: (pct) => updateQueue(item.id, { info: `Subiendo... ${pct}%` }),
                        })
                        updateQueue(item.id, { status: 'saved', info: 'Procesando en segundo plano...', batchId: res.batchId })
                        navigate(`preview?batch_id=${res.batchId}`)
                        return
                    }
                    const { headers, rows } = await parseExcelFile(item.file)
                    const docType = detectarTipoDocumento(headers)
                    updateQueue(item.id, { status: 'ready', headers, rows, docType, error: null, info: null, jobId: undefined })
                    // Guardar y navegar siempre a vista previa si hay batch_id, sin importar docType
                    {
                        const ok = await saveItem({ ...item, headers, rows, docType })
                        if (ok && item.batchId) {
                            navigate(`preview?batch_id=${item.batchId}`)
                        }
                    }
                    return
                }

                if (isDoc) {
                    const response = item.jobId
                        ? await pollOcrJob(item.jobId, token || undefined)
                        : await procesarDocumento(item.file, token || undefined)

                    if (response.status === 'pending') {
                        updateQueue(item.id, {
                            status: 'processing',
                            error: null,
                            info: 'Estamos procesando tu documento. Esto puede tardar unos segundos.',
                            jobId: response.jobId,
                        })

                        setTimeout(() => {
                            const current = queueRef.current.find((queued) => queued.id === item.id)
                            if (current && current.status === 'processing' && current.jobId === response.jobId) {
                                processItem(current)
                            }
                        }, OCR_RECHECK_DELAY_MS)
                        return
                    }

                    const documentos = Array.isArray(response.payload?.documentos) ? response.payload.documentos : []
                    const headers = documentos.length ? Object.keys(documentos[0]) : []
                    const rows: Row[] = documentos.map((doc: Record<string, unknown>) => {
                        const result: Row = {}
                        headers.forEach((header) => {
                            result[header] = String(doc[header] ?? '')
                        })
                        return result
                    })

                    const docType = (documentos[0]?.documentoTipo as string) || 'generico'

                    updateQueue(item.id, {
                        status: 'ready',
                        headers,
                        rows,
                        docType,
                        error: null,
                        info: null,
                        jobId: response.jobId,
                    })
                    {
                        const ok = await saveItem({ ...item, headers, rows, docType })
                        if (ok && item.batchId) {
                            navigate(`preview?batch_id=${item.batchId}`)
                        }
                    }
                    return
                }

                throw new Error('Tipo de archivo no soportado')
            } catch (err: any) {
                updateQueue(item.id, {
                    status: 'error',
                    error: err?.message || 'Ocurri? un error al procesar el archivo',
                    info: null,
                    jobId: undefined,
                })
            }
        },
        [token, updateQueue, mappings, defaultMappingId],
    )

    const processAll = async () => {

        setGlobalError(null)

        const pendings = queue.filter((q) => q.status === 'pending')

        for (const item of pendings) {

            // eslint-disable-next-line no-await-in-loop

            await processItem(item)

        }

    }



    const saveItem = useCallback(

        async (item: QueueItem) => {

            if (!item.headers || !item.rows) return false

            updateQueue(item.id, { status: 'saving', error: null, info: null })

            const sugeridos = autoMapeoColumnas(item.headers, getAliasSugeridos())

            // Para productos, normalizar a shape de producto; en otros casos, documento genérico
            let docs: any[]
            if ((item.docType || '').toLowerCase() === 'productos') {
                const { normalizarProductos } = await import('./utils/normalizarProductosSections')
                docs = normalizarProductos(item.rows)
            } else {
                docs = normalizarDocumento(item.rows, sugeridos as any)
            }

            const metadata = {

                filename: item.name,

                docType: item.docType || 'generico',

                rows: docs.length,

                mimeType: item.type,

            }



            try {

                const batch = await createBatch({

                    source_type: item.docType || 'manual-upload',

                    origin: item.name || 'importador-tenant',

                    mapping_id: item.mappingId || (defaultMappingId || undefined),

                    metadata,

                })

                await ingestBatch(batch.id, { rows: docs })

                // Propagar el batchId al item local para que saveAll pueda detectarlo
                // y habilitar la navegación hacia la vista de preview.
                item.batchId = batch.id

                updateQueue(item.id, { status: 'saved', info: null, jobId: undefined, batchId: batch.id })

                return true

            } catch (primaryError: any) {

                console.warn('Fallo al crear/ingestar lote, intentando fallback a pendientes', primaryError)

                try {

                    for (const doc of docs) {

                        const payload: DatosImportadosCreate = {

                            tipo: 'documento',

                            origen: 'excel',

                            datos: { ...doc, documentoTipo: item.docType || 'generico' },

                        }

                        // eslint-disable-next-line no-await-in-loop

                        await guardarPendiente(payload)

                    }

                    updateQueue(item.id, { status: 'saved', info: null, jobId: undefined })

                    return true

                } catch (fallbackError: any) {

                    const message =

                        fallbackError?.message || primaryError?.message || 'Error al guardar el documento'

                    updateQueue(item.id, { status: 'error', error: message, info: null, jobId: undefined })

                    return false

                }

            }

        },

        [token, updateQueue],

    )



    const saveAll = async () => {

        setSavingAll(true)

        setGlobalError(null)

        setSavedSummary(null)

        const readyItems = queue.filter((q) => q.status === 'ready')

        let savedCounter = 0

        let errorCounter = 0

        let lastBatchId: string | undefined
        let lastDocType: string | undefined



        for (const item of readyItems) {

            // eslint-disable-next-line no-await-in-loop

            const ok = await saveItem(item)

            if (ok) {
                savedCounter += 1
                if (item.batchId) lastBatchId = item.batchId
                if (item.docType) lastDocType = item.docType
            }

            else errorCounter += 1

        }



        if (errorCounter) {

            setGlobalError('Algunos archivos no se pudieron guardar. Revisa la cola para mas detalles.')

        }

        setSavedSummary({ saved: savedCounter, errors: errorCounter, lastBatchId, lastDocType })

        setSavingAll(false)

        if (savedCounter > 0 && lastBatchId) {
            setTimeout(() => navigate(`preview?batch_id=${lastBatchId}`), 2000)
        }

    }



    const anyPending = queue.some((item) => item.status === 'pending')

    const anyReady = queue.some((item) => item.status === 'ready')

    const total = useMemo(() => queue.length, [queue])



    return (

        <>
            <ImportadorLayout

                title="Importar archivos"

                description="Sube recibos, archivos CSV o Excel y documentos PDF. Revisa la previsualizacion y guarda los registros en pendientes cuando estes conforme."

                actions={

                    total > 0 && (

                        <>

                            <button

                                type="button"

                                className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"

                                onClick={processAll}

                                disabled={!anyPending}

                            >

                                Procesar pendientes

                            </button>

                            <button

                                type="button"

                                className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-green-300"

                                onClick={saveAll}

                                disabled={!anyReady || savingAll}

                            >

                                {savingAll ? 'Enviando...' : 'Enviar todo a vista previa'}

                            </button>

                        </>

                    )

                }

            >

                {cameraModalOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
                        <div className="w-full max-w-sm rounded-lg bg-white p-4 shadow-xl">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-semibold text-neutral-900">Capturar foto</h3>
                                <button
                                    type="button"
                                    className="text-xs text-neutral-500 hover:text-neutral-700"
                                    onClick={closeCameraModal}
                                >
                                    Cerrar
                                </button>
                            </div>
                            <div className="mt-3 aspect-[3/4] w-full overflow-hidden rounded-md bg-neutral-900">
                                <video
                                    ref={videoRef}
                                    playsInline
                                    autoPlay
                                    muted
                                    className={`h-full w-full object-cover ${cameraInitializing || cameraError ? 'hidden' : ''}`}
                                />
                                {(cameraInitializing || cameraError) && (
                                    <div className="flex h-full items-center justify-center px-3 text-center text-xs text-white">
                                        {cameraError || 'Iniciando c�mara...'}
                                    </div>
                                )}
                            </div>
                            <div className="mt-3 flex flex-col gap-1 text-xs text-neutral-500">
                                <span>Alinea el documento antes de capturar.</span>
                                <span>Si tienes problemas, usa la opci�n de subir archivo.</span>
                            </div>
                            <div className="mt-4 flex flex-wrap justify-between gap-2">
                                <button
                                    type="button"
                                    className="rounded-md border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
                                    onClick={closeCameraModal}
                                >
                                    Cancelar
                                </button>
                                <div className="flex gap-2">
                                    <button
                                        type="button"
                                        className="rounded-md border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
                                        onClick={() => { closeCameraModal(); cameraInputRef.current?.click() }}
                                    >
                                        Subir archivo
                                    </button>
                                    <button
                                        type="button"
                                        className="rounded-md bg-blue-600 px-3 py-2 text-xs font-medium text-white shadow hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-300"
                                        onClick={capturePhoto}
                                        disabled={cameraInitializing}
                                    >
                                        {cameraInitializing ? 'Procesando...' : 'Capturar'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                <section className="grid gap-6 lg:grid-cols-[2fr,3fr]">

                    <div className="rounded-lg border border-dashed border-neutral-300 bg-white p-6 shadow-sm">

                        <div className="flex h-full flex-col justify-between gap-6">

                            <div className="space-y-3">

                                <h2 className="text-lg font-semibold text-neutral-900">Anade archivos</h2>

                                <p className="text-sm text-neutral-600">

                                    Aceptamos CSV, Excel, PDF o imagenes (JPG/PNG). Puedes arrastrarlos aqui o seleccionarlos manualmente.

                                </p>

                                <div className="space-y-1">

                                    <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">Plantilla de mapeo</label>

                                    {mappingsError ? (

                                        <div className="text-xs text-rose-600">{mappingsError}</div>

                                    ) : loadingMappings ? (

                                        <div className="text-xs text-neutral-500">Cargando plantillas...</div>

                                    ) : mappings.length ? (

                                        <select

                                            className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"

                                            value={defaultMappingId}

                                            onChange={(event) => setDefaultMappingId(event.target.value)}

                                        >

                                            <option value="">Sin plantilla</option>

                                            {mappings.map((mapping) => (

                                                <option key={mapping.id} value={mapping.id}>

                                                    {mapping.name} ({mapping.source_type})

                                                </option>

                                            ))}

                                        </select>

                                    ) : (

                                        <div className="text-xs text-neutral-400">No hay plantillas configuradas.</div>

                                    )}

                                </div>

                                <div className="flex w-full flex-wrap items-center gap-3">

                                    <label className="group flex flex-1 cursor-pointer flex-col items-center justify-center rounded-md border border-neutral-200 bg-neutral-50 px-4 py-8 text-center transition hover:border-blue-400 hover:bg-blue-50">

                                        <span className="text-sm font-medium text-blue-700 group-hover:text-blue-600">Seleccionar archivos</span>

                                        <span className="mt-1 text-xs text-neutral-500">Max. 10 archivos por lote</span>

                                        <input

                                            className="hidden"

                                            type="file"

                                            multiple

                                            accept=".csv,.xlsx,.xls,.pdf,image/*"

                                            onChange={onFiles}

                                        />

                                    </label>

                                    <button

                                        type="button"

                                        className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:bg-neutral-100"

                                        onClick={triggerCameraCapture}

                                        disabled={cameraModalOpen || cameraInitializing}

                                        title={cameraAvailable ? 'Abrir camara' : 'El dispositivo no expone camara, se abrira el selector de archivos'}

                                    >

                                        {cameraAvailable ? 'Abrir camara' : 'Subir foto'}

                                    </button>

                                </div>

                                <input

                                    ref={cameraInputRef}

                                    className="hidden"

                                    type="file"

                                    accept="image/*"

                                    capture="environment"

                                    onChange={onCameraCapture}

                                />

                            </div>

                            <ul className="space-y-2 text-xs text-neutral-500">

                                <li>Detectamos tipo de documento automaticamente.</li>

                                <li>Aplica plantillas de mapeo al crear cada lote.</li>

                                <li>Cada archivo genera un bloque de filas que puedes revisar antes de guardar.</li>

                            </ul>

                        </div>

                    </div>

                    <div className="space-y-4">

                        <div className="flex items-center justify-between">

                            <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Cola de documentos</h3>

                            <span className="text-xs text-neutral-500">{total} archivo{total === 1 ? '' : 's'}</span>

                        </div>



                        {globalError && (

                            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">

                                {globalError}

                            </div>

                        )}



                        {total === 0 && (

                            <div className="rounded-lg border border-neutral-200 bg-white p-6 text-sm text-neutral-600 shadow-sm">

                                Todavia no hay archivos en la cola. Sube uno para comenzar.

                            </div>

                        )}



                        <div className="space-y-4">

                            {queue.map((item) => {

                                const isExpanded = expandedId === item.id

                                const hasPreview = !!item.headers?.length && !!item.rows?.length

                                const mapping = item.mappingId ? mappings.find((m) => m.id === item.mappingId) : undefined

                                return (

                                    <article key={item.id} className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">

                                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">

                                            <div className="space-y-1">

                                                <div className="flex flex-wrap items-center gap-2">

                                                    <h4 className="text-sm font-semibold text-neutral-900">{item.name}</h4>

                                                    <StatusBadge status={item.status} />

                                                </div>

                                                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-500">

                                                    <span>{item.type || 'Archivo'}</span>

                                                    <span>{formatBytes(item.size)}</span>

                                                    {item.rows && <span>{item.rows.length} filas detectadas</span>}

                                                    {item.docType && <span>Tipo: {item.docType}</span>}

                                                </div>

                                                <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-500">

                                                    <span>Plantilla:</span>

                                                    {mappings.length ? (

                                                        <select

                                                            className="rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"

                                                            value={item.mappingId || ''}

                                                            onChange={(event) =>

                                                                updateQueue(item.id, { mappingId: event.target.value || undefined })

                                                            }

                                                        >

                                                            <option value="">Sin plantilla</option>

                                                            {mappings.map((mappingOption) => (

                                                                <option key={mappingOption.id} value={mappingOption.id}>

                                                                    {mappingOption.name}

                                                                </option>

                                                            ))}

                                                        </select>

                                                    ) : (

                                                        <span className="text-neutral-400">No disponible</span>

                                                    )}

                                                    {mapping && (

                                                        <span className="text-neutral-400">({mapping.source_type})</span>

                                                    )}

                                                </div>

                                                {(item.status === 'processing' || item.status === 'saving') && (
                                                    <div className="flex items-center gap-2 text-xs text-blue-600">
                                                        <span className="h-2 w-2 animate-ping rounded-full bg-blue-500" />
                                                        <span>{item.status === 'processing' ? 'Analizando documento...' : 'Guardando datos...'}</span>
                                                    </div>
                                                )}

                                            </div>

                                            <div className="flex flex-wrap items-center gap-2">

                                                {item.status === 'pending' && (

                                                    <button

                                                        type="button"

                                                        className="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"

                                                        onClick={() => processItem(item)}

                                                    >

                                                        Procesar

                                                    </button>

                                                )}

                                                {(item.status === 'ready' || item.status === 'saving') && (
                                                    <button
                                                        type="button"
                                                        className="rounded-md bg-green-600 px-3 py-1.5 text-xs font-medium text-white shadow hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-green-300"
                                                        onClick={async () => {
                                                            const ok = await saveItem(item)
                                                            if (ok && item.batchId) {
                                                                // Solo redirige automático si este es el único archivo en la cola.
                                                                if (total <= 1) {
                                                                    setTimeout(() => navigate(`preview?batch_id=${item.batchId}`), 500)
                                                                } else {
                                                                    // Mostrar aviso con acceso directo a la vista previa de este batch
                                                                    setRecentSaved({ batchId: item.batchId, name: item.name })
                                                                }
                                                            }
                                                        }}
                                                        disabled={item.status === 'saving'}
                                                    >
                                                        {item.status === 'saving' ? 'Enviando...' : 'Enviar a vista previa'}
                                                    </button>
                                                )}

                                                {(item.status === 'error' || item.status === 'saved') && (

                                                    <button

                                                        type="button"

                                                        className="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100"

                                                        onClick={() => processItem(item)}

                                                    >

                                                        Volver a procesar

                                                    </button>

                                                )}

                                                {hasPreview && (

                                                    <button

                                                        type="button"

                                                        className="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100"

                                                        onClick={() => setExpandedId((prev) => (prev === item.id ? null : item.id))}

                                                    >

                                                        {isExpanded ? 'Ocultar vista previa' : 'Ver vista previa'}

                                                    </button>

                                                )}

                                            </div>

                                        </div>



                                        {item.info && (

                                            <div className="mt-3 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">

                                                {item.info}

                                            </div>

                                        )}

                                        {item.status === 'error' && item.error && (

                                            <div className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">

                                                {item.error}

                                            </div>

                                        )}



                                        {hasPreview && isExpanded && (

                                            <div className="mt-4">

                                                <PreviewTable headers={item.headers} rows={item.rows} />

                                            </div>

                                        )}

                                    </article>

                                )

                            })}

                        </div>

                    </div>

                </section>



                {savedSummary && (

                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">

                        Guardados {savedSummary.saved} archivo{savedSummary.saved === 1 ? '' : 's'} en staging

                        {savedSummary.errors ? `, ${savedSummary.errors} con error.` : '.'}

                        <div className="mt-2">

                            <Link

                                to={`${empresa ? `/${empresa}` : ''}/mod/imports/pendientes`}

                                className="text-sm font-medium text-emerald-900 underline"

                            >

                                Ir a pendientes

                            </Link>

                        </div>

                    </div>

                )}

            </ImportadorLayout>

            {/* Modal de sugerencia de mapping */}
            <MappingSuggestModal
                file={mappingFile}
                open={mappingModalOpen}
                onClose={() => { setMappingModalOpen(false); setMappingTargetId(null); setMappingFile(null) }}
                onSaved={(saved) => {
                    setMappings((prev) => [saved, ...prev])
                    setDefaultMappingId(saved.id)
                    if (mappingTargetId) {
                        updateQueue(mappingTargetId, { mappingId: saved.id, info: `Mapping guardado: ${saved.name}` })
                        const target = queueRef.current.find((q) => q.id === mappingTargetId)
                        setMappingModalOpen(false)
                        setMappingTargetId(null)
                        setMappingFile(null)
                        if (target) {
                            // eslint-disable-next-line @typescript-eslint/no-floating-promises
                            processItem({ ...target, mappingId: saved.id })
                        }
                    }
                }}
            />

            {/* Toast no intrusivo cuando se guarda un archivo y hay más en cola */}
            {recentSaved && (
                <div className="fixed bottom-4 right-4 z-50 max-w-sm rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
                    <div className="flex items-start gap-3">
                        <div className="mt-1 h-2 w-2 rounded-full bg-emerald-500" />
                        <div className="flex-1">
                            <div className="text-sm font-medium text-slate-900">Archivo guardado</div>
                            {recentSaved.name && (
                                <div className="mt-0.5 truncate text-xs text-slate-600">{recentSaved.name}</div>
                            )}
                            <div className="mt-3 flex gap-2">
                                <button
                                    className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500"
                                    onClick={() => navigate(`preview?batch_id=${recentSaved.batchId}`)}
                                >
                                    Ver vista previa
                                </button>
                                <a
                                    className="rounded-md border border-blue-200 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
                                    href={`${basePath}/preview?batch_id=${recentSaved.batchId}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    Abrir en pestaña nueva
                                </a>
                                <button
                                    className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
                                    onClick={() => setRecentSaved(null)}
                                >
                                    Cerrar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

        </>

    )

}
