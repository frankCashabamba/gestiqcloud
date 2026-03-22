import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { listOpportunities, deleteOpportunity, type Opportunity } from '../../services'
import { useCrmLabels } from '../../useCrmLabels'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { usePagination, Pagination } from '../../../../shared/pagination'
import { OpportunityStage } from '../../types'

export default function OpportunitiesList() {
  const [items, setItems] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const { t } = useCrmLabels()
  const [q, setQ] = useState('')
  const [searchParams] = useSearchParams()
  const pendingOnly = searchParams.get('pending') === '1'
  const PENDING_STAGES = new Set([
    OpportunityStage.PROSPECTING,
    OpportunityStage.QUALIFICATION,
    OpportunityStage.PROPOSAL,
    OpportunityStage.NEGOTIATION,
  ])
  const [stageFilter, setStageFilter] = useState<string>('')
  const [assignedFilter, setAssignedFilter] = useState<string>('')

  useEffect(() => {
    (async () => {
      try { setLoading(true); setItems(await listOpportunities()) }
      catch (e: any) { const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
      finally { setLoading(false) }
    })()
  }, [])

  const [sortKey, setSortKey] = useState<'name'|'value'|'stage'|'expected_close_date'>('name')
  const [sortDir, setSortDir] = useState<'asc'|'desc'>('asc')
  const [per, setPer] = useState(10)
  const filtered = useMemo(() => items.filter(c => {
    const matchSearch = (c.name||'').toLowerCase().includes(q.toLowerCase())
    const matchStage = !stageFilter ? (!pendingOnly || PENDING_STAGES.has(c.stage as OpportunityStage)) : c.stage === stageFilter
    const matchAssigned = !assignedFilter || c.assigned_to === assignedFilter
    return matchSearch && matchStage && matchAssigned
  }), [items, q, stageFilter, assignedFilter, pendingOnly])
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

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">
          {pendingOnly ? t('opportunities.pendingTitle') : t('opportunities.title')}
        </h2>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('new')}>{t('opportunities.newButton')}</button>
      </div>
      <input value={q} onChange={(e)=> setQ(e.target.value)} placeholder={t('opportunities.searchPlaceholder')} className="mb-3 w-full px-3 py-2 border rounded text-sm" />
      <div className="flex gap-3 mb-3">
        <select value={stageFilter} onChange={(e)=> setStageFilter(e.target.value)} className="border px-2 py-1 rounded text-sm">
          <option value="">{t('opportunities.allStages')}</option>
          <option value={OpportunityStage.PROSPECTING}>{t('opportunities.stageProspecting')}</option>
          <option value={OpportunityStage.QUALIFICATION}>{t('opportunities.stageQualification')}</option>
          <option value={OpportunityStage.PROPOSAL}>{t('opportunities.stageProposal')}</option>
          <option value={OpportunityStage.NEGOTIATION}>{t('opportunities.stageNegotiation')}</option>
          <option value={OpportunityStage.CLOSED_WON}>{t('opportunities.stageClosedWon')}</option>
          <option value={OpportunityStage.CLOSED_LOST}>{t('opportunities.stageClosedLost')}</option>
        </select>
        <input
          type="text"
          value={assignedFilter}
          onChange={(e)=> setAssignedFilter(e.target.value)}
          placeholder={t('opportunities.filterAssigned')}
          className="border px-2 py-1 rounded text-sm"
        />
      </div>
      {loading && <div className="text-sm text-gray-500">{t('opportunities.loading')}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>{t('opportunities.perPage')}</label>
        <select value={per} onChange={(e)=> setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th><button className="underline" onClick={()=> { setSortKey('name'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('opportunities.name')} {sortKey==='name' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th><button className="underline" onClick={()=> { setSortKey('value'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('opportunities.value')} {sortKey==='value' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th>{t('opportunities.probability')}</th>
            <th><button className="underline" onClick={()=> { setSortKey('stage'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('opportunities.stage')} {sortKey==='stage' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th><button className="underline" onClick={()=> { setSortKey('expected_close_date'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('opportunities.closeDate')} {sortKey==='expected_close_date' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
            <th>{t('opportunities.depositAmount')}</th>
            <th>{t('opportunities.assignedTo')}</th>
            <th>{t('opportunities.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {view.map((c) => (
            <tr key={c.id} className="border-b">
              <td>{c.name}</td>
              <td>{c.value} {c.currency || 'USD'}</td>
              <td>{c.probability ?? '-'}%</td>
              <td>{c.stage}</td>
              <td>{c.expected_close_date || '-'}</td>
              <td>
                {(c.deposit_amount ?? 0) > 0
                  ? <span className={(c.deposit_paid ? 'text-green-700' : 'text-amber-600') + ' text-xs font-medium'}>
                      {c.deposit_paid ? '✓ ' : '⏳ '}{Number(c.deposit_amount).toFixed(2)}
                    </span>
                  : '-'}
              </td>
              <td>{c.assigned_to || '-'}</td>
              <td>
                <Link to={`${c.id}/edit`} className="text-blue-600 hover:underline mr-3">{t('opportunities.editBtn')}</Link>
                <button className="text-red-700" onClick={async () => { if (!confirm(t('opportunities.deleteConfirm'))) return; try { await deleteOpportunity(c.id); setItems((p)=>p.filter(x=>x.id!==c.id)); success(t('opportunities.deleted')) } catch(e:any){ toastError(getErrorMessage(e)) } }}>{t('opportunities.deleteBtn')}</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (<tr><td className="py-3 px-3" colSpan={7}>{t('opportunities.empty')}</td></tr>)}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
