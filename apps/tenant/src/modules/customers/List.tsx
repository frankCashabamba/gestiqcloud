import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listClientes, removeCliente, type Cliente } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'

export default function ClientesList() {
  const { t } = useTranslation(['customers', 'common'])
  const can = usePermission()
  const [items, setItems] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [q, setQ] = useState('')

  useEffect(() => {
    (async () => {
      try { setLoading(true); setItems(await listClientes()) }
      catch (e: any) { const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
      finally { setLoading(false) }
    })()
  }, [])

  const [sortKey, setSortKey] = useState<'nombre'|'email'>('nombre')
  const [sortDir, setSortDir] = useState<'asc'|'desc'>('asc')
  const [per, setPer] = useState(10)
  const filtered = useMemo(() => items.filter(c => (c.name||'').toLowerCase().includes(q.toLowerCase()) || (c.email||'').toLowerCase().includes(q.toLowerCase())), [items,q])
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

  if (!can('customers:read')) {
    return <PermissionDenied permission="customers:read" />
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">{t('customers:title')}</h2>
        {can('customers:create') && (
          <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>{t('customers:new')}</button>
        )}
      </div>
      <input value={q} onChange={(e)=> setQ(e.target.value)} placeholder={t('customers:searchPlaceholder')} className="mb-3 w-full px-3 py-2 border rounded text-sm" />
      {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>{t('common.perPage')}</label>
        <select value={per} onChange={(e)=> setPer(Number(e.target.value))} className="border px-2 py-1 rounded">
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>
      <table className="min-w-full text-sm">
        <thead>
            <tr className="text-left border-b">
              <th><button className="underline" onClick={()=> { setSortKey('nombre'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('customers:table.name')} {sortKey==='nombre' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
              <th><button className="underline" onClick={()=> { setSortKey('email'); setSortDir(d=> d==='asc'?'desc':'asc') }}>{t('customers:table.email')} {sortKey==='email' ? (sortDir==='asc'?'▲':'▼') : ''}</button></th>
              <th>{t('customers:table.phone')}</th>
              <th>{t('customers:table.wholesale')}</th>
              <th>{t('common.actions')}</th>
            </tr>
          </thead>
        <tbody>
          {view.map((c) => (
            <tr key={c.id} className="border-b">
              <td>{c.name}</td>
              <td>{c.email || '-'}</td>
              <td>{c.phone || '-'}</td>
              <td>{c.is_wholesale ? t('common.yes') : t('common.no')}</td>
                <td>
                  {can('customers:update') && (
                    <Link to={`${c.id}/editar`} className="text-blue-600 hover:underline mr-3">{t('common.edit')}</Link>
                  )}
                  {can('customers:delete') && (
                    <button className="text-red-700" onClick={async () => { if (!confirm(t('customers:confirmDelete'))) return; try { await removeCliente(c.id); setItems((p)=>p.filter(x=>x.id!==c.id)); success(t('customers:messages.deleted')) } catch(e:any){ toastError(getErrorMessage(e)) } }}>{t('common.delete')}</button>
                  )}
                </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (<tr><td className="py-3 px-3" colSpan={4}>{t('customers:empty')}</td></tr>)}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
