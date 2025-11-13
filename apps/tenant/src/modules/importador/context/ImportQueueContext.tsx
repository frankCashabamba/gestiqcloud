import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '../../../auth/AuthContext'
import { procesarDocumento, pollOcrJob } from '../services'
import { parseExcelFile } from '../services/parseExcelFile'
import { uploadExcelViaChunks, createBatch, ingestBatch, type ImportMapping } from '../services/importsApi'
import { detectarTipoDocumento } from '../utils/detectarTipoDocumento'
import { guardarPendiente, type DatosImportadosCreate } from '../services'

const OCR_RECHECK_DELAY_MS = Number(import.meta.env.VITE_IMPORTS_JOB_RECHECK_INTERVAL ?? 2000)

type Row = Record<string, string>
type ItemStatus = 'pending' | 'processing' | 'ready' | 'saving' | 'saved' | 'duplicate' | 'error'

export type QueueItem = {
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

type ImportQueueContextType = {
  queue: QueueItem[]
  addToQueue: (files: FileList | File[]) => void
  removeFromQueue: (id: string) => void
  clearQueue: () => void
  isProcessing: boolean
  processingCount: number
}

const ImportQueueContext = createContext<ImportQueueContextType | undefined>(undefined)

const STORAGE_KEY = 'importador_queue_state'

function parseCSV(text: string): { headers: string[]; rows: Row[] } {
  const lines = text.split(/\r?\n/).filter(Boolean)
  if (lines.length === 0) return { headers: [], rows: [] }
  const headers = lines[0].split(',').map((h) => h.trim())
  const rows = lines.slice(1).map((line) => {
    const cols = line.split(',')
    const row: Row = {}
    headers.forEach((header, idx) => {
      row[header] = (cols[idx] || '').trim()
    })
    return row
  })
  return { headers, rows }
}

export function ImportQueueProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth() as { token: string | null }
  const [queue, setQueue] = useState<QueueItem[]>([])
  const queueRef = useRef<QueueItem[]>([])
  const processingRef = useRef<Set<string>>(new Set())
  const [isProcessing, setIsProcessing] = useState(false)

  // Persistir cola en localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Solo restaurar items que no estén completados
        const toRestore = parsed.filter((item: QueueItem) => 
          item.status !== 'saved' && item.status !== 'duplicate'
        )
        if (toRestore.length > 0) {
          setQueue(toRestore)
        }
      } catch (e) {
        console.error('Error al restaurar cola:', e)
      }
    }
  }, [])

  useEffect(() => {
    queueRef.current = queue
    // Guardar en localStorage (sin los objetos File por seguridad)
    const toSave = queue.map(item => ({
      ...item,
      file: undefined, // No persistir el objeto File
    }))
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  }, [queue])

  const updateQueue = useCallback((id: string, updates: Partial<QueueItem>) => {
    setQueue((prev) => prev.map((item) => (item.id === id ? { ...item, ...updates } : item)))
  }, [])

  const processItem = useCallback(
    async (item: QueueItem, mappings?: ImportMapping[], defaultMappingId?: string) => {
      if (processingRef.current.has(item.id)) return
      processingRef.current.add(item.id)

      updateQueue(item.id, { status: 'processing', error: null })

      const isCSV = item.name.toLowerCase().endsWith('.csv')
      const isExcel = item.name.toLowerCase().endsWith('.xlsx') || item.name.toLowerCase().endsWith('.xls')
      const isDoc = item.type.includes('pdf') || item.type.includes('image')

      try {
        if (isCSV) {
          const textContent = await item.file.text()
          const { headers, rows } = parseCSV(textContent)
          const docType = detectarTipoDocumento(headers)
          updateQueue(item.id, { status: 'ready', headers, rows, docType, error: null, info: null })
          await saveItem(item, headers, rows, docType)
          return
        }

        if (isExcel) {
          let effectiveMappingId = item.mappingId || defaultMappingId || ''
          if (!effectiveMappingId && mappings && mappings.length) {
            const matched = mappings.find((m) => {
              try {
                if (!m.file_pattern) return false
                const rx = new RegExp(m.file_pattern, 'i')
                return rx.test(item.name)
              } catch {
                return false
              }
            })
            if (matched) {
              effectiveMappingId = matched.id
              updateQueue(item.id, { mappingId: matched.id, info: `Usando mapping: ${matched.name}` })
            }
          }

          const thresholdMb = Number(import.meta.env.VITE_IMPORTS_CHUNK_THRESHOLD_MB ?? 8)
          if (item.size > thresholdMb * 1024 * 1024) {
            updateQueue(item.id, { info: 'Subiendo archivo por partes...' })
            const res = await uploadExcelViaChunks(item.file, {
              sourceType: 'products',
              mappingId: effectiveMappingId || undefined,
              onProgress: (pct) => updateQueue(item.id, { info: `Subiendo... ${pct}%` }),
            })
            updateQueue(item.id, { status: 'saved', info: 'Procesando en segundo plano...', batchId: res.batchId })
            processingRef.current.delete(item.id)
            return
          }

          const { headers, rows } = await parseExcelFile(item.file)
          const docType = detectarTipoDocumento(headers)
          updateQueue(item.id, { status: 'ready', headers, rows, docType, error: null, info: null })
          await saveItem(item, headers, rows, docType)
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
              info: 'Procesando documento OCR...',
              jobId: response.jobId,
            })

            setTimeout(() => {
              const current = queueRef.current.find((q) => q.id === item.id)
              if (current && current.status === 'processing' && current.jobId === response.jobId) {
                processItem(current, mappings, defaultMappingId)
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
          updateQueue(item.id, { status: 'ready', headers, rows, docType, error: null, info: null, jobId: response.jobId })
          await saveItem(item, headers, rows, docType)
          return
        }

        throw new Error('Tipo de archivo no soportado')
      } catch (err: any) {
        updateQueue(item.id, {
          status: 'error',
          error: err?.message || 'Error al procesar el archivo',
          info: null,
        })
      } finally {
        processingRef.current.delete(item.id)
      }
    },
    [token, updateQueue]
  )

  const saveItem = async (item: QueueItem, headers: string[], rows: Row[], docType: string) => {
    if (!headers || !rows) return false

    updateQueue(item.id, { status: 'saving' })

    try {
      const batch = await createBatch({
        origin: item.name || 'importador-tenant',
        source_type: docType,
      })

      const batchId = batch.id

      const payload = {
        rows: rows.map((row) => ({
          tipo: docType,
          origen: 'ocr' as const,
          datos: row,
          estado: 'pendiente',
          hash: null,
        }))
      }

      await ingestBatch(batchId, payload)
      updateQueue(item.id, { status: 'saved', batchId })
      return true
    } catch (err: any) {
      updateQueue(item.id, { status: 'error', error: err?.message || 'Error al guardar' })
      return false
    }
  }

  const addToQueue = useCallback((files: FileList | File[]) => {
    const newItems: QueueItem[] = Array.from(files).map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'pending' as const,
    }))

    setQueue((prev) => [...prev, ...newItems])

    // Auto-iniciar procesamiento
    setTimeout(() => {
      newItems.forEach((item) => processItem(item))
    }, 100)
  }, [processItem])

  const removeFromQueue = useCallback((id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const clearQueue = useCallback(() => {
    setQueue([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  const processingCount = queue.filter((item) => item.status === 'processing').length

  useEffect(() => {
    setIsProcessing(processingCount > 0)
  }, [processingCount])

  return (
    <ImportQueueContext.Provider
      value={{
        queue,
        addToQueue,
        removeFromQueue,
        clearQueue,
        isProcessing,
        processingCount,
      }}
    >
      {children}
    </ImportQueueContext.Provider>
  )
}

export function useImportQueue() {
  const context = useContext(ImportQueueContext)
  if (!context) {
    throw new Error('useImportQueue debe usarse dentro de ImportQueueProvider')
  }
  return context
}
