import React, { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { procesarDocumento, guardarPendiente, guardarBatch, type DatosImportadosCreate } from './services'
import { autoMapeoColumnas } from './services/autoMapeoColumnas'
import { getAliasSugeridos } from './utils/aliasCampos'
import { detectarTipoDocumento } from './utils/detectarTipoDocumento'
import { normalizarDocumento } from './utils/normalizarDocumento'

type Row = Record<string, string>
type ItemStatus = 'pending' | 'processing' | 'ready' | 'saving' | 'saved' | 'duplicate' | 'error'
type QueueItem = {
  id: string
  file: File
  name: string
  type: string
  status: ItemStatus
  error?: string | null
  headers?: string[]
  rows?: Row[]
  docType?: string
}

function parseCSV(text: string): { headers: string[]; rows: Row[] } {
  const lines = text.split(/\r?\n/).filter(Boolean)
  if (lines.length === 0) return { headers: [], rows: [] }
  const headers = lines[0].split(',').map(h => h.trim())
  const rows = lines.slice(1).map(line => {
    const cols = line.split(',')
    const row: Row = {}
    headers.forEach((h, i) => (row[h] = (cols[i] ?? '').trim()))
    return row
  })
  return { headers, rows }
}

export default function ImportadorPage() {
  const { token } = useAuth() as { token: string | null }
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [savingAll, setSavingAll] = useState(false)
  const [savedSummary, setSavedSummary] = useState<{ saved: number; errors: number } | null>(null)
  const { empresa } = useParams()

  const onFiles: React.ChangeEventHandler<HTMLInputElement> = async (e) => {
    const files = Array.from(e.target.files || [])
    const items: QueueItem[] = files.map((f, idx) => ({ id: `${Date.now()}-${idx}`, file: f, name: f.name, type: f.type, status: 'pending' }))
    setQueue(prev => [...prev, ...items])
  }

  const processItem = async (item: QueueItem) => {
    const ext = item.name.toLowerCase()
    const isCSV = ext.endsWith('.csv')
    const isExcel = ext.endsWith('.xlsx') || ext.endsWith('.xls')
    const isDoc = ext.endsWith('.pdf') || isExcel || item.type.startsWith('image/')
    setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'processing', error: null } : q))
    try {
      if (isCSV) {
        const text = await item.file.text()
        const { headers, rows } = parseCSV(text)
        const sugeridos = autoMapeoColumnas(headers, getAliasSugeridos())
        const docType = detectarTipoDocumento(headers)
        // Normalizamos solo al guardar; aquí dejamos headers/rows para preview
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'ready', headers, rows, docType } : q))
      } else if (isDoc) {
        const resp = await procesarDocumento(item.file, token || undefined)
        const documentos = Array.isArray(resp?.documentos) ? resp.documentos : []
        const headers = documentos.length ? Object.keys(documentos[0]) : []
        const rows: Row[] = documentos.map((d: any) => {
          const r: Row = {}
          headers.forEach(h => { r[h] = String(d[h] ?? '') })
          return r
        })
        const docType = (documentos[0]?.documentoTipo as string) || 'generico'
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'ready', headers, rows, docType } : q))
      } else {
        throw new Error('Tipo de archivo no soportado')
      }
    } catch (e: any) {
      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'error', error: e?.message || 'Error' } : q))
    }
  }

  const processAll = async () => {
    setGlobalError(null)
    const toProcess = queue.filter(q => q.status === 'pending')
    for (const it of toProcess) {
      // sequential to avoid overloading; could be Promise.allSettled for parallel
      // eslint-disable-next-line no-await-in-loop
      await processItem(it)
    }
  }

  const saveItem = async (item: QueueItem) => {
    if (!item.headers || !item.rows) return
    setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'saving' } : q))
    try {
      // Guardar todos los rows como documentos individuales en datos_importados
      const sugeridos = autoMapeoColumnas(item.headers, getAliasSugeridos())
      const docs = normalizarDocumento(item.rows, sugeridos as any)
      for (const d of docs) {
        const payload: DatosImportadosCreate = {
          tipo: 'documento',
          origen: 'excel',
          datos: { ...d, documentoTipo: item.docType || 'generico' },
        }
        // eslint-disable-next-line no-await-in-loop
        await guardarPendiente(payload, token || undefined)
      }
      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'saved' } : q))
    } catch (e: any) {
      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'error', error: e?.message || 'Error al guardar' } : q))
    }
  }

  const saveAll = async () => {
    setSavingAll(true)
    setGlobalError(null)
    setSavedSummary(null)
    const ready = queue.filter(q => q.status === 'ready')
    try {
      // Try batch first
      const batch: DatosImportadosCreate[] = []
      for (const it of ready) {
        if (!it.headers || !it.rows) continue
        const sugeridos = autoMapeoColumnas(it.headers, getAliasSugeridos())
        const docs = normalizarDocumento(it.rows, sugeridos as any)
        for (const d of docs) {
          batch.push({ tipo: 'documento', origen: 'excel', datos: { ...d, documentoTipo: it.docType || 'generico' } })
        }
      }
      if (batch.length) {
        await guardarBatch(batch, token || undefined)
        // Mark all ready as saved
        setQueue(prev => prev.map(q => q.status === 'ready' ? { ...q, status: 'saved' } : q))
      }
    } catch (e) {
      // Fallback: iterative save per item
      for (const it of ready) {
        // eslint-disable-next-line no-await-in-loop
        await saveItem(it)
      }
    }
    const saved = (ready.length > 0) ? ready.length : queue.filter(q => q.status === 'saved').length
    const errors = queue.filter(q => q.status === 'error').length
    setSavedSummary({ saved, errors })
    setSavingAll(false)
  }

  const anyPending = queue.some(q => q.status === 'pending')
  const anyReady = queue.some(q => q.status === 'ready')

  const total = useMemo(() => queue.length, [queue])

  return (
    <div className="p-4 max-w-4xl space-y-4">
      <h2 className="text-lg font-semibold">Importar archivos</h2>
      <p className="text-sm text-gray-600">Selecciona múltiples archivos (CSV, Excel, PDF o imágenes). Se procesarán y quedarán listos para guardar en pendientes.</p>

      <div className="flex flex-wrap items-center gap-3">
        <input type="file" multiple accept=".csv,.xlsx,.xls,.pdf,image/*" onChange={onFiles} />
        <button className="bg-blue-600 text-white px-3 py-2 rounded" onClick={processAll} disabled={!anyPending}>Procesar</button>
        <button className="bg-green-600 text-white px-3 py-2 rounded" onClick={saveAll} disabled={!anyReady || savingAll}>{savingAll ? 'Guardando…' : 'Guardar todos'}</button>
      </div>
      {globalError && <div className="text-sm text-red-700">{globalError}</div>}

      {total === 0 ? (
        <div className="text-sm text-gray-600">No hay archivos en cola.</div>
      ) : (
        <div className="overflow-auto border rounded">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="px-2 py-1 text-left">Archivo</th>
                <th className="px-2 py-1 text-left">Tipo</th>
                <th className="px-2 py-1 text-left">Estado</th>
                <th className="px-2 py-1 text-left">Filas</th>
                <th className="px-2 py-1" />
              </tr>
            </thead>
            <tbody>
              {queue.map((q) => (
                <tr key={q.id} className="border-t">
                  <td className="px-2 py-1">{q.name}</td>
                  <td className="px-2 py-1">{q.type || '-'}</td>
                  <td className="px-2 py-1">{q.status}{q.error ? ` · ${q.error}` : ''}</td>
                  <td className="px-2 py-1">{q.rows?.length ?? '-'}</td>
                  <td className="px-2 py-1 whitespace-nowrap">
                    {q.status === 'pending' && (
                      <button className="bg-blue-600 text-white px-2 py-1 rounded" onClick={()=> processItem(q)}>Procesar</button>
                    )}
                    {q.status === 'ready' && (
                      <button className="bg-green-600 text-white px-2 py-1 rounded" onClick={()=> saveItem(q)}>Guardar</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {savedSummary && (
        <div className="p-3 border rounded bg-green-50 text-sm text-green-800">
          Guardados {savedSummary.saved} archivos en pendientes{savedSummary.errors ? `, ${savedSummary.errors} con error` : ''}.
          <div className="mt-2">
            <Link to={`${empresa ? `/${empresa}` : ''}/mod/importador/pendientes`} className="underline text-green-900">Revisar pendientes</Link>
          </div>
        </div>
      )}
    </div>
  )
}
