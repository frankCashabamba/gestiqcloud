import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import { listPurchases, removePurchase, type Purchase } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import StatusBadge from '../sales/components/StatusBadge'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'

export default function PurchasesList() {
  const { t } = useTranslation(['purchases', 'common'])
  const can = usePermission()
  const [items, setItems] = useState<Purchase[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [status, setStatus] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState<'date' | 'total' | 'status' | 'supplier_name'>('date')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [per, setPer] = useState(10)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listPurchases())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [toastError])

  const filtered = useMemo(() => items.filter(v => {
    if (status && v.status !== status) return false
    if (from && v.date < from) return false
    if (to && v.date > to) return false
    if (q) {
      const search = q.toLowerCase()
      const matches =
        String(v.id).includes(search) ||
        (v.number || '').toLowerCase().includes(search) ||
        (v.supplier_name || '').toLowerCase().includes(search) ||
        v.status.toLowerCase().includes(search)
      if (!matches) return false
    }
    return true
  }), [items, status, from, to, q])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = (a as any)[sortKey] || ''
      const bv = (b as any)[sortKey] || ''
      if (sortKey === 'total') return ((av as number) - (bv as number)) * dir
      return (av < bv ? -1 : av > bv ? 1 : 0) * dir
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  function exportCSV(rows: Purchase[]) {
    const esc = (v: string | number | undefined | null) => {
      const s = String(v ?? '')
      return s.includes(',') || s.includes('"') || s.includes('\n')
        ? `"${s.replace(/"/g, '""')}"`
        : s
    }
    const header = ['id', 'number', 'date', 'delivery_date', 'supplier', 'subtotal', 'taxes', 'total', 'status', 'notes']
    const body = rows.map((r) => [
      r.id, r.number, r.date, r.delivery_date, r.supplier_name,
      r.subtotal, r.taxes, r.total, r.status, r.notes,
    ].map(esc))
    const csv = [header, ...body].map((line) => line.join(',')).join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `purchases-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">{t('purchases:title')}</h2>
        <div className="flex gap-2">
          <ProtectedButton
            permission="purchases:read"
            variant="secondary"
            onClick={() => exportCSV(view)}
          >
            {t('purchases:exportCsv')}
          </ProtectedButton>
          {can('purchases:create') && (
            <ProtectedButton
              permission="purchases:create"
              variant="primary"
              onClick={() => nav('new')}
            >
              {t('purchases:new')}
            </ProtectedButton>
          )}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2">{t('purchases:status')}</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          >
            <option value="">{t('purchases:all')}</option>
            <option value="draft">{t('purchases:draft')}</option>
            <option value="sent">{t('purchases:sent')}</option>
            <option value="received">{t('purchases:received')}</option>
            <option value="cancelled">{t('purchases:cancelled')}</option>
          </select>
        </div>
        <div>
          <label className="text-sm mr-2">{t('purchases:from')}</label>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">{t('purchases:to')}</label>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">{t('purchases:search')}</label>
          <input
            placeholder={t('purchases:searchPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">{t('purchases:loading')}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>{t('purchases:perPage')}</label>
        <select
          value={per}
          onChange={(e) => setPer(Number(e.target.value))}
          className="border px-2 py-1 rounded"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('date')}>
                  {t('purchases:date')} {sortKey === 'date' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">{t('purchases:number')}</th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('supplier_name')}>
                  {t('purchases:supplier')} {sortKey === 'supplier_name' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('total')}>
                  {t('purchases:total')} {sortKey === 'total' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('status')}>
                  {t('purchases:status')} {sortKey === 'status' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">{t('purchases:actions')}</th>
            </tr>
          </thead>
          <tbody>
            {view.map((v) => (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-2">{v.date}</td>
                <td className="py-2 px-2">{v.number || '-'}</td>
                <td className="py-2 px-2">{v.supplier_name || '-'}</td>
                <td className="py-2 px-2">{v.total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td className="py-2 px-2">
                  <StatusBadge status={v.status} />
                </td>
                <td className="py-2 px-2">
                  {can('purchases:read') && (
                    <Link to={`${v.id}`} className="text-blue-600 hover:underline mr-3">
                      {t('purchases:view')}
                    </Link>
                  )}
                  {v.status === 'draft' && can('purchases:update') && (
                    <Link to={`${v.id}/edit`} className="text-blue-600 hover:underline mr-3">
                      {t('purchases:edit')}
                    </Link>
                  )}
                  {can('purchases:delete') && (
                    <button
                      className="text-red-700 hover:underline text-sm"
                      onClick={() => setDeleteId(String(v.id))}
                    >
                      {t('purchases:delete')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={6}>
                  {t('purchases:empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="font-semibold text-gray-900 mb-1">{t('purchases:deleteConfirm')}</h3>
            <p className="text-sm text-gray-500 mb-5">{t('purchases:deleteConfirmBody')}</p>
            <div className="flex gap-3 justify-end">
              <button
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                onClick={() => setDeleteId(null)}
              >
                {t('common:cancel')}
              </button>
              <button
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700"
                onClick={async () => {
                  const currentId = deleteId
                  setDeleteId(null)
                  try {
                    await removePurchase(currentId)
                    setItems((p) => p.filter((x) => String(x.id) !== currentId))
                    success(t('purchases:deleted'))
                  } catch (e: any) {
                    toastError(getErrorMessage(e))
                  }
                }}
              >
                {t('purchases:delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
