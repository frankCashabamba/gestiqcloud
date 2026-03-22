import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listLeads, deleteLead, convertLead, type Lead } from '../../services'
import { useCrmLabels } from '../../useCrmLabels'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { usePagination, Pagination } from '../../../../shared/pagination'
import { LeadStatus, LeadSource } from '../../types'

export default function LeadsList() {
  const [items, setItems] = useState<Lead[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const { t } = useCrmLabels()
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
    if (!confirm(t('leads.convertConfirm'))) return
    try {
      await convertLead(id, { create_opportunity: true })
      setItems((p)=>p.filter(x=>x.id!==id))
      success(t('leads.converted'))
    } catch(e:any){ toastError(getErrorMessage(e)) }
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">{t('leads.title')}</h2>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('new')}>{t('leads.newLead')}</button>
      </div>
      <input value={q} onChange={(e)=> setQ(e.target.value)} placeholder={t('leads.searchPlaceholder')} className="mb-3 w-full px-3 py-2 border rounded text-sm" />
      <div className="flex gap-3 mb-3">
        <select value={statusFilter} onChange={(e)=> setStatusFilter(e.target.value)} className="border px-2 py-1 rounded text-sm">
          <option value="">{t('leads.allStatuses')}</option>
          <option value={LeadStatus.NEW}>{t('leads.statusNew')}</option>
          <option value={LeadStatus.CONTACTED}>{t('leads.statusContacted')}</option>
          <option value={LeadStatus.QUALIFIED}>{t('leads.statusQualified')}</option>
          <option value={LeadStatus.LOST}>{t('leads.statusLost')}</option>
          <option value={LeadStatus.CONVERTED}>{t('leads.statusConverted')}</option>
        </select>
        <select value={sourceFilter} onChange={(e)=> setSourceFilter(e.target.value)} className="border px-2 py-1 rounded text-sm">
          <option value="">{t('leads.allSources')}</option>
          <option value={LeadSource.WEBSITE}>{t('leads.sourceWebsite')}</option>
          <option value={LeadSource.REFERRAL}>{t('leads.sourceReferral')}</option>
          <option value={LeadSource.SOCIAL_MEDIA}>{t('leads.sourceSocialMedia')}</option>
          <option value={LeadSource.EMAIL}>{t('leads.sourceEmail')}</option>
          <option value={LeadSource.PHONE}>{t('leads.phoneSource')}</option>
          <option value={LeadSource.EVENT}>{t('leads.sourceEvent')}</option>
          <option value={LeadSource.OTHER}>{t('leads.sourceOther')}</option>
        </select>
      </div>
      {loading && <div className="text-sm text-gray-500">{t('leads.loading')}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>{t('leads.perPage')}</label>
        <select value={per} onChange={(e)=> setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th><button className="underline" onClick={()=> { setSortKey('name'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('leads.name')} {sortKey==='name' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th><button className="underline" onClick={()=> { setSortKey('company'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('leads.company')} {sortKey==='company' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th><button className="underline" onClick={()=> { setSortKey('email'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('leads.email')} {sortKey==='email' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th>{t('leads.phone')}</th>
            <th><button className="underline" onClick={()=> { setSortKey('status'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('leads.status')} {sortKey==='status' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th>{t('leads.assignedTo')}</th>
            <th>{t('leads.actions')}</th>
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
                <Link to={`${c.id}/edit`} className="text-blue-600 hover:underline mr-3">{t('leads.edit')}</Link>
                <button className="text-green-700 mr-3" onClick={() => handleConvert(c.id)}>{t('leads.convert')}</button>
                <button className="text-red-700" onClick={async () => { if (!confirm(t('leads.deleteConfirm'))) return; try { await deleteLead(c.id); setItems((p)=>p.filter(x=>x.id!==c.id)); success(t('leads.deleted')) } catch(e:any){ toastError(getErrorMessage(e)) } }}>{t('leads.deleteBtn')}</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (<tr><td className="py-3 px-3" colSpan={7}>{t('leads.empty')}</td></tr>)}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
