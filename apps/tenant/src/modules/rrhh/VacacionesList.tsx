import React, { useEffect, useState } from 'react'
import { listVacaciones, type Vacacion } from './services'
import { getErrorMessage, useToast } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'

export default function VacacionesList() {
  const [items, setItems] = useState<Vacacion[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [estado, setEstado] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const { error } = useToast()
  useEffect(()=> { (async ()=> { try { setLoading(true); setItems(await listVacaciones()) } catch(e:any){ const m=getErrorMessage(e); setErrMsg(m); error(m) } finally{ setLoading(false) } })() },[])
  const filtered = items.filter(v => (!estado || (v.estado||'')===estado) && (!from || v.inicio >= from) && (!to || v.fin <= to))
  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-3">Vacaciones</h2>
      <div className="flex items-end gap-3 mb-3 text-sm">
        <div><label className="block mb-1">Estado</label><select value={estado} onChange={(e)=> setEstado(e.target.value)} className="border px-2 py-1 rounded"><option value="">Todos</option><option value="pendiente">Pendiente</option><option value="aprobada">Aprobada</option><option value="rechazada">Rechazada</option></select></div>
        <div><label className="block mb-1">Desde</label><input type="date" value={from} onChange={(e)=> setFrom(e.target.value)} className="border px-2 py-1 rounded" /></div>
        <div><label className="block mb-1">Hasta</label><input type="date" value={to} onChange={(e)=> setTo(e.target.value)} className="border px-2 py-1 rounded" /></div>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <table className="min-w-full text-sm">
        <thead><tr className="text-left border-b"><th>Usuario</th><th>Inicio</th><th>Fin</th><th>Estado</th></tr></thead>
        <tbody>
          {view.map(v => (
            <tr key={v.id} className="border-b"><td>{v.usuario_id}</td><td>{v.inicio}</td><td>{v.fin}</td><td>{v.estado||'-'}</td></tr>
          ))}
          {!loading && items.length===0 && <tr><td className="py-3 px-3" colSpan={4}>Sin registros</td></tr>}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
