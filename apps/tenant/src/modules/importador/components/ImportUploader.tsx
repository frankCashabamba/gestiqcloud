import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchFileSupportConfig,
  fetchImportBatch,
  fetchImportBatches,
  fetchRecipes,
  fetchSnapshots,
  runImportAsync,
  streamImportBatch,
  type FileSupportConfig,
  type ImportBatch,
  type ImportBatchItem,
  type Recipe,
  type RecipeSnapshot,
} from '../services'

type ImportMode = 'files' | 'folder'
type FileStatus = 'pending' | 'processing' | 'done' | 'error'
type FileEntry = {
  name: string
  size: number
  file?: File
  status: FileStatus
  docId?: string
  batchItemId?: string
  errorMessage?: string
  result?: {
    id: string
    estado: string
    tipo_documento_detectado?: string
    action?: 'CREATED' | 'REUSED' | 'REPROCESS'
    message?: string | null
  }
}
type PersistedFileEntry = Omit<FileEntry, 'file'>
type DirectoryInputProps = React.InputHTMLAttributes<HTMLInputElement> & { webkitdirectory?: string }

const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.heic,.heif,.xlsx,.xls,.csv,.xml,.txt'
const ACCEPTED_EXTENSIONS = new Set([
  '.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.heic', '.heif', '.xlsx', '.xls', '.csv', '.xml', '.txt',
])
const EXCEL_EXTENSIONS = new Set(['.xlsx', '.xls'])
const MAX_IMPORT_FILE_SIZE_MB = 16
const MAX_IMPORT_FILE_SIZE_BYTES = MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024
const TERMINAL_BATCH_STATES = new Set(['COMPLETED', 'FAILED', 'PARTIAL'])
const TERMINAL_DOCUMENT_STATES = new Set(['REVIEW', 'CONFIRMED', 'FAILED'])
const UPLOADER_SESSION_KEY = 'importador.uploader.session.v1'

const FILE_ICONS: Record<string, string> = {
  '.pdf': 'PDF',
  '.jpg': 'IMG',
  '.jpeg': 'IMG',
  '.png': 'IMG',
  '.heic': 'IMG',
  '.heif': 'IMG',
  '.xlsx': 'XLS',
  '.xls': 'XLS',
  '.csv': 'CSV',
  '.xml': 'XML',
  '.txt': 'TXT',
}

function fileIcon(name: string) {
  const ext = '.' + name.split('.').pop()?.toLowerCase()
  return FILE_ICONS[ext] || 'FILE'
}

function importActionCopy(action?: string | null) {
  switch (action) {
    case 'REUSED':
      return { label: 'Duplicado reutilizado', color: '#92400e', bg: '#fef3c7' }
    case 'REPROCESS':
      return { label: 'Reprocesado limpio', color: '#1d4ed8', bg: '#dbeafe' }
    case 'CREATED':
      return { label: 'Nuevo documento', color: '#166534', bg: '#dcfce7' }
    default:
      return null
  }
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function trackedEntryKey(entry: Pick<FileEntry, 'batchItemId' | 'docId' | 'name' | 'size'>) {
  if (entry.batchItemId) return `batch:${entry.batchItemId}`
  if (entry.docId) return `doc:${entry.docId}`
  return `file:${entry.name}:${entry.size}`
}

function statusFromBatchItem(item: ImportBatchItem): FileStatus {
  if (item.estado === 'PENDING' || item.estado === 'PROCESSING') return 'processing'
  if (item.estado === 'FAILED') return 'error'
  if (TERMINAL_DOCUMENT_STATES.has(item.estado)) return 'done'
  return 'processing'
}

function entryFromBatchItem(item: ImportBatchItem, existing?: FileEntry): FileEntry {
  return {
    name: item.nombre_archivo,
    size: item.tamanio_bytes,
    file: existing?.file,
    status: statusFromBatchItem(item),
    docId: item.documento_id || existing?.docId,
    batchItemId: item.id,
    errorMessage: item.estado === 'FAILED' ? (item.error_detalle || existing?.errorMessage) : undefined,
    result: existing?.result,
  }
}

function sameEntries(left: FileEntry[], right: FileEntry[]) {
  if (left.length !== right.length) return false
  for (let index = 0; index < left.length; index += 1) {
    const a = left[index]
    const b = right[index]
    if (
      a.name !== b.name
      || a.size !== b.size
      || a.status !== b.status
      || a.docId !== b.docId
      || a.batchItemId !== b.batchItemId
      || a.errorMessage !== b.errorMessage
      || a.result?.id !== b.result?.id
      || a.result?.estado !== b.result?.estado
      || a.result?.tipo_documento_detectado !== b.result?.tipo_documento_detectado
    ) {
      return false
    }
  }
  return true
}

function Spinner() {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 14,
        height: 14,
        border: '2px solid #c7d2fe',
        borderTopColor: '#6366F1',
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
        flexShrink: 0,
      }}
    />
  )
}

type ImportUploaderProps = {
  onImported?: () => void
  initialForceReprocess?: boolean
  documentPathBuilder?: (docId: string) => string
}

