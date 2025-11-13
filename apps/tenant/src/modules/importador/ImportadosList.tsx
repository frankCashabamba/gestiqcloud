import React, { useEffect, useMemo, useState } from 'react'
import ImportadorLayout from './components/ImportadorLayout'
import { useAuth } from '../../auth/AuthContext'
import {
  listarPendientes,
  eliminarPendiente,
  actualizarPendiente,
  enviarDocumento,
  type DatosImportadosOut,
} from './services'

type Editable = {
  fecha?: string
  concepto?: string
  monto?: number
  documentoTipo?: string
  cuenta?: string
  cliente?: string
}

type PendingRowState = {
  saving?: boolean
  sending?: boolean
  deleting?: boolean
}

export default function ImportadosList() {
  const { token } = useAuth() as { token: string | null }
  const [items, setItems] = useState<DatosImportadosOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [editing, setEditing] = useState<Record<number, Editable>>({})
  const [selected, setSelected] = useState<Record<number, boolean>>({})
  const [rowState, setRowState] = useState<Record<number, PendingRowState>>({})
  const [bulkSending, setBulkSending] = useState(false)

  const cols = useMemo(() => ['fecha', 'concepto', 'monto', 'documentoTipo', 'cuenta', 'cliente'], [])

  async function load() {
    setError(null)
    setMessage(null)
    setLoading(true)
    try {
      const data = await listarPendientes()
      setItems(data)
      setEditing({})
      const initialSelected: Record<number, boolean> = {}
      data.forEach((item) => {
        initialSelected[item.id] = false
      })
      setSelected(initialSelected)
    } catch (err: any) {
      setError(err?.message || 'Error al cargar pendientes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onEditChange = (id: number, key: keyof Editable, value: string) => {
    setEditing((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), [key]: value } }))
  }

  const setRowStatus = (id: number, changes: PendingRowState) => {
    setRowState((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), ...changes } }))
  }

  const onSave = async (item: DatosImportadosOut) => {
    const pendingChanges = editing[item.id] || {}
    const datos = { ...(item.datos || {}) } as Record<string, unknown>
    if (pendingChanges.fecha !== undefined) datos.fecha = pendingChanges.fecha
    if (pendingChanges.concepto !== undefined) datos.concepto = pendingChanges.concepto
    if (pendingChanges.monto !== undefined) datos.monto = Number(pendingChanges.monto)
    if (pendingChanges.documentoTipo !== undefined) datos.documentoTipo = pendingChanges.documentoTipo
    if (pendingChanges.cuenta !== undefined) datos.cuenta = pendingChanges.cuenta
    if (pendingChanges.cliente !== undefined) datos.cliente = pendingChanges.cliente

    setRowStatus(item.id, { saving: true })
    try {
      await actualizarPendiente(
        item.id,
        { tipo: item.tipo, origen: item.origen, datos, estado: item.estado },
        token || undefined,
      )
      setMessage('Cambios guardados correctamente')
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'No se pudo guardar el registro')
    } finally {
      setRowStatus(item.id, { saving: false })
    }
  }

  const onDelete = async (id: number) => {
    setRowStatus(id, { deleting: true })
    try {
      await eliminarPendiente(id)
      setMessage('Registro eliminado')
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'No se pudo eliminar el registro')
      setRowStatus(id, { deleting: false })
    }
  }

  const onSend = async (id: number) => {
    setRowStatus(id, { sending: true })
    try {
      await enviarDocumento(id, token || undefined)
      setMessage('Documento enviado')
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'No se pudo enviar el documento')
      setRowStatus(id, { sending: false })
    }
  }

  const toggleAll = (checked: boolean) => {
    const next: Record<number, boolean> = {}
    items.forEach((item) => {
      next[item.id] = checked
    })
    setSelected(next)
  }

  const toggleOne = (id: number, checked: boolean) => {
    setSelected((prev) => ({ ...prev, [id]: checked }))
  }

  const selectedIds = useMemo(() => items.filter((item) => selected[item.id]).map((item) => item.id), [items, selected])

  const onSendSelected = async () => {
    if (!selectedIds.length) return
    setBulkSending(true)
    try {
      for (const id of selectedIds) {
        // eslint-disable-next-line no-await-in-loop
        await enviarDocumento(id, token || undefined)
      }
      setMessage(`${selectedIds.length} documento${selectedIds.length === 1 ? '' : 's'} enviados`)
      await load()
    } catch (err: any) {
      setMessage(null)
      setError(err?.message || 'No se pudieron enviar los documentos seleccionados')
    } finally {
      setBulkSending(false)
    }
  }

  const total = items.length
  const selectedCount = selectedIds.length
  const empty = !loading && total === 0

  return (
    <ImportadorLayout
      title="Pendientes por revisar"
      description="Edita los datos sugeridos antes de enviarlos al sistema. Puedes guardar ajustes, enviar en lote o descartar los registros."
      actions={
        <button
          type="button"
          className="rounded-md bg-green-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-green-300"
          onClick={onSendSelected}
          disabled={!selectedCount || bulkSending}
        >
          {bulkSending ? 'Enviando...' : `Enviar seleccionados (${selectedCount})`}
        </button>
      }
    >
      <section className="space-y-4">
        {error && (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
            {error}
          </div>
        )}
        {message && (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700" role="status">
            {message}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-neutral-500">
          <span>{total} registro{total === 1 ? '' : 's'} en pendientes</span>
          <button
            type="button"
            className="rounded-md border border-neutral-200 px-2 py-1 font-medium text-neutral-700 hover:bg-neutral-100"
            onClick={load}
            disabled={loading}
          >
            {loading ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>

        {loading && (
          <div className="rounded-lg border border-neutral-200 bg-white p-6 text-center text-sm text-neutral-500">
            Cargando pendientes...
          </div>
        )}

        {empty && (
          <div className="rounded-lg border border-neutral-200 bg-white p-6 text-sm text-neutral-600 shadow-sm">
            No hay pendientes en este momento.
          </div>
        )}

        {!loading && !empty && (
          <div className="overflow-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-neutral-50 text-xs font-medium uppercase tracking-wide text-neutral-500">
                <tr>
                  <th className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedCount > 0 && selectedCount === total}
                      onChange={(event) => toggleAll(event.target.checked)}
                    />
                  </th>
                  <th className="px-4 py-3 text-left">ID</th>
                  {cols.map((col) => (
                    <th key={col} className="px-4 py-3 text-left capitalize">
                      {col}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const currentData = (item.datos || {}) as Record<string, unknown>
                  const draft = editing[item.id] || {}
                  const state = rowState[item.id] || {}

                  return (
                    <tr key={item.id} className="border-t border-neutral-100 hover:bg-neutral-50">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={!!selected[item.id]}
                          onChange={(event) => toggleOne(item.id, event.target.checked)}
                        />
                      </td>
                      <td className="px-4 py-3 text-xs font-mono text-neutral-500">{item.id}</td>
                      {cols.map((col) => (
                        <td key={col} className="px-4 py-3">
                          <input
                            className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                            value={(draft as Record<string, string>)[col] ?? String(currentData[col] ?? '')}
                            onChange={(event) => onEditChange(item.id, col as keyof Editable, event.target.value)}
                          />
                        </td>
                      ))}
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <button
                            type="button"
                            className="rounded-md bg-blue-600 px-3 py-1.5 font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-300"
                            onClick={() => onSave(item)}
                            disabled={state.saving}
                          >
                            {state.saving ? 'Guardando...' : 'Guardar'}
                          </button>
                          <button
                            type="button"
                            className="rounded-md bg-green-600 px-3 py-1.5 font-medium text-white hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-green-300"
                            onClick={() => onSend(item.id)}
                            disabled={state.sending}
                          >
                            {state.sending ? 'Enviando...' : 'Enviar'}
                          </button>
                          <button
                            type="button"
                            className="rounded-md bg-rose-600 px-3 py-1.5 font-medium text-white hover:bg-rose-500 disabled:cursor-not-allowed disabled:bg-rose-300"
                            onClick={() => onDelete(item.id)}
                            disabled={state.deleting}
                          >
                            {state.deleting ? 'Eliminando...' : 'Eliminar'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </ImportadorLayout>
  )
}
