import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import i18n from '../../../i18n'
import { useAuth } from '../../../auth/AuthContext'
import { pollOcrJob, processDocument } from '../services/importsApi'
import { parseExcelFile } from '../services/parseExcelFile'
import { uploadExcelViaChunks, createBatch, ingestBatch, type ImportMapping } from '../services/importsApi'
import { detectarTipoDocumento, type ImportDocType } from '../utils/detectarTipoDocumento'
import { normalizeOCRRows } from '../utils/normalizeOCRFields'
import { normalizarProductos } from '../utils/normalizarProductosSections'
import { normalizarDocumento } from '../utils/normalizarDocumento'
import { analyzeFile } from '../services/analyzeApi'

const env =
  (typeof import.meta !== 'undefined' && (import.meta as any)?.env)
    ? (import.meta as any).env
    : ((globalThis as any).__IMPORTS_ENV__ || {})
const OCR_RECHECK_DELAY_MS = Number(env.VITE_IMPORTS_JOB_RECHECK_INTERVAL ?? 2000)
const OCR_MAX_POLL_ATTEMPTS = Number(env.VITE_IMPORTS_JOB_POLL_ATTEMPTS ?? 120)
const OCR_MAX_WAIT_MS = Number(env.VITE_IMPORTS_JOB_MAX_WAIT_MS ?? 10 * 60 * 1000)
const STORE_UPLOAD_FILES = String(env.VITE_IMPORTS_STORE_UPLOAD_FILES ?? '1').toLowerCase() !== '0'
const FORCE_PARSE_LOCAL = String(env.VITE_IMPORTS_FORCE_PARSE_LOCAL ?? '0') === '1'

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
  docType?: ImportDocType
  mappingId?: string
  jobId?: string
  batchId?: string
  ocrPollAttempts?: number
  ocrStartedAt?: number
}

type ImportQueueContextType = {
  queue: QueueItem[]
  addToQueue: (files: FileList | File[], docType?: ImportDocType | string) => void
  removeFromQueue: (id: string) => void
  clearQueue: () => void
  isProcessing: boolean
  processingCount: number
}

const ImportQueueContext = createContext<ImportQueueContextType | undefined>(undefined)

const STORAGE_KEY = 'importador_queue_state'

import { parseCSV } from '../services/parseCSVFile'

