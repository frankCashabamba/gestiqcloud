import React, { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { listarPendientes, eliminarPendiente, actualizarPendiente, enviarDocumento, type DatosImportadosOut } from './services'

type Editable = {
  fecha?: string
  concepto?: string
  monto?: number
  documentoTipo?: string
  cuenta?: string
  cliente?: string
}

export default function ImportadosList() {
  const { token } = useAuth() as { token: string | null }
  const [items, setItems] = useState<DatosImportadosOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Record<number, Editable>>({})
  const [selected, setSelected] = useState<Record<number, boolean>>({})

  async function load() {
    setError(null)
    setLoading(true)
    try {
      const data = await listarPendientes(token || undefined)
      setItems(data)
    } catch (e: any) {
      setError(e?.message || 'Error al cargar')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const onEditChange = (id: number, k: keyof Editable, v: string) => {
    setEditing((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), [k]: v } }))
  }

  const onSave = async (it: DatosImportadosOut) => {
    const e = editing[it.id] || {}
    const datos = { ...(it.datos || {}) } as any
    if (e.fecha !== undefined) datos.fecha = e.fecha
    if (e.concepto !== undefined) datos.concepto = e.concepto
    if (e.monto !== undefined) datos.monto = Number(e.monto)
    if (e.documentoTipo !== undefined) datos.documentoTipo = e.documentoTipo
    if (e.cuenta !== undefined) datos.cuenta = e.cuenta
    if (e.cliente !== undefined) datos.cliente = e.cliente
    try {
      await actualizarPendiente(it.id, { tipo: it.tipo, origen: it.origen, datos, estado: it.estado }, token || undefined)
      await load()
    } catch {}
  }

  const onDelete = async (id: number) => {
    try { await eliminarPendiente(id, token || undefined); await load() } catch {}
  }

  const onSend = async (id: number) => {
    try { await enviarDocumento(id, token || undefined); await load() } catch {}
  }

  const cols = useMemo(() => ['fecha', 'concepto', 'monto', 'documentoTipo', 'cuenta', 'cliente'], [])

  const toggleAll = (checked: boolean) => {
    const next: Record<number, boolean> = {}
    items.forEach(it => { next[it.id] = checked })
    setSelected(next)
  }

  const toggleOne = (id: number, checked: boolean) => {
    setSelected(prev => ({ ...prev, [id]: checked }))
  }

  const onSendSelected = async () => {
    const ids = items.filter(it => selected[it.id]).map(it => it.id)
    for (const id of ids) {
      try { await onSend(id) } catch {}
    }
    await load()
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-3">Importados pendientes</h2>
      <div className="mb-2 flex items-center gap-2">
        <button className="bg-green-600 text-white px-2 py-1 rounded" onClick={onSendSelected} disabled={!items.some(it => selected[it.id])}>Enviar seleccionados</button>
      </div>
      {loading && <div className="text-sm text-gray-600">Cargando…</div>}
      {error && <div className="text-sm text-red-700">{error}</div>}
      {!loading && items.length === 0 && <div className="text-sm text-gray-600">No hay pendientes.</div>}
      {!loading && items.length > 0 && (
        <div className="overflow-auto border rounded">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="px-2 py-1 text-left"><input type="checkbox" onChange={(e)=> toggleAll(e.target.checked)} /></th>
                <th className="px-2 py-1 text-left">ID</th>
                {cols.map(c => <th key={c} className="px-2 py-1 text-left capitalize">{c}</th>)}
                <th className="px-2 py-1" />
              </tr>
            </thead>
            <tbody>
              {items.map((it) => {
                const d = (it.datos || {}) as any
                const ed = editing[it.id] || {}
                return (
                  <tr key={it.id} className="border-t">
                    <td className="px-2 py-1"><input type="checkbox" checked={!!selected[it.id]} onChange={(e)=> toggleOne(it.id, e.target.checked)} /></td>
                    <td className="px-2 py-1">{it.id}</td>
                    {cols.map((c) => (
                      <td key={c} className="px-2 py-1">
                        <input
                          className="border px-2 py-1 rounded text-sm w-full"
                          value={(ed as any)[c] ?? (d[c] ?? '')}
                          onChange={(e)=> onEditChange(it.id, c as keyof Editable, e.target.value)}
                        />
                      </td>
                    ))}
                    <td className="px-2 py-1 whitespace-nowrap">
                      <button className="bg-blue-600 text-white px-2 py-1 rounded mr-2" onClick={()=> onSave(it)}>Guardar</button>
                      <button className="bg-green-600 text-white px-2 py-1 rounded mr-2" onClick={()=> onSend(it.id)}>Enviar</button>
                      <button className="bg-red-600 text-white px-2 py-1 rounded" onClick={()=> onDelete(it.id)}>Eliminar</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
