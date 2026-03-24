import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listClientes, removeCliente, type Cliente } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import { BackButton } from '@ui'

function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  if (!active) return (
    <svg className="w-3.5 h-3.5 text-slate-300 inline ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4" />
    </svg>
  )
  return dir === 'asc'
    ? <svg className="w-3.5 h-3.5 text-blue-600 inline ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" /></svg>
    : <svg className="w-3.5 h-3.5 text-blue-600 inline ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
}

export default function ClientesList() {
  const { t } = useTranslation(['customers', 'common'])
  const can = usePermission()
  const [items, setItems] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [deleteId, setDeleteId] = useState<number | string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [q, setQ] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const data = await listClientes()
        if (!cancelled) setItems(data)
      } catch (e: any) {
        if (!cancelled) {
          const m = getErrorMessage(e)
          setErrMsg(m)
          toastError(m)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const [sortKey, setSortKey] = useState<'name' | 'email'>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(15)

  const filtered = useMemo(() =>
    items.filter(c =>
      (c.name || '').toLowerCase().includes(q.toLowerCase()) ||
      (c.email || '').toLowerCase().includes(q.toLowerCase()) ||
      (c.phone || '').toLowerCase().includes(q.toLowerCase())
    ),
    [items, q]
  )

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = String((a as any)[sortKey] || '').toLowerCase()
      const bv = String((b as any)[sortKey] || '').toLowerCase()
      return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const handleDelete = async () => {
    if (!deleteId) return
    const id = deleteId
    setDeleteId(null)
    try {
      await removeCliente(id)
      setItems(prev => prev.filter(x => x.id !== id))
      success(t('customers:messages.deleted'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  if (!can('customers:read')) {
    return <PermissionDenied permission="customers:read" />
  }

  return (
    <div className="p-4 space-y-4 max-w-7xl mx-auto">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">{t('customers:title')}</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {filtered.length} {filtered.length === 1 ? t('customers:countSingular', 'cliente') : t('customers:countPlural', 'clientes')}
            {q && ` · "${q}"`}
          </p>
        </div>
        {can('customers:create') && (
          <button
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl font-semibold text-sm shadow-sm transition-colors"
            onClick={() => nav('nuevo')}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            {t('customers:new')}
          </button>
        )}
      </div>

      {errMsg && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {errMsg}
        </div>
      )}

      {/* Toolbar */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm px-4 py-3 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-52 max-w-sm">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t('customers:searchPlaceholder')}
            className="w-full border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500 ml-auto">
          <span>{t('common:perPage')}</span>
          <select
            value={per}
            onChange={(e) => setPer(Number(e.target.value))}
            className="border border-slate-200 rounded-lg px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center gap-3 py-16 text-slate-400">
            <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">{t('common:loading')}</span>
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left">
                  <button
                    className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:text-slate-800 transition-colors"
                    onClick={() => toggleSort('name')}
                  >
                    {t('customers:table.name')}
                    <SortIcon active={sortKey === 'name'} dir={sortDir} />
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button
                    className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:text-slate-800 transition-colors"
                    onClick={() => toggleSort('email')}
                  >
                    {t('customers:table.email')}
                    <SortIcon active={sortKey === 'email'} dir={sortDir} />
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('customers:table.phone')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('customers:table.wholesale')}
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('common:actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {view.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-medium text-slate-900">{c.name}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{c.email || <span className="text-slate-300">—</span>}</td>
                  <td className="px-4 py-3 text-slate-600">{c.phone || <span className="text-slate-300">—</span>}</td>
                  <td className="px-4 py-3">
                    {c.is_wholesale ? (
                      <span className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold bg-violet-50 text-violet-700">
                        {t('common:yes')}
                      </span>
                    ) : (
                      <span className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold bg-slate-100 text-slate-500">
                        {t('common:no')}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1">
                      {can('customers:update') && (
                        <Link
                          to={`${c.id}/editar`}
                          className="px-3 py-1.5 rounded-lg text-sm font-medium text-blue-600 hover:bg-blue-50 transition-colors"
                        >
                          {t('common:edit')}
                        </Link>
                      )}
                      {can('customers:delete') && (
                        <button
                          className="px-3 py-1.5 rounded-lg text-sm font-medium text-rose-600 hover:bg-rose-50 transition-colors"
                          onClick={() => setDeleteId(c.id)}
                        >
                          {t('common:delete')}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {view.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-2 text-slate-400">
                      <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <p className="text-sm font-medium">
                        {q ? t('common:noResults') : t('customers:empty')}
                      </p>
                      {!q && can('customers:create') && (
                        <button
                          className="mt-2 text-sm text-blue-600 hover:underline font-medium"
                          onClick={() => nav('nuevo')}
                        >
                          + {t('customers:new')}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />

      {/* Delete modal */}
      {deleteId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setDeleteId(null)}>
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-start gap-3 mb-5">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-gray-900">{t('customers:confirmDelete')}</h3>
                <p className="text-sm text-gray-500 mt-0.5">{t('customers:confirmDeleteBody')}</p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                className="px-4 py-2 border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                onClick={() => setDeleteId(null)}
              >
                {t('common:cancel')}
              </button>
              <button
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-colors"
                onClick={() => void handleDelete()}
              >
                {t('common:delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