export function ImportQueueProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth() as { token: string | null }
  const [queue, setQueue] = useState<QueueItem[]>([])
  const queueRef = useRef<QueueItem[]>([])
  const processingRef = useRef<Set<string>>(new Set())
  const [isProcessing, setIsProcessing] = useState(false)

  const normalizeDocType = useCallback((value?: string | null): ImportDocType => {
    const v = (value || '').toLowerCase()
    if (v === 'products' || v === 'product') return 'products'
    if (v === 'invoice' || v === 'invoices' || v === 'factura') return 'invoices'
    if (v === 'bank' || v === 'transferencia' || v === 'banco') return 'bank'
    if (v === 'ticket_pos' || v === 'ticket' || v === 'pos') return 'ticket_pos' as ImportDocType
    if (v === 'recipe' || v === 'recipes' || v === 'receta' || v === 'recetas') return 'recipes'
    return 'expenses'
  }, [])

  // Persistir cola en localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Restaurar items útiles para la UI (mapeo / preview) evitando loops con estados atascados.
        // - Se descartan sólo los duplicados.
        // - Estados intermedios ('processing', 'saving') solo se restauran si ya traen datos parseados.
        // - Los 'saved' ahora se conservan si tienen headers/rows o batchId para que aparezcan en "Mapeo".
        const toRestore = parsed.filter((item: QueueItem) => {
          if (item.status === 'duplicate') return false
          if (['processing', 'saving'].includes(item.status)) {
            return Boolean(item.headers?.length || item.rows?.length)
          }
          if (item.status === 'saved') {
            return Boolean(item.headers?.length || item.rows?.length || item.batchId)
          }
          return true
        })
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

  const applyMappingSuggestion = useCallback((rows: Row[], mapping?: Record<string, string> | null) => {
    if (!mapping || Object.keys(mapping).length === 0) return rows
    return rows.map((row) => {
      const mapped: Row = { ...row }
      Object.entries(mapping).forEach(([src, dest]) => {
        if (dest && dest !== 'ignore' && src in row) {
          mapped[dest] = row[src]
        }
      })
      return mapped
    })
  }, [])

  const detectFileKind = useCallback((item: QueueItem): 'csv' | 'excel' | 'xml' | 'doc' | 'unknown' => {
    const name = (item.name || '').toLowerCase()
    const type = (item.type || '').toLowerCase()

    const isCSV = name.endsWith('.csv') || type.includes('text/csv') || type.includes('application/csv')
    if (isCSV) return 'csv'

    const isXML = name.endsWith('.xml') || type.includes('xml')
    if (isXML) return 'xml'

    const isExcel =
      name.endsWith('.xlsx') ||
      name.endsWith('.xls') ||
      type.includes('spreadsheetml.sheet') ||
      type.includes('ms-excel') ||
      type.includes('excel')
    if (isExcel) return 'excel'

    const isDocumentByName =
      name.endsWith('.pdf') ||
      name.endsWith('.png') ||
      name.endsWith('.jpg') ||
      name.endsWith('.jpeg') ||
      name.endsWith('.webp') ||
      name.endsWith('.bmp') ||
      name.endsWith('.tif') ||
      name.endsWith('.tiff') ||
      name.endsWith('.heic') ||
      name.endsWith('.heif')
    const isDocumentByType = type.includes('pdf') || type.includes('image')
    if (isDocumentByName || isDocumentByType) return 'doc'

    return 'unknown'
  }, [])

  const processItem = useCallback(
    async (item: QueueItem, mappings?: ImportMapping[], defaultMappingId?: string) => {
      if (processingRef.current.has(item.id)) return
      processingRef.current.add(item.id)

      updateQueue(item.id, { status: 'processing', error: null })

          const fileKind = detectFileKind(item)
          const isCSV = fileKind === 'csv'
          const isExcel = fileKind === 'excel'
          const isXML = fileKind === 'xml'
          const isDoc = fileKind === 'doc'

      try {
        const forcedDocType = item.docType ? normalizeDocType(item.docType) : undefined

        if (isCSV) {
          const textContent = await item.file.text()
          const { headers, rows } = parseCSV(textContent)
          const docType = forcedDocType || detectarTipoDocumento(headers)
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

            // Intentar análisis rápido (headers) para determinar docType antes de decidir chunking
            let docType: ImportDocType = forcedDocType || 'products'
            let mappingSuggestion: Record<string, string> | null | undefined
            try {
              const analysis = await analyzeFile(item.file, token || undefined)
              if (analysis?.suggested_doc_type) {
                docType = normalizeDocType(analysis.suggested_doc_type)
              } else if (analysis?.headers_sample || analysis?.headers) {
                const headersSample = analysis.headers_sample || analysis.headers || []
                docType = detectarTipoDocumento(headersSample)
              }
              if (analysis?.mapping_suggestion) {
                mappingSuggestion = analysis.mapping_suggestion
              }
            } catch {
              // fallback: infer from filename if analysis no disponible
              docType = detectarTipoDocumento([item.name])
            }

            // Recetas o archivos grandes suben por chunks, pero intentamos obtener headers/rows para "Mapeo".
            const thresholdMb = Number(env.VITE_IMPORTS_CHUNK_THRESHOLD_MB ?? 8)
            const shouldChunk = STORE_UPLOAD_FILES && (docType === 'recipes' || item.size > thresholdMb * 1024 * 1024)
            if (shouldChunk) {
              // Intento ligero de parseo para poblar headers/rows en UI (sin bloquear si falla).
              try {
                const { headers, rows } = await parseExcelFile(item.file, token || undefined)
                updateQueue(item.id, {
                  headers,
                  rows,
                  docType,
                  info: 'Archivo listo para mapeo (cargando al servidor)...',
                })
              } catch {
                // Continuar si no se puede parsear rápido (p.ej. archivo muy grande)
              }

              updateQueue(item.id, { info: 'Subiendo archivo por partes...' })
              const res = await uploadExcelViaChunks(item.file, {
                sourceType: docType || 'products',
                mappingId: effectiveMappingId || undefined,
                onProgress: (pct) => updateQueue(item.id, { info: `Subiendo... ${pct}%` }),
                authToken: token || undefined,
              })
              updateQueue(item.id, {
                status: 'saved',
                info: 'Procesando en segundo plano...',
                batchId: res.batchId,
                docType,
              })
              processingRef.current.delete(item.id)
              return
            }

            const { headers, rows } = await parseExcelFile(item.file, token || undefined)
            // Intentar análisis con IA para obtener doc_type y mapping sugerido
            // Recalcular docType usando headers reales; si AI discrepó, damos prioridad a los headers
            const docTypeFromHeaders = forcedDocType || detectarTipoDocumento(headers)
            let docTypeLocal: ImportDocType = docTypeFromHeaders
            if (docType && docType !== docTypeFromHeaders) {
              // Solo respetar sugerencia externa en casos especiales (recetas) donde headers son pobres
              docTypeLocal = docType === 'recipes' ? 'recipes' : docTypeFromHeaders
            }
            let mappedRows = rows
            try {
              const analysis = await analyzeFile(item.file, token || undefined)
              if (analysis?.suggested_doc_type) {
                const aiDoc = normalizeDocType(analysis.suggested_doc_type)
                // Si AI dice productos y headers dicen productos, perfecto. Si AI dice invoices pero headers muestran catálogo,
                // mantenemos catálogo para que aparezca en mapeo de productos.
                if (aiDoc === 'recipes') {
                  docTypeLocal = 'recipes'
                } else if (docTypeFromHeaders === 'products' && aiDoc !== 'products') {
                  docTypeLocal = 'products'
                } else {
                  docTypeLocal = aiDoc
                }
              }
              if (analysis?.mapping_suggestion) {
                mappedRows = applyMappingSuggestion(rows, analysis.mapping_suggestion)
              } else if (mappingSuggestion) {
                mappedRows = applyMappingSuggestion(rows, mappingSuggestion)
              }
            } catch {
              // Si falla el análisis, seguir con heurística
            }

            // Recalcular headers tras el mapping sugerido (si aplica).
            // Limitar filas a evitar uso excesivo de memoria en UI.
            const effectiveRows = mappedRows.slice(0, 5000)
            const effectiveHeaders =
              effectiveRows.length > 0 ? Object.keys(effectiveRows[0]) : headers

            // Propagar docType final al estado y al guardado
            docType = docTypeLocal
            updateQueue(item.id, { status: 'ready', headers: effectiveHeaders, rows: effectiveRows, docType, error: null, info: null })

            // Ajuste defensivo: si es productos y existe columna "precio unitario venta", copiarla como precio antes de guardar.
            const rowsForSave = (() => {
              if (docType !== 'products') return effectiveRows
              const priceKey = effectiveHeaders.find(h => /precio\s*unitario\s*venta/i.test(h))
              if (!priceKey) return effectiveRows
              return effectiveRows.map(r => ({
                ...r,
                precio: r.precio ?? r[priceKey],
                price: r.price ?? r[priceKey],
                pvp: r.pvp ?? r[priceKey],
              }))
            })()

            await saveItem(item, effectiveHeaders, rowsForSave, docType)
            return
          }

        if (isXML) {
          if (!STORE_UPLOAD_FILES) {
            throw new Error('Importar XML requiere almacenamiento de archivos en servidor (VITE_IMPORTS_STORE_UPLOAD_FILES=1).')
          }

          // Infer best hint for dispatcher: xml_invoice vs xml_camt053_bank, etc.
          let docType: ImportDocType = 'invoices'
          try {
            const xml = (await item.file.text()).slice(0, 200_000).toLowerCase()
            if (
              xml.includes('camt.053') ||
              xml.includes('bktocstmrstmt') ||
              xml.includes('cstmrstmt') ||
              xml.includes('banktocus') ||
              xml.includes('camt')
            ) {
              docType = 'bank'
            } else if (
              xml.includes('facturae') ||
              xml.includes('<invoice') ||
              xml.includes(':invoice') ||
              xml.includes('invoice')
            ) {
              docType = 'invoices'
            }
          } catch {
            docType = detectarTipoDocumento([item.name])
          }

          updateQueue(item.id, { info: 'Subiendo XML...' })
          const res = await uploadExcelViaChunks(item.file, {
            sourceType: docType,
            onProgress: (pct) => updateQueue(item.id, { info: `Subiendo... ${pct}%` }),
            authToken: token || undefined,
          })
          updateQueue(item.id, {
            status: 'saved',
            info: 'Procesando en segundo plano...',
            batchId: res.batchId,
            docType,
          })
          processingRef.current.delete(item.id)
          return
        }

        if (isDoc) {
          const response = item.jobId
            ? await pollOcrJob(item.jobId, token || undefined)
            : await processDocument(item.file, token || undefined)

          if (response.status === 'pending') {
            const startedAt = item.ocrStartedAt || Date.now()
            const nextPollAttempts = (item.ocrPollAttempts || 0) + 1
            const elapsedMs = Date.now() - startedAt
            const exceededAttempts = nextPollAttempts >= OCR_MAX_POLL_ATTEMPTS
            const exceededTime = elapsedMs >= OCR_MAX_WAIT_MS

            if (exceededAttempts || exceededTime) {
              throw new Error(
                'El OCR sigue en cola y no responde a tiempo. Verifica que el worker de importaciones este activo e intenta de nuevo.'
              )
            }

            updateQueue(item.id, {
              status: 'processing',
              error: null,
              info: 'Procesando documento OCR...',
              jobId: response.jobId,
              ocrPollAttempts: nextPollAttempts,
              ocrStartedAt: startedAt,
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
          const rows: Row[] = documentos.map((doc: Record<string, unknown>) =>
            Object.fromEntries(
              Object.entries(doc || {}).map(([k, v]) => [String(k), String(v ?? '')])
            )
          )

          const firstDoc = (documentos[0] || {}) as Record<string, unknown>
            const docType = forcedDocType || normalizeDocType(
              (firstDoc.documentoTipo as string)
              || (firstDoc.doc_type as string)
              || (firstDoc.tipo as string)
            )
          updateQueue(item.id, { status: 'ready', headers, rows, docType, error: null, info: null, jobId: response.jobId })
          await saveItem(item, headers, rows, docType)
          return
        }

        throw new Error('Tipo de archivo no soportado. Usa CSV, Excel, XML, PDF o imagen.')
      } catch (err: any) {
        updateQueue(item.id, {
          status: 'error',
          error: err?.message || i18n.t('importer:queue.errorProcessing'),
          info: null,
        })
      } finally {
        processingRef.current.delete(item.id)
      }
    },
    [token, updateQueue, detectFileKind]
  )

  const saveItem = async (item: QueueItem, headers: string[], rows: Row[], docType: ImportDocType) => {
    if (!headers || !rows) return false

    updateQueue(item.id, { status: 'saving' })

    try {
      const nameLower = (item.name || '').toLowerCase()
      const isExcel = nameLower.endsWith('.xlsx') || nameLower.endsWith('.xls')
      const isCsv = nameLower.endsWith('.csv')
      const isExcelOrCsv = isExcel || isCsv

      if (isExcel && STORE_UPLOAD_FILES && !FORCE_PARSE_LOCAL) {
        const res = await uploadExcelViaChunks(item.file, {
          sourceType: docType || 'products',
          mappingId: item.mappingId || undefined,
          authToken: token || undefined,
          onProgress: (pct) => updateQueue(item.id, { info: `Subiendo... ${pct}%` }),
        })
        updateQueue(item.id, {
          status: 'saved',
          batchId: res.batchId,
          info: 'Procesando en segundo plano...',
        })
        return true
      }

      let normalizedRows: Record<string, unknown>[]
      if (isExcelOrCsv) {
        if (docType === 'products') {
          normalizedRows = normalizarProductos(rows)
        } else {
          normalizedRows = normalizarDocumento(rows, {}, docType)
        }
      } else {
        // Normalizar campos OCR al schema canónico antes de enviar al backend
        normalizedRows = normalizeOCRRows(rows, docType)
      }

      // Pasar token de autenticación
      const batch = await createBatch({
        origin: item.name || 'importador-tenant',
        source_type: docType,
      }, token || undefined)

      const batchId = batch.id

      const origen = isExcelOrCsv ? (isCsv ? 'csv' : 'excel') : 'ocr'
      const payload = {
        rows: normalizedRows.map((row) => ({
          tipo: docType,
          origen: origen as 'ocr' | 'excel' | 'csv',
          datos: row,
          estado: 'pendiente',
          hash: null,
        }))
      }

      // Pasar token de autenticación
      await ingestBatch(batchId, payload, token || undefined)
      updateQueue(item.id, { status: 'saved', batchId })
      return true
    } catch (err: any) {
      updateQueue(item.id, { status: 'error', error: err?.message || i18n.t('importer:queue.errorSaving') })
      return false
    }
  }

  const addToQueue = useCallback((files: FileList | File[], docType?: ImportDocType | string) => {
    const forcedType = docType ? normalizeDocType(String(docType)) : undefined
    const newItems: QueueItem[] = Array.from(files).map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'pending' as const,
      docType: forcedType,
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
