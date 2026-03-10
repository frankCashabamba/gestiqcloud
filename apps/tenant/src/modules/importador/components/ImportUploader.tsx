import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchImportBatch,
  fetchImportBatches,
  fetchRecipes,
  fetchSnapshots,
  runImportAsync,
  streamImportBatch,
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
  result?: { id: string; estado: string; tipo_documento_detectado?: string }
}
type PersistedFileEntry = Omit<FileEntry, 'file'>
type DirectoryInputProps = React.InputHTMLAttributes<HTMLInputElement> & { webkitdirectory?: string }

const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.tiff,.bmp,.xlsx,.xls,.csv,.xml,.txt'
const ACCEPTED_EXTENSIONS = new Set([
  '.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.xlsx', '.xls', '.csv', '.xml', '.txt',
])
const EXCEL_EXTENSIONS = new Set(['.xlsx', '.xls'])
const MAX_IMPORT_FILE_SIZE_MB = 16
const MAX_IMPORT_FILE_SIZE_BYTES = MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024
const TERMINAL_BATCH_STATES = new Set(['COMPLETED', 'FAILED', 'PARTIAL'])
const TERMINAL_DOCUMENT_STATES = new Set(['REVIEW', 'CONFIRMED', 'REJECTED'])
const UPLOADER_SESSION_KEY = 'importador.uploader.session.v1'