export default function ImportUploader({
  onImported,
  initialForceReprocess = false,
  documentPathBuilder = (docId) => `documents/${docId}`,
}: ImportUploaderProps) {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const folderRef = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<ImportMode>('files')
  const [dragging, setDragging] = useState(false)
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [activeBatchId, setActiveBatchId] = useState('')
  const [activeBatch, setActiveBatch] = useState<ImportBatch | null>(null)
  const [forceReprocess, setForceReprocess] = useState(initialForceReprocess)
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [snapshots, setSnapshots] = useState<RecipeSnapshot[]>([])
  const [fileSupport, setFileSupport] = useState<FileSupportConfig | null>(null)
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [selectedSnapshotId, setSelectedSnapshotId] = useState('')
  const [sessionHydrated, setSessionHydrated] = useState(false)
  const directoryInputProps: DirectoryInputProps = { webkitdirectory: 'true' }
  const clearedBatchIdsRef = useRef<Set<string>>(new Set())
  const dismissedEntryKeysRef = useRef<Set<string>>(new Set())
  const userClearedRef = useRef(false)
  const sessionHadDataRef = useRef(false)

  useEffect(() => {
    setForceReprocess(initialForceReprocess)
  }, [initialForceReprocess])

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(UPLOADER_SESSION_KEY)
      if (!raw) return
      const saved = JSON.parse(raw) as {
        activeBatchId?: string
        activeBatch?: ImportBatch | null
        entries?: PersistedFileEntry[]
        dismissedEntryKeys?: string[]
        forceReprocess?: boolean
        selectedRecipeId?: string
        selectedSnapshotId?: string
      }
      sessionHadDataRef.current = true
      if (saved.activeBatchId) setActiveBatchId(saved.activeBatchId)
      if (saved.activeBatch) setActiveBatch(saved.activeBatch)
      if (Array.isArray(saved.entries) && saved.entries.length > 0) {
        setEntries(saved.entries)
      }
      if (Array.isArray(saved.dismissedEntryKeys) && saved.dismissedEntryKeys.length > 0) {
        dismissedEntryKeysRef.current = new Set(saved.dismissedEntryKeys)
      }
      if (typeof saved.forceReprocess === 'boolean') setForceReprocess(saved.forceReprocess)
      if (typeof saved.selectedRecipeId === 'string') setSelectedRecipeId(saved.selectedRecipeId)
      if (typeof saved.selectedSnapshotId === 'string') setSelectedSnapshotId(saved.selectedSnapshotId)
    } catch {
      sessionStorage.removeItem(UPLOADER_SESSION_KEY)
    } finally {
      setSessionHydrated(true)
    }
  }, [])

  useEffect(() => {
    fetchRecipes().then(setRecipes).catch(() => {})
  }, [])

  useEffect(() => {
    fetchFileSupportConfig().then(setFileSupport).catch(() => {})
  }, [])

  const acceptedAttr = useMemo(
    () => (fileSupport?.accepted_extensions?.length ? fileSupport.accepted_extensions.join(',') : ACCEPTED),
    [fileSupport]
  )
  const acceptedExtensions = useMemo(
    () => new Set((fileSupport?.accepted_extensions?.length ? fileSupport.accepted_extensions : Array.from(ACCEPTED_EXTENSIONS)).map(value => value.toLowerCase())),
    [fileSupport]
  )

  useEffect(() => {
    if (!sessionHydrated || activeBatchId || userClearedRef.current || !sessionHadDataRef.current) return
    fetchImportBatches({ active_only: true, limit: 1 })
      .then((batches) => {
        if (!batches[0]) return
        setActiveBatchId(batches[0].id)
        setActiveBatch(batches[0])
      })
      .catch(() => {})
  }, [activeBatchId, sessionHydrated])

  useEffect(() => {
    if (!selectedRecipeId) {
      setSnapshots([])
      setSelectedSnapshotId('')
      return
    }
    fetchSnapshots(selectedRecipeId)
      .then((snaps) => {
        setSnapshots(snaps)
        setSelectedSnapshotId(snaps[0]?.id || '')
      })
      .catch(() => setSnapshots([]))
  }, [selectedRecipeId])

  useEffect(() => {
    if (!activeBatchId) return

    let cancelled = false
    let intervalId: number | null = null
    let closeStream: (() => void) | null = null
    let stuckTicks = 0
    let usingPolling = false

    const isBatchDone = (batch: ImportBatch) => {
      if (TERMINAL_BATCH_STATES.has(batch.estado)) return true
      const items = batch.items
      if (
        items?.length
        && items.every((item) =>
          TERMINAL_BATCH_STATES.has(item.estado)
          || item.estado === 'REVIEW'
          || item.estado === 'CONFIRMED'
          || item.estado === 'FAILED'
        )
      ) {
        return true
      }
      return false
    }

    const stopAll = () => {
      if (closeStream) {
        closeStream()
        closeStream = null
      }
      if (intervalId !== null) {
        window.clearInterval(intervalId)
        intervalId = null
      }
    }

    const applyBatch = (batch: ImportBatch) => {
      if (cancelled) return
      if (clearedBatchIdsRef.current.has(batch.id)) {
        stopAll()
        return
      }
      setActiveBatch(batch)
      if (isBatchDone(batch)) {
        stopAll()
      }
    }

    const loadBatch = () => {
      void fetchImportBatch(activeBatchId)
        .then((batch) => {
          applyBatch(batch)
          if (!usingPolling || isBatchDone(batch)) return
          stuckTicks++
          if (stuckTicks > 60 && intervalId !== null) {
            window.clearInterval(intervalId)
            intervalId = null
          }
        })
        .catch(() => {})
    }

    const startPolling = () => {
      if (cancelled || usingPolling) return
      usingPolling = true
      if (closeStream) {
        closeStream()
        closeStream = null
      }
      loadBatch()
      intervalId = window.setInterval(loadBatch, 5000)
    }

    try {
      closeStream = streamImportBatch(activeBatchId, {
        onMessage: (batch) => {
          applyBatch(batch)
        },
        onError: () => {
          startPolling()
        },
      })
    } catch {
      startPolling()
    }

    return () => {
      cancelled = true
      stopAll()
    }
  }, [activeBatchId])

  useEffect(() => {
    const items = activeBatch?.items
    if (!items?.length) return

    setEntries((prev) => {
      const prevByKey = new Map(prev.map((entry) => [trackedEntryKey(entry), entry]))
      const localPending = prev.filter((entry) => !entry.batchItemId && !entry.docId && entry.file)
      const trackedEntries = items.filter((item) => {
        const batchKey = `batch:${item.id}`
        const docKey = item.documento_id ? `doc:${item.documento_id}` : ''
        const fileKey = `file:${item.nombre_archivo}:${item.tamanio_bytes}`
        return !dismissedEntryKeysRef.current.has(batchKey)
          && (!docKey || !dismissedEntryKeysRef.current.has(docKey))
          && !dismissedEntryKeysRef.current.has(fileKey)
      }).map((item) => {
        const existing = prevByKey.get(`batch:${item.id}`)
          || (item.documento_id ? prevByKey.get(`doc:${item.documento_id}`) : undefined)
          || prevByKey.get(`file:${item.nombre_archivo}:${item.tamanio_bytes}`)
        return entryFromBatchItem(item, existing)
      })
      const next = [...localPending, ...trackedEntries]
      return sameEntries(prev, next) ? prev : next
    })
  }, [activeBatch])

  useEffect(() => {
    if (!sessionHydrated) return

    const recoverableEntries = entries
      .filter((entry) => entry.batchItemId || entry.docId || entry.result?.id)
      .map(({ file: _file, ...entry }) => entry)

    if (!activeBatchId && !activeBatch && recoverableEntries.length === 0) {
      sessionStorage.removeItem(UPLOADER_SESSION_KEY)
      return
    }

    sessionStorage.setItem(
      UPLOADER_SESSION_KEY,
      JSON.stringify({
        activeBatchId,
        activeBatch,
        entries: recoverableEntries,
        dismissedEntryKeys: Array.from(dismissedEntryKeysRef.current),
        forceReprocess,
        selectedRecipeId,
        selectedSnapshotId,
      }),
    )
  }, [activeBatch, activeBatchId, entries, forceReprocess, selectedRecipeId, selectedSnapshotId, sessionHydrated])

  const addFiles = useCallback((fileList: FileList | File[]) => {
    const incoming = Array.from(fileList || []).filter((file) => {
      if (!file || file.size < 0) return false
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      return acceptedExtensions.has(ext)
    })
    if (!incoming.length) return
    setEntries((prev) => {
      const existing = new Set(prev.map((entry) => `${entry.name}-${entry.size}`))
      const merged = [...prev]
      incoming.forEach((file) => {
        if (!existing.has(`${file.name}-${file.size}`)) {
          merged.push({ file, name: file.name, size: file.size, status: 'pending' })
        }
      })
      return merged
    })
  }, [acceptedExtensions])

  const dismissEntry = (entry: FileEntry) => {
    dismissedEntryKeysRef.current.add(trackedEntryKey(entry))
    setEntries((prev) => prev.filter((current) => trackedEntryKey(current) !== trackedEntryKey(entry)))
  }

  const clearAll = () => {
    if (processing) return
    const batchIdToClear = activeBatchId || activeBatch?.id
    userClearedRef.current = true
    if (batchIdToClear) {
      clearedBatchIdsRef.current.add(batchIdToClear)
    }
    const dismissedEntryKeys = new Set(dismissedEntryKeysRef.current)
    activeBatch?.items?.forEach((item) => {
      dismissedEntryKeys.add(`batch:${item.id}`)
      if (item.documento_id) dismissedEntryKeys.add(`doc:${item.documento_id}`)
      dismissedEntryKeys.add(`file:${item.nombre_archivo}:${item.tamanio_bytes}`)
    })
    dismissedEntryKeysRef.current = dismissedEntryKeys
    setEntries([])
    setError('')
    setActiveBatch(null)
    setActiveBatchId('')
    sessionStorage.removeItem(UPLOADER_SESSION_KEY)
  }

  const clearDone = () => {
    setEntries((prev) => {
      const toRemove = prev.filter((entry) => entry.status === 'done' || entry.status === 'error')
      toRemove.forEach((entry) => {
        dismissedEntryKeysRef.current.add(trackedEntryKey(entry))
      })
      return prev.filter((entry) => entry.status !== 'done' && entry.status !== 'error')
    })
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }, [addFiles])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files)
    e.target.value = ''
  }

  const onFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files)
    e.target.value = ''
  }

  const handleRun = useCallback(async () => {
    const pending = entries.filter((entry): entry is FileEntry & { file: File } =>
      entry.status === 'pending' && Boolean(entry.file)
    )
    if (!pending.length) return

    const isExcel = (file: File) => EXCEL_EXTENSIONS.has('.' + file.name.split('.').pop()?.toLowerCase())
    const oversized = pending.filter((entry) => !isExcel(entry.file) && entry.file.size > MAX_IMPORT_FILE_SIZE_BYTES)
    const uploadable = pending.filter((entry) => isExcel(entry.file) || entry.file.size <= MAX_IMPORT_FILE_SIZE_BYTES)

    if (oversized.length > 0) {
      setEntries((prev) => prev.map((entry) => {
        if (!oversized.some((item) => item.file === entry.file)) return entry
        return {
          ...entry,
          status: 'error',
          errorMessage: `Excede el limite de ${MAX_IMPORT_FILE_SIZE_MB} MB (${fmtSize(entry.size)}).`,
        }
      }))
      setError(
        oversized.length === 1
          ? `Archivo '${oversized[0].name}' excede el limite de ${MAX_IMPORT_FILE_SIZE_MB} MB (${fmtSize(oversized[0].size)}).`
          : `${oversized.length} archivos exceden el limite de ${MAX_IMPORT_FILE_SIZE_MB} MB y se omitieron de esta importacion.`,
      )
    }

    if (!uploadable.length) return

    setProcessing(true)
    if (!oversized.length) setError('')

    setEntries((prev) => prev.map((entry) =>
      uploadable.some((item) => item.file === entry.file)
        ? { ...entry, status: 'processing', errorMessage: undefined }
        : entry
    ))

    try {
      const asyncResults = await runImportAsync(
        uploadable.map((entry) => entry.file),
        { force: forceReprocess, recipe_snapshot_id: selectedSnapshotId || undefined },
      )

      const batchId = asyncResults[0]?.batch_id
      if (batchId) setActiveBatchId(batchId)

      setEntries((prev) => prev.map((entry) => {
        const uploadIndex = uploadable.findIndex((item) => item.file === entry.file)
        const asyncResult = uploadIndex >= 0 ? asyncResults[uploadIndex] : undefined
        if (!asyncResult) {
          return entry.status === 'processing' ? { ...entry, status: 'error' } : entry
        }
        if (asyncResult.estado === 'FAILED') {
          return {
            ...entry,
            status: 'error',
            docId: asyncResult.id,
            batchItemId: asyncResult.batch_item_id,
            result: asyncResult,
          }
        }
        if (asyncResult.estado !== 'PENDING' && asyncResult.estado !== 'PROCESSING') {
          return {
            ...entry,
            status: 'done',
            docId: asyncResult.id,
            batchItemId: asyncResult.batch_item_id,
            result: asyncResult,
          }
        }
        return {
          ...entry,
          status: 'processing',
          docId: asyncResult.id,
          batchItemId: asyncResult.batch_item_id,
          result: asyncResult,
        }
      }))
      onImported?.()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al encolar archivos')
      setEntries((prev) => prev.map((entry) =>
        entry.status === 'processing' ? { ...entry, status: 'pending' } : entry
      ))
    } finally {
      setProcessing(false)
    }
  }, [entries, forceReprocess, selectedSnapshotId, onImported])

  const { pendingCount, totalCount, activeCount, errorCount, completedCount, progressPct, reviewEntries, queueEntries, errorEntries } = useMemo(() => {
    const reviewEntries = entries.filter((entry) => entry.status === 'done')
    const queueEntries = entries.filter((entry) => entry.status === 'processing' || entry.status === 'pending')
    const errorEntries = entries.filter((entry) => entry.status === 'error')
    const pendingCount = entries.filter((entry) => entry.status === 'pending').length
    const totalCount = entries.length
    const activeCount = queueEntries.filter((entry) => entry.status === 'processing').length
    const errorCount = errorEntries.length
    const completedCount = reviewEntries.length
    const progressPct = totalCount > 0 ? Math.round(((completedCount + errorCount) / totalCount) * 100) : 0
    return { pendingCount, totalCount, activeCount, errorCount, completedCount, progressPct, reviewEntries, queueEntries, errorEntries }
  }, [entries])
  const statusChips = useMemo(() => [
    { label: 'Por revisar', value: reviewEntries.length, color: '#10B981' },
    { label: 'En curso', value: queueEntries.length, color: '#4F46E5' },
    { label: 'Errores', value: errorEntries.length, color: '#EF4444' },
  ], [reviewEntries.length, queueEntries.length, errorEntries.length])
  const headerTitle = processing
    ? `Encolando ${totalCount} documento${totalCount > 1 ? 's' : ''}...`
    : activeCount > 0
      ? `Procesando ${activeCount} archivo${activeCount > 1 ? 's' : ''} en segundo plano`
      : `${entries.length} archivo${entries.length > 1 ? 's' : ''} en esta bandeja`
  const headerMeta = activeBatch
    ? `${activeBatch.review_items + activeBatch.confirmed_items} resueltos · ${activeBatch.pending_items} en cola · ${activeBatch.failed_items} fallidos`
    : `Los documentos abiertos con Ver salen automaticamente de esta lista.`

  return (
    <>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg) } }

        @media (max-width: 960px) {
          .import-uploader {
            padding: 1rem !important;
            border-radius: 20px !important;
          }
          .import-uploader__dropzone-title {
            font-size: 26px !important;
          }
          .import-uploader__dropzone-subtitle {
            font-size: 14px !important;
          }
          .import-uploader__status-title {
            font-size: 16px !important;
          }
        }

        @media (max-width: 640px) {
          .import-uploader {
            padding: 0.85rem !important;
            border-radius: 18px !important;
          }
          .import-uploader__top {
            gap: 0.85rem !important;
            margin-bottom: 0.85rem !important;
          }
          .import-uploader__tabs {
            width: 100%;
          }
          .import-uploader__tabs button {
            flex: 1;
          }
          .import-uploader__dropzone {
            padding: 1.3rem 0.95rem !important;
            border-radius: 20px !important;
          }
          .import-uploader__dropzone-title {
            font-size: 23px !important;
          }
          .import-uploader__dropzone-subtitle {
            font-size: 13px !important;
          }
          .import-uploader__panel {
            padding: 0.85rem !important;
          }
          .import-uploader__status {
            padding: 0.85rem !important;
          }
          .import-uploader__status-progress {
            min-width: 100% !important;
            max-width: none !important;
          }
          .import-uploader__section {
            padding: 0.8rem !important;
          }
          .import-uploader__entry {
            grid-template-columns: auto minmax(0, 1fr) !important;
            gap: 0.75rem !important;
            padding: 0.75rem !important;
          }
          .import-uploader__entry-actions {
            grid-column: 1 / -1;
            justify-content: flex-start !important;
            padding-left: 3rem;
            margin-top: -0.15rem;
          }
          .import-uploader__controls {
            flex-direction: column;
            align-items: stretch !important;
            padding: 0.75rem !important;
          }
          .import-uploader__controls > * {
            width: 100%;
          }
          .import-uploader__select {
            min-width: 0 !important;
            width: 100%;
          }
          .import-uploader__checkbox {
            width: 100%;
          }
          .import-uploader__cta {
            min-height: 52px !important;
            font-size: 14px !important;
          }
        }
      `}</style>
      <div className="import-uploader" style={{ background: 'linear-gradient(180deg, #ffffff 0%, #f8faff 100%)', border: '1px solid #e5e7eb', borderRadius: 24, padding: '1.15rem', boxShadow: '0 18px 40px rgba(15, 23, 42, 0.06)', position: 'relative', overflow: 'hidden' }}>
        <div className="import-uploader__top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#6366f1', marginBottom: 4 }}>
              Preparar importacion
            </div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>
              {entries.length > 0 ? 'Sigue cargando documentos a esta bandeja' : 'Sube documentos sueltos o una carpeta completa'}
            </div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
              {entries.length > 0 ? 'Puedes seguir agregando archivos mientras el sistema procesa en segundo plano.' : 'Arrastra archivos, haz clic para seleccionarlos y lanza la importacion cuando este todo listo.'}
            </div>
          </div>
          <div className="import-uploader__tabs" style={{ display: 'inline-flex', gap: '0.55rem', padding: '0.35rem', borderRadius: 16, border: '1px solid #dbeafe', background: 'linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%)' }}>
            {(['files', 'folder'] as ImportMode[]).map((itemMode) => (
              <button
                key={itemMode}
                onClick={() => setMode(itemMode)}
                disabled={processing}
                style={{
                  padding: '0.55rem 1rem',
                  borderRadius: 12,
                  border: '1px solid transparent',
                  cursor: processing ? 'default' : 'pointer',
                  fontSize: 13,
                  background: mode === itemMode ? 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)' : '#fff',
                  color: mode === itemMode ? '#fff' : '#374151',
                  fontWeight: mode === itemMode ? 700 : 500,
                  boxShadow: mode === itemMode ? '0 10px 20px rgba(79, 70, 229, 0.22)' : '0 1px 2px rgba(15, 23, 42, 0.05)',
                }}
              >
                {itemMode === 'files' ? 'Archivos individuales' : 'Seleccionar carpeta'}
              </button>
            ))}
          </div>
          {entries.length > 0 && !processing && (
            <button
              onClick={clearAll}
              style={{ fontSize: 12, color: '#6b7280', border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', padding: '0.45rem 0.8rem', borderRadius: 10, fontWeight: 700 }}
            >
              Limpiar todo
            </button>
          )}
        </div>

        {mode === 'files' && (
          <div
            className="import-uploader__dropzone"
            onDragOver={(e) => { e.preventDefault(); if (!processing) setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !processing && fileRef.current?.click()}
            style={{
              border: `2px dashed ${dragging ? '#6366F1' : '#d1d5db'}`,
              borderRadius: 24,
              padding: '1.7rem 1.4rem',
              textAlign: 'center',
              cursor: processing ? 'default' : 'pointer',
              background: dragging
                ? 'radial-gradient(circle at top, rgba(99, 102, 241, 0.18) 0%, rgba(255,255,255,0.96) 55%), linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%)'
                : 'radial-gradient(circle at top, rgba(99, 102, 241, 0.08) 0%, rgba(255,255,255,0.98) 52%), linear-gradient(180deg, #fcfcff 0%, #f8fafc 100%)',
              transition: 'all 0.2s',
              boxShadow: dragging ? 'inset 0 0 0 1px rgba(99, 102, 241, 0.14)' : 'inset 0 0 0 1px rgba(255,255,255,0.6)',
            }}
          >
            <div style={{ width: 54, height: 54, margin: '0 auto 0.85rem', borderRadius: 18, background: dragging ? '#6366F1' : 'linear-gradient(180deg, #E0E7FF 0%, #C7D2FE 100%)', color: dragging ? '#fff' : '#4F46E5', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700, boxShadow: '0 14px 26px rgba(99, 102, 241, 0.16)' }}>
              +
            </div>
            <p style={{ fontSize: 13, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 0.45rem', color: '#6366f1' }}>Zona de carga</p>
            <p className="import-uploader__dropzone-title" style={{ fontSize: 30, fontWeight: 800, lineHeight: 1.1, margin: '0 0 0.35rem', color: '#111827' }}>Arrastra tus archivos aqui</p>
            <p className="import-uploader__dropzone-subtitle" style={{ fontSize: 15, color: '#475569', margin: '0 0 1rem' }}>o haz clic para seleccionarlos manualmente</p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
              {['PDF', 'JPG/PNG', 'HEIC', 'Excel', 'CSV', 'XML', 'TXT'].map((label) => (
                <span key={label} style={{ padding: '0.22rem 0.55rem', borderRadius: 999, background: '#fff', border: '1px solid #e5e7eb', color: '#64748b', fontSize: 11, fontWeight: 700 }}>
                  {label}
                </span>
              ))}
            </div>
            <div style={{ marginTop: '0.9rem', fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>
              El sistema clasifica y prepara los documentos automaticamente.
            </div>
            <input ref={fileRef} type="file" multiple accept={acceptedAttr} onChange={onFileChange} style={{ display: 'none' }} />
          </div>
        )}

        {mode === 'folder' && (
          <div
            className="import-uploader__dropzone"
            onClick={() => !processing && folderRef.current?.click()}
            style={{
              border: '2px dashed #d1d5db',
              borderRadius: 24,
              padding: '1.7rem 1.4rem',
              textAlign: 'center',
              cursor: processing ? 'default' : 'pointer',
              background: 'radial-gradient(circle at top, rgba(14, 165, 233, 0.09) 0%, rgba(255,255,255,0.98) 52%), linear-gradient(180deg, #fcfcff 0%, #f8fafc 100%)',
            }}
          >
            <div style={{ width: 54, height: 54, margin: '0 auto 0.85rem', borderRadius: 18, background: 'linear-gradient(180deg, #E0F2FE 0%, #BAE6FD 100%)', color: '#0369A1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700, boxShadow: '0 14px 26px rgba(14, 165, 233, 0.14)' }}>
              F
            </div>
            <p style={{ fontSize: 13, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 0.45rem', color: '#0284c7' }}>Carga por carpeta</p>
            <p className="import-uploader__dropzone-title" style={{ fontSize: 30, fontWeight: 800, lineHeight: 1.1, margin: '0 0 0.35rem', color: '#111827' }}>Importacion por carpeta</p>
            <p className="import-uploader__dropzone-subtitle" style={{ fontSize: 15, color: '#475569', margin: 0 }}>Procesa todos los archivos compatibles contenidos en una misma carpeta</p>
            <input ref={folderRef} type="file" multiple onChange={onFolderChange} style={{ display: 'none' }} {...directoryInputProps} />
          </div>
        )}

        {entries.length > 0 && (
          <div className="import-uploader__panel" style={{ marginTop: '1rem', border: '1px solid #E5E7EB', borderRadius: 18, padding: '1rem', background: 'linear-gradient(180deg, #ffffff 0%, #fafbff 100%)' }}>
            <div className="import-uploader__status" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem', padding: '0.95rem 1rem', borderRadius: 16, border: '1px solid #c7d2fe', background: 'linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%)' }}>
              <div style={{ flex: 1, minWidth: 260 }}>
                <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#6366f1', marginBottom: 4 }}>
                  Estado actual
                </div>
                <div className="import-uploader__status-title" style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>
                  {headerTitle}
                </div>
                <div style={{ marginTop: 4, fontSize: 12, color: '#4f46e5' }}>
                  {headerMeta}
                </div>
                <div style={{ display: 'flex', gap: '0.55rem', flexWrap: 'wrap', marginTop: '0.8rem' }}>
                  {statusChips.map((item) => (
                    <div key={item.label} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', padding: '0.4rem 0.65rem', borderRadius: 999, background: '#fff', border: '1px solid rgba(148, 163, 184, 0.22)' }}>
                      <span style={{ width: 8, height: 8, borderRadius: 999, background: item.color, flexShrink: 0 }} />
                      <span style={{ fontSize: 11, color: item.color, fontWeight: 800 }}>{item.value}</span>
                      <span style={{ fontSize: 12, color: '#64748b', fontWeight: 600 }}>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="import-uploader__status-progress" style={{ minWidth: 220, maxWidth: 280, flex: '0 0 auto' }}>
                {(processing || activeCount > 0 || completedCount > 0 || errorCount > 0 || activeBatch) && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12, color: '#6366f1', fontWeight: 700 }}>
                      <span>{activeBatch?.estado === 'COMPLETED' ? 'Lote completado' : 'Progreso visible'}</span>
                      <span>{activeBatch?.progress_pct ?? progressPct}%</span>
                    </div>
                    <div style={{ height: 8, background: 'rgba(79, 70, 229, 0.12)', borderRadius: 999, overflow: 'hidden' }}>
                      <div style={{ height: '100%', background: 'linear-gradient(90deg, #6366F1 0%, #22C55E 100%)', borderRadius: 999, width: `${activeBatch?.progress_pct ?? progressPct}%`, transition: 'width 0.3s ease' }} />
                    </div>
                  </>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                {!processing && completedCount > 0 && (
                  <button onClick={clearDone} style={{ fontSize: 12, color: '#6b7280', border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', padding: '0.42rem 0.75rem', borderRadius: 10, fontWeight: 700 }}>
                    Ocultar revisados
                  </button>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gap: '0.9rem' }}>
              {[
                { key: 'review', title: 'Por revisar', subtitle: 'Documentos listos para abrir y retirar de la bandeja', entries: reviewEntries },
                { key: 'queue', title: 'En curso', subtitle: 'Archivos procesandose o pendientes de envio', entries: queueEntries },
                { key: 'errors', title: 'Errores', subtitle: 'Archivos que requieren una nueva subida o revision', entries: errorEntries },
              ].filter((section) => section.entries.length > 0).map((section) => (
                <div className="import-uploader__section" key={section.key} style={{ border: '1px solid #E5E7EB', borderRadius: 18, background: '#fff', padding: '0.9rem', boxShadow: '0 10px 22px rgba(15, 23, 42, 0.03)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'baseline', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: '#0f172a' }}>{section.title}</div>
                      <div style={{ marginTop: 3, fontSize: 12, color: '#64748b' }}>{section.subtitle}</div>
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 700 }}>
                      {section.entries.length} archivo{section.entries.length > 1 ? 's' : ''}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gap: '0.7rem', maxHeight: 280, overflowY: 'auto', paddingRight: 2 }}>
                    {section.entries.map((entry) => {
                      const actionCopy = importActionCopy(entry.result?.action)
                      const tone = entry.status === 'done'
                        ? { bg: '#f0fdf4', border: '#bbf7d0', badge: '#dcfce7', color: '#166534' }
                        : entry.status === 'error'
                          ? { bg: '#fef2f2', border: '#fecaca', badge: '#fee2e2', color: '#991b1b' }
                          : entry.status === 'pending'
                            ? { bg: '#fafaf9', border: '#e7e5e4', badge: '#f5f5f4', color: '#57534e' }
                            : { bg: '#eef2ff', border: '#c7d2fe', badge: '#e0e7ff', color: '#3730a3' }
                      return (
                        <div
                          className="import-uploader__entry"
                          key={trackedEntryKey(entry)}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'auto minmax(0, 1fr) auto',
                            gap: '0.85rem',
                            alignItems: 'center',
                            padding: '0.85rem 0.95rem',
                            border: `1px solid ${tone.border}`,
                            borderRadius: 14,
                            background: tone.bg,
                          }}
                        >
                          <div style={{ width: 38, height: 38, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', background: tone.badge, color: tone.color, fontSize: 11, fontWeight: 800 }}>
                            {entry.status === 'processing' ? <Spinner /> : entry.status === 'done' ? 'OK' : entry.status === 'error' ? 'ERR' : fileIcon(entry.name)}
                          </div>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ display: 'flex', gap: '0.45rem', alignItems: 'center', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {entry.name}
                              </span>
                              <span style={{ padding: '0.15rem 0.45rem', borderRadius: 999, background: tone.badge, color: tone.color, fontSize: 10, fontWeight: 700 }}>
                                {entry.status === 'done' ? 'Listo para revisar' : entry.status === 'error' ? 'Requiere atencion' : entry.status === 'pending' ? 'Listo para enviar' : 'Procesando'}
                              </span>
                              {entry.result?.tipo_documento_detectado && (
                                <span style={{ padding: '0.15rem 0.45rem', borderRadius: 999, background: '#fff', color: '#475569', border: '1px solid rgba(148, 163, 184, 0.35)', fontSize: 10, fontWeight: 700 }}>
                                  {entry.result.tipo_documento_detectado}
                                </span>
                              )}
                              {actionCopy && (
                                <span
                                  style={{
                                    padding: '0.15rem 0.45rem',
                                    borderRadius: 999,
                                    background: actionCopy.bg,
                                    color: actionCopy.color,
                                    fontSize: 10,
                                    fontWeight: 700,
                                  }}
                                >
                                  {actionCopy.label}
                                </span>
                              )}
                            </div>
                            <div style={{ marginTop: 4, display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', fontSize: 11, color: '#64748b' }}>
                              <span>{fmtSize(entry.size)}</span>
                              {entry.status === 'processing' && <span style={{ color: tone.color }}>Trabajo en segundo plano</span>}
                              {entry.status === 'pending' && <span style={{ color: tone.color }}>Pendiente de envio</span>}
                              {entry.status === 'error' && entry.errorMessage && <span style={{ color: tone.color, fontWeight: 600 }}>{entry.errorMessage}</span>}
                              {entry.status === 'done' && <span style={{ color: tone.color }}>Se retira de la bandeja al abrirlo</span>}
                            </div>
                            {entry.result?.message && (
                              <div style={{ marginTop: 6, fontSize: 11, color: '#475569' }}>
                                {entry.result.message}
                              </div>
                            )}
                          </div>
                          <div className="import-uploader__entry-actions" style={{ display: 'flex', gap: '0.45rem', alignItems: 'center', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                            {entry.status === 'done' && (entry.docId || entry.result?.id) && (
                              <button
                                onClick={() => {
                                  dismissEntry(entry)
                                  navigate(documentPathBuilder(entry.docId || entry.result!.id))
                                }}
                                style={{ padding: '0.42rem 0.8rem', border: '1px solid #4F46E5', borderRadius: 10, background: '#4F46E5', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 700 }}
                              >
                                Ver
                              </button>
                            )}
                            {entry.status === 'pending' && !processing && (
                              <button
                                onClick={() => setEntries((prev) => prev.filter((current) => trackedEntryKey(current) !== trackedEntryKey(entry)))}
                                style={{ padding: '0.42rem 0.7rem', border: '1px solid #D6D3D1', borderRadius: 10, background: '#fff', color: '#78716C', cursor: 'pointer', fontSize: 12, fontWeight: 700 }}
                              >
                                Quitar
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="import-uploader__controls" style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap', padding: '0.85rem', border: '1px solid #e5e7eb', borderRadius: 18, background: 'linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(248,250,252,0.96) 100%)' }}>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 5, fontWeight: 700 }}>Plantilla / Receta <span style={{ color: '#d1d5db' }}>opcional</span></div>
            <select
              className="import-uploader__select"
              value={selectedRecipeId}
              onChange={(e) => setSelectedRecipeId(e.target.value)}
              disabled={processing}
              style={{ padding: '0.55rem 0.7rem', border: '1px solid #d1d5db', borderRadius: 12, fontSize: 13, minWidth: 220, background: '#fff' }}
            >
              <option value="">Auto-detectar (recomendado)</option>
              {recipes.map((recipe) => <option key={recipe.id} value={recipe.id}>{recipe.name}</option>)}
            </select>
          </div>
          {selectedRecipeId && snapshots.length > 0 && (
            <select
              className="import-uploader__select"
              value={selectedSnapshotId}
              onChange={(e) => setSelectedSnapshotId(e.target.value)}
              disabled={processing}
              style={{ padding: '0.55rem 0.7rem', border: '1px solid #d1d5db', borderRadius: 12, fontSize: 13, minWidth: 190, background: '#fff' }}
            >
              {snapshots.map((snapshot) => (
                <option key={snapshot.id} value={snapshot.id}>
                  {snapshot.version_tag || `v${new Date(snapshot.created_at).toLocaleDateString()}`}
                </option>
              ))}
            </select>
          )}
          <label className="import-uploader__checkbox" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.55rem', fontSize: 12, color: '#6b7280', cursor: processing ? 'default' : 'pointer', userSelect: 'none', padding: '0.72rem 0.85rem', border: '1px solid #e5e7eb', borderRadius: 14, background: '#fff', minHeight: 46 }}>
            <input
              type="checkbox"
              checked={forceReprocess}
              disabled={processing}
              onChange={(e) => setForceReprocess(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            Reimportacion limpia
            <span style={{ color: '#d1d5db' }}>(omite dedupe)</span>
          </label>
        </div>

        <button
          className="import-uploader__cta"
          onClick={handleRun}
          disabled={pendingCount === 0 || processing}
          style={{
            marginTop: '1rem',
            width: '100%',
            padding: '0.88rem 1rem',
            background: pendingCount === 0 || processing ? 'linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)' : 'linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)',
            color: pendingCount === 0 || processing ? '#94a3b8' : '#fff',
            border: pendingCount === 0 || processing ? '1px dashed #cbd5e1' : 'none',
            borderRadius: 16,
            fontSize: 15,
            fontWeight: 800,
            cursor: pendingCount === 0 || processing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            transition: 'background 0.2s',
            boxShadow: pendingCount === 0 || processing ? 'none' : '0 18px 30px rgba(79, 70, 229, 0.22)',
            minHeight: 58,
          }}
        >
          {processing ? (
            <>
              <Spinner />
              Encolando {totalCount} documento{totalCount > 1 ? 's' : ''}...
            </>
          ) : activeCount > 0
            ? `Procesando en segundo plano: ${completedCount + errorCount} de ${totalCount}`
            : pendingCount > 0
              ? `Importar ${pendingCount} documento${pendingCount > 1 ? 's' : ''}`
              : entries.length > 0
                ? 'Todo procesado - agrega mas archivos'
                : 'Selecciona archivos para comenzar'}
        </button>

        {error && (
          <div style={{ marginTop: '0.75rem', padding: '0.8rem 0.9rem', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 12, color: '#991B1B', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>
    </>
  )
}
