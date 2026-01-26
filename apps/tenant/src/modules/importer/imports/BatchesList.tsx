import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import ImportadorLayout from '../components/ImportadorLayout'
import { listBatches, type ImportBatch } from '../services/importsApi'
import { useAuth } from '../../../auth/AuthContext'

const statusOptions = [
  { value: '', label: 'Todos' },
  { value: 'READY', label: 'Listos' },
  { value: 'VALIDATED', label: 'Validados' },
  { value: 'PROMOTED', label: 'Promovidos' },
  { value: 'EMPTY', label: 'Vacíos' },
  { value: 'ERROR', label: 'Con errores' },
]
const statusLabels: Record<string, string> = {
  EMPTY: 'Vacío',
}

export default function BatchesList() {
  const { token, profile } = useAuth() as { token: string | null; profile: any }
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<ImportBatch[]>([])

  async function load() {
    if (!token) {
      setError('No hay sesión activa')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await listBatches(status || undefined, profile?.tenant_id)
      setRows(data)
    } catch (err: any) {
      setError(err?.message || 'No se pudieron obtener los lotes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const empty = !loading && rows.length === 0
  const total = useMemo(() => rows.length, [rows])

  return (
    <ImportadorLayout
      title="Lotes de importacion"
      description="Consulta el historial de lotes procesados, filtra por estado y accede al detalle para revalidar o promover registros."
      actions={
        <button
          type="button"
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
          onClick={load}
          disabled={loading}
        >
          {loading ? 'Actualizando...' : 'Actualizar'}
        </button>
      }
    >
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {statusOptions.map((opt) => {
              const isActive = status === opt.value
              return (
                <button
                  key={opt.value || 'all'}
                  type="button"
                  onClick={() => setStatus(opt.value)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    isActive
                      ? 'bg-blue-600 text-white shadow'
                      : 'border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  {opt.label}
                </button>
              )
            })}
          </div>
          <span className="text-xs text-neutral-500">{total} lote{total === 1 ? '' : 's'}</span>
        </div>

        {error && (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
            {error}
          </div>
        )}

        <div className="overflow-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-4 py-3">Lote</th>
                <th className="px-4 py-3">Origen</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Creado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((batch) => (
                <tr key={batch.id} className="border-t border-neutral-100 hover:bg-neutral-50">
                  <td className="px-4 py-3 font-mono text-xs text-blue-700">
                    <Link to={`./${batch.id}`} className="hover:underline">
                      {batch.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-neutral-700">
                    <div className="font-medium text-neutral-900">{batch.source_type}</div>
                    <div className="text-xs text-neutral-500">{batch.origin || 'sin origen'}</div>
                  </td>
                  <td className="px-4 py-3 text-neutral-700">{statusLabels[batch.status] || batch.status}</td>
                  <td className="px-4 py-3 text-neutral-700">
                    {new Date(batch.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && (
            <div className="px-4 py-6 text-center text-sm text-neutral-500">Loading batches...</div>
          )}
          {empty && (
            <div className="px-4 py-6 text-center text-sm text-neutral-500">No se encontraron lotes con ese filtro.</div>
          )}
        </div>
      </section>
    </ImportadorLayout>
  )
}
