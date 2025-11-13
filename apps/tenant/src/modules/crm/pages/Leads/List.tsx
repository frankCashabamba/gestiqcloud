import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listLeads, deleteLead, convertLead, type Lead } from '../../services'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { usePagination, Pagination } from '../../../../shared/pagination'
import { LeadStatus, LeadSource } from '../../types'

export default function LeadsList() {
  const [items, setItems] = useState<Lead[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sourceFilter, setSourceFilter] = useState<string>('')

  useEffect(() => {
    (async () => {
      try { setLoading(true); setItems(await listLeads()) }
      catch (e: any) { const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
      finally { setLoading(false) }
    })()
  }, [])

  const [sortKey, setSortKey] = useState<'name'|'email'|'company'|'status'>('name')
  const [sortDir, setSortDir] = useState<'asc'|'desc'>('asc')
  const [per, setPer] = useState(10)
  const filtered = useMemo(() => items.filter(c => {
    const matchSearch = (c.name||'').toLowerCase().includes(q.toLowerCase()) || (c.email||'').toLowerCase().includes(q.toLowerCase())
    const matchStatus = !statusFilter || c.status === statusFilter
    const matchSource = !sourceFilter || c.source === sourceFilter
    return matchSearch && matchStatus && matchSource
  }), [items,q,statusFilter,sourceFilter])
  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a,b) => {
      const av = ((a as any)[sortKey]||'').toString().toLowerCase()
      const bv = ((b as any)[sortKey]||'').toString().toLowerCase()
      return av < bv ? -1*dir : av > bv ? 1*dir : 0
    })
  }, [filtered, sortKey, sortDir])
  const { page, setPage, totalPages, view, perPage, setPerPage } = usePagination(sorted, per)
  useEffect(()=> setPerPage(per), [per, setPerPage])

  const handleConvert = async (id: string) => {
    if (!confirm('¿Convertir lead a oportunidad?')) return
    try {
      await convertLead(id, { create_opportunity: true })
      setItems((p)=>p.filter(x=>x.id!==id))
      success('Lead convertido')
    } catch(e:any){ toastError(getErrorMessage(e)) }
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">Leads</h2>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nuevo Lead</button>
      </div>
      <input value={q} onChange={(e)=> setQ(e.target.value)} placeholder="Buscar nombre o email..." className="mb-3 w-full px-3 py-2 border rounded text-sm" />
      <div className="flex gap-3 mb-3">
        <select value={statusFilter} onChange={(e)=> setStatusFilter(e.target.value)} className="border px-2 py-1 rounded text-sm">
          <option value="">Todos los estados</option>
          <option value={LeadStatus.NEW}>Nuevo</option>
          <option value={LeadStatus.CONTACTED}>Contactado</option>
          <option value={LeadStatus.QUALIFIED}>Calificado</option>
          <option value={LeadStatus.LOST}>Perdido</option>
          <option value={LeadStatus.CONVERTED}>Convertido</option>
        </select>
        <select value={sourceFilter} onChange={(e)=> setSourceFilter(e.target.value)} className="border px-2 py-1 rounded text-sm">
          <option value="">Todas las fuentes</option>
          <option value={LeadSource.WEBSITE}>Website</option>
          <option value={LeadSource.REFERRAL}>Referido</option>
          <option value={LeadSource.SOCIAL_MEDIA}>Redes Sociales</option>
          <option value={LeadSource.EMAIL}>Email</option>
          <option value={LeadSource.PHONE}>Teléfono</option>
          <option value={LeadSource.EVENT}>Evento</option>
          <option value={LeadSource.OTHER}>Otro</option>
        </select>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>Por página</label>
        <select value={per} onChange={(e)=> setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th><button className="underline" onClick={()=> { setSortKey('name'); setSortDir(d=> d==='asc'?'desc':'asc') }}>Nombre {sortKey==='name' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th><button className="underline" onClick={()=> { setSortKey('company'); setSortDir(d=> d==='asc'?'desc':'asc') }}>Empresa {sortKey==='company' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th><button className="underline" onClick={()=> { setSortKey('email'); setSortDir(d=> d==='asc'?'desc':'asc') }}>Email {sortKey==='email' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th>Teléfono</th>
            <th><button className="underline" onClick={()=> { setSortKey('status'); setSortDir(d=> d==='asc'?'desc':'asc') }}>Estado {sortKey==='status' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th>Asignado a</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {view.map((c) => (
            <tr key={c.id} className="border-b">
              <td>{c.name}</td>
              <td>{c.company || '-'}</td>
              <td>{c.email || '-'}</td>
              <td>{c.phone || '-'}</td>
              <td>{c.status}</td>
              <td>{c.assigned_to || '-'}</td>
              <td>
                <Link to={`${c.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-green-700 mr-3" onClick={() => handleConvert(c.id)}>Convertir</button>
                <button className="text-red-700" onClick={async () => { if (!confirm('¿Eliminar lead?')) return; try { await deleteLead(c.id); setItems((p)=>p.filter(x=>x.id!==c.id)); success('Lead eliminado') } catch(e:any){ toastError(getErrorMessage(e)) } }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (<tr><td className="py-3 px-3" colSpan={7}>Sin registros</td></tr>)}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
