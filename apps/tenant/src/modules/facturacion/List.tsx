import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listFacturas, removeFactura, type Factura } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import FacturaStatusBadge from './components/FacturaStatusBadge'

export default function FacturasList() {
  const [items, setItems] = useState<Factura[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [estado, setEstado] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    (async () => {
      try { setLoading(true); setItems(await listFacturas()) }
      catch (e:any) { const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
      finally { setLoading(false) }
    })()
  }, [])

  const filtered = useMemo(() => items.filter(v => {
    if (estado && (v.estado||'') !== estado) return false
    if (desde && v.fecha < desde) return false
    if (hasta && v.fecha > hasta) return false
    if (q && !(`${v.id}`.includes(q) || (v.estado||'').toLowerCase().includes(q.toLowerCase()))) return false
    return true
  }), [items, estado, desde, hasta, q])

  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">Facturación</h2>
        <div className="flex gap-2">
          <button className="bg-gray-200 px-3 py-1 rounded" onClick={()=> nav('sectores')}>Sectores</button>
          <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={()=> nav('nueva')}>Nueva</button>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2 block">Estado</label>
          <select value={estado} onChange={(e)=> setEstado(e.target.value)} className="border px-2 py-1 rounded text-sm">
            <option value="">Todos</option>
            <option value="borrador">Borrador</option>
            <option value="emitida">Emitida</option>
            <option value="anulada">Anulada</option>
          </select>
        </div>
        <div>
          <label className="text-sm mr-2 block">Desde</label>
          <input type="date" value={desde} onChange={(e)=> setDesde(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
        <div>
          <label className="text-sm mr-2 block">Hasta</label>
          <input type="date" value={hasta} onChange={(e)=> setHasta(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
        <div>
          <label className="text-sm mr-2 block">Buscar</label>
          <input placeholder="ID o estado" value={q} onChange={(e)=> setQ(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <table className="min-w-full text-sm">
        <thead><tr className="text-left border-b"><th>Fecha</th><th>Total</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>
          {view.map((v) => (
            <tr key={v.id} className="border-b">
              <td>{v.fecha}</td>
              <td>{v.total.toFixed(2)}</td>
              <td><FacturaStatusBadge estado={v.estado} /></td>
              <td>
                <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async ()=> { if(!confirm('¿Eliminar factura?')) return; try { await removeFactura(v.id); setItems((p)=>p.filter(x=>x.id!==v.id)); success('Factura eliminada') } catch(e:any){ toastError(getErrorMessage(e)) } }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length===0 && <tr><td className="py-3 px-3" colSpan={4}>Sin registros</td></tr>}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}