const FILE_ICONS: Record<string, string> = {
  '.pdf': 'PDF',
  '.jpg': 'IMG',
  '.jpeg': 'IMG',
  '.png': 'IMG',
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
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [selectedSnapshotId, setSelectedSnapshotId] = useState('')
  const [sessionHydrated, setSessionHydrated] = useState(false)
  const directoryInputProps: DirectoryInputProps = { webkitdirectory: 'true' }

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
        forceReprocess?: boolean
        selectedRecipeId?: string
        selectedSnapshotId?: string
      }
      if (saved.activeBatchId) setActiveBatchId(saved.activeBatchId)
      if (saved.activeBatch) setActiveBatch(saved.activeBatch)
      if (Array.isArray(saved.entries) && saved.entries.length > 0) {
        setEntries(saved.entries)
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
    if (!sessionHydrated || activeBatchId) return
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
          || item.estado === 'REJECTED'
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
      const trackedEntries = items.map((item) => {
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
      return ACCEPTED_EXTENSIONS.has(ext)
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
  }, [])

  const removeEntry = (idx: number) => {
    if (processing) return
    setEntries((prev) => prev.filter((_, i) => i !== idx))
  }

  const clearAll = () => {
    if (processing) return
    setEntries([])
    setError('')
    setActiveBatch(null)
    setActiveBatchId('')
    sessionStorage.removeItem(UPLOADER_SESSION_KEY)
  }

  const clearDone = () => setEntries((prev) => prev.filter((entry) => entry.status === 'pending'))

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

  const handleRun = async () => {
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
  }

  const pendingCount = entries.filter((entry) => entry.status === 'pending').length
  const totalCount = entries.length
  const activeCount = entries.filter((entry) => entry.status === 'processing').length
  const errorCount = entries.filter((entry) => entry.status === 'error').length
  const completedCount = entries.filter((entry) => entry.status === 'done').length
  const progressPct = totalCount > 0 ? Math.round(((completedCount + errorCount) / totalCount) * 100) : 0

  return (
    <>
      <style>{'@keyframes spin { to { transform: rotate(360deg) } }'}</style>
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1rem' }}>
        {activeBatch && (
          <div style={{ marginBottom: '1rem', padding: '0.85rem 1rem', borderRadius: 12, border: '1px solid #c7d2fe', background: 'linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%)', color: '#312e81' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700 }}>
                  {activeBatch.estado === 'COMPLETED' ? 'Ultimo lote completado' : 'Lote en segundo plano'}
                </div>
                <div style={{ fontSize: 12, color: '#4f46e5', marginTop: 4 }}>
                  {activeBatch.processing_items} procesando · {activeBatch.pending_items} en cola · {activeBatch.review_items + activeBatch.confirmed_items} resueltos · {activeBatch.failed_items} fallidos
                </div>
              </div>
              <div style={{ minWidth: 160 }}>
                <div style={{ fontSize: 12, color: '#6366f1', textAlign: 'right', marginBottom: 4 }}>
                  {activeBatch.progress_pct}% completado
                </div>
                <div style={{ height: 6, background: '#dbeafe', borderRadius: 999, overflow: 'hidden' }}>
                  <div style={{ width: `${activeBatch.progress_pct}%`, height: '100%', background: '#4f46e5' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {(['files', 'folder'] as ImportMode[]).map((itemMode) => (
              <button
                key={itemMode}
                onClick={() => setMode(itemMode)}
                disabled={processing}
                style={{
                  padding: '0.4rem 1rem',
                  borderRadius: 6,
                  border: '1px solid #d1d5db',
                  cursor: processing ? 'default' : 'pointer',
                  fontSize: 13,
                  background: mode === itemMode ? '#6366F1' : '#fff',
                  color: mode === itemMode ? '#fff' : '#374151',
                  fontWeight: mode === itemMode ? 600 : 400,
                }}
              >
                {itemMode === 'files' ? 'Archivos individuales' : 'Seleccionar carpeta'}
              </button>
            ))}
          </div>
          {entries.length > 0 && !processing && (
            <button
              onClick={clearAll}
              style={{ fontSize: 12, color: '#6b7280', border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}
            >
              Limpiar todo
            </button>
          )}
        </div>

        {mode === 'files' && (
          <div
            onDragOver={(e) => { e.preventDefault(); if (!processing) setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !processing && fileRef.current?.click()}
            style={{
              border: `2px dashed ${dragging ? '#6366F1' : '#d1d5db'}`,
              borderRadius: 12,
              padding: '1.5rem',
              textAlign: 'center',
              cursor: processing ? 'default' : 'pointer',
              background: dragging ? '#EEF2FF' : '#f9fafb',
              transition: 'all 0.2s',
            }}
          >
            <div style={{ fontSize: 36, marginBottom: '0.4rem' }}>DROP</div>
            <p style={{ fontSize: 14, fontWeight: 600, margin: '0 0 2px' }}>Arrastra archivos o haz clic para seleccionar</p>
            <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>PDF, JPG/PNG, Excel, CSV, XML, TXT</p>
            <input ref={fileRef} type="file" multiple accept={ACCEPTED} onChange={onFileChange} style={{ display: 'none' }} />
          </div>
        )}

        {mode === 'folder' && (
          <div
            onClick={() => !processing && folderRef.current?.click()}
            style={{
              border: '2px dashed #d1d5db',
              borderRadius: 12,
              padding: '1.5rem',
              textAlign: 'center',
              cursor: processing ? 'default' : 'pointer',
              background: '#f9fafb',
            }}
          >
            <div style={{ fontSize: 36, marginBottom: '0.4rem' }}>FOLDER</div>
            <p style={{ fontSize: 14, fontWeight: 600, margin: '0 0 2px' }}>Seleccionar carpeta</p>
            <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>Procesa todos los archivos soportados dentro</p>
            <input ref={folderRef} type="file" multiple onChange={onFolderChange} style={{ display: 'none' }} {...directoryInputProps} />
          </div>
        )}

        {entries.length > 0 && (
          <div style={{ marginTop: '0.75rem' }}>
            {activeCount > 0 && (
              <div style={{ marginBottom: '0.6rem', padding: '0.7rem 0.85rem', borderRadius: 10, border: '1px solid #c7d2fe', background: '#eef2ff', color: '#3730a3', fontSize: 13 }}>
                El sistema sigue trabajando en segundo plano. {activeCount} archivo{activeCount > 1 ? 's' : ''} en proceso.
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>
                {processing
                  ? `Encolando ${totalCount} documento${totalCount > 1 ? 's' : ''}...`
                  : activeCount > 0
                    ? `Seguimiento activo: ${completedCount + errorCount} de ${totalCount} resuelto${totalCount === 1 ? '' : 's'}`
                    : `${entries.length} archivo${entries.length > 1 ? 's' : ''} seleccionado${entries.length > 1 ? 's' : ''}`}
              </span>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                {completedCount > 0 && <span style={{ fontSize: 11, color: '#10B981', fontWeight: 600 }}>OK {completedCount} listo{completedCount > 1 ? 's' : ''}</span>}
                {errorCount > 0 && <span style={{ fontSize: 11, color: '#EF4444', fontWeight: 600 }}>ERR {errorCount} error{errorCount > 1 ? 'es' : ''}</span>}
                {!processing && completedCount > 0 && (
                  <button onClick={clearDone} style={{ fontSize: 11, color: '#6b7280', border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}>
                    Limpiar completados
                  </button>
                )}
              </div>
            </div>

            {(processing || activeCount > 0) && (
              <div style={{ height: 4, background: '#e5e7eb', borderRadius: 4, marginBottom: '0.5rem', overflow: 'hidden' }}>
                <div style={{ height: '100%', background: '#6366F1', borderRadius: 4, width: `${progressPct}%`, transition: 'width 0.3s ease' }} />
              </div>
            )}

            <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: 8 }}>
              {entries.map((entry, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.45rem 0.75rem',
                    background: entry.status === 'done' ? '#F0FDF4' : entry.status === 'error' ? '#FEF2F2' : entry.status === 'processing' ? '#EEF2FF' : '#fff',
                    borderBottom: i < entries.length - 1 ? '1px solid #f3f4f6' : 'none',
                    fontSize: 13,
                    transition: 'background 0.2s',
                  }}
                >
                  <span style={{ flexShrink: 0, width: 26, display: 'flex', justifyContent: 'center', fontSize: 10, color: '#64748b', fontWeight: 700 }}>
                    {entry.status === 'processing' ? <Spinner /> : entry.status === 'done' ? 'OK' : entry.status === 'error' ? 'ERR' : fileIcon(entry.name)}
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: entry.status === 'error' ? '#991B1B' : '#374151' }}>
                    {entry.name}
                  </span>
                  <span style={{ color: '#9ca3af', fontSize: 11, flexShrink: 0 }}>{fmtSize(entry.size)}</span>
                  {entry.status === 'error' && entry.errorMessage && (
                    <span style={{ color: '#b91c1c', fontSize: 11, flexShrink: 0 }}>
                      {entry.errorMessage}
                    </span>
                  )}
                  {entry.result?.tipo_documento_detectado && (
                    <span style={{ background: '#e0e7ff', color: '#3730a3', padding: '1px 7px', borderRadius: 10, fontSize: 11, flexShrink: 0 }}>
                      {entry.result.tipo_documento_detectado}
                    </span>
                  )}
                  {entry.status === 'done' && (entry.docId || entry.result?.id) && (
                    <button
                      onClick={() => navigate(documentPathBuilder(entry.docId || entry.result!.id))}
                      style={{ padding: '2px 8px', border: '1px solid #6366F1', borderRadius: 5, background: '#fff', color: '#6366F1', cursor: 'pointer', fontSize: 11, flexShrink: 0 }}
                    >
                      Ver
                    </button>
                  )}
                  {entry.status === 'pending' && !processing && (
                    <button onClick={() => removeEntry(i)} style={{ border: 'none', background: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 16, padding: 0, lineHeight: 1, flexShrink: 0 }}>
                      x
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 3 }}>Plantilla / Receta <span style={{ color: '#d1d5db' }}>opcional</span></div>
            <select
              value={selectedRecipeId}
              onChange={(e) => setSelectedRecipeId(e.target.value)}
              disabled={processing}
              style={{ padding: '0.35rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 190 }}
            >
              <option value="">Auto-detectar (recomendado)</option>
              {recipes.map((recipe) => <option key={recipe.id} value={recipe.id}>{recipe.name}</option>)}
            </select>
          </div>
          {selectedRecipeId && snapshots.length > 0 && (
            <select
              value={selectedSnapshotId}
              onChange={(e) => setSelectedSnapshotId(e.target.value)}
              disabled={processing}
              style={{ padding: '0.35rem 0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, minWidth: 170 }}
            >
              {snapshots.map((snapshot) => (
                <option key={snapshot.id} value={snapshot.id}>
                  {snapshot.version_tag || `v${new Date(snapshot.created_at).toLocaleDateString()}`}
                </option>
              ))}
            </select>
          )}
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.6rem', fontSize: 12, color: '#6b7280', cursor: processing ? 'default' : 'pointer', userSelect: 'none' }}>
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

        <button
          onClick={handleRun}
          disabled={pendingCount === 0 || processing}
          style={{
            marginTop: '0.75rem',
            width: '100%',
            padding: '0.7rem',
            background: pendingCount === 0 || processing ? '#e5e7eb' : '#6366F1',
            color: pendingCount === 0 || processing ? '#9ca3af' : '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 15,
            fontWeight: 700,
            cursor: pendingCount === 0 || processing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            transition: 'background 0.2s',
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
                : 'Importar documentos'}
        </button>

        {error && (
          <div style={{ marginTop: '0.5rem', padding: '0.6rem 0.75rem', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 8, color: '#991B1B', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>
    </>
  )
}
