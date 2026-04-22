import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import { listInvoices, deleteInvoice, markInvoiceAsPaid, clearInvoicesCache, type Invoice } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import InvoiceStatusBadge from './components/FacturaStatusBadge'
import { useCurrency } from '../../hooks/useCurrency'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'

function sortInvoices(items: Invoice[]): Invoice[] {
  const parseNumber = (value?: string | number) => {
    if (value === undefined || value === null) return null
    if (typeof value === 'number') return Number.isFinite(value) ? value : null
    const match = value.match(/(\d+)(?!.*\d)/)
    if (!match) return null
    const n = Number(match[1])
    return Number.isFinite(n) ? n : null
  }

  const parseDate = (value?: string) => {
    const ts = value ? Date.parse(value) : NaN
    return Number.isNaN(ts) ? null : ts
  }

  return [...items].sort((a, b) => {
    const na = parseNumber(a.number)
    const nb = parseNumber(b.number)
    if (nb !== null || na !== null) {
      if (nb === null) return 1
      if (na === null) return -1
      if (nb !== na) return nb - na
    }

    const da = parseDate(a.issue_date)
    const db = parseDate(b.issue_date)
    if (da !== null && db !== null && db !== da) return db - da

    return String(b.id).localeCompare(String(a.id))
  })
}

export default function InvoicesList() {
  const { t } = useTranslation()
  const { formatCurrency } = useCurrency()
  const can = usePermission()
  const [items, setItems] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [markTarget, setMarkTarget] = useState<Invoice | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Invoice | null>(null)
  const [status, setStatus] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    const loadInvoices = async () => {
      try {
        setLoading(true)
        setErrMsg(null)
        const invoices = await listInvoices()
        setItems(sortInvoices(invoices))
      } catch (e: any) {
        const message = getErrorMessage(e)
        setErrMsg(message)
        toastError(message)
      } finally {
        setLoading(false)
      }
    }

    loadInvoices()
  }, [toastError])

  const filtered = useMemo(() => {
    const res = items.filter((invoice) => {
      if (status && (invoice.status || '') !== status) return false
      if (dateFrom && (invoice.issue_date || '') < dateFrom) return false
      if (dateTo && (invoice.issue_date || '') > dateTo) return false
      if (query && !(`${invoice.id}`.includes(query) || (invoice.status || '').toLowerCase().includes(query.toLowerCase()))) {
        return false
      }
      return true
    })
    return sortInvoices(res)
  }, [items, status, dateFrom, dateTo, query])

  const pendingCount = useMemo(
    () => items.filter((invoice) => (invoice.status || '').toLowerCase() === 'pending_payment').length,
    [items]
  )

  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  const markPaid = async () => {
    if (!markTarget) return
    try {
      await markInvoiceAsPaid(markTarget.id)
      clearInvoicesCache()
      setItems((prev) => prev.map((item) => (item.id === markTarget.id ? { ...item, status: 'issued' } : item)))
      success(t('billing.markedAsPaid'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setMarkTarget(null)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteInvoice(deleteTarget.id)
      clearInvoicesCache()
      setItems((prev) => prev.filter((item) => item.id !== deleteTarget.id))
      success(t('billing.deleted'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setDeleteTarget(null)
    }
  }

  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}>
        <BackButton onClick={() => nav(-1)} />
      </div>
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">{t('nav.invoicing')}</h2>
        <div className="flex gap-2">
          {can('billing:create') && (
            <ProtectedButton permission="billing:create" variant="primary" onClick={() => nav('nueva')}>
              {t('common.new')}
            </ProtectedButton>
          )}
        </div>
      </div>

      {pendingCount > 0 && (
        <button
          onClick={() => setStatus(status === 'pending_payment' ? '' : 'pending_payment')}
          className={`mb-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors
            ${status === 'pending_payment'
              ? 'bg-amber-100 border-amber-400 text-amber-800'
              : 'bg-white border-amber-300 text-amber-700 hover:bg-amber-50'}`}
        >
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-400 text-white text-xs font-bold">
            {pendingCount}
          </span>
          {t('billing.filterPending')}
          {status === 'pending_payment' && <span className="text-amber-500">✕</span>}
        </button>
      )}

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2 block">{t('common.status')}</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="border px-2 py-1 rounded text-sm">
            <option value="">{t('common.all')}</option>
            <option value="draft">{t('billing.status.draft')}</option>
            <option value="issued">{t('billing.status.issued')}</option>
            <option value="pending_payment">{t('billing.status.pending_payment')}</option>
            <option value="voided">{t('billing.status.voided')}</option>
          </select>
        </div>
        <div>
          <label className="text-sm mr-2 block">{t('common.from')}</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
        <div>
          <label className="text-sm mr-2 block">{t('common.to')}</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
        <div>
          <label className="text-sm mr-2 block">{t('common.search')}</label>
          <input
            placeholder={t('billing.searchPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>{t('common.date')}</th>
            <th>{t('common.total')}</th>
            <th>{t('common.status')}</th>
            <th>{t('common.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {view.map((invoice) => (
            <tr key={invoice.id} className="border-b">
              <td>{invoice.issue_date ? new Date(invoice.issue_date).toLocaleDateString() : '-'}</td>
              <td>
                {typeof invoice.total === 'number' && !Number.isNaN(invoice.total)
                  ? formatCurrency(invoice.total)
                  : '-'}
              </td>
              <td><InvoiceStatusBadge status={invoice.status} /></td>
              <td className="flex gap-2 items-center">
                {(invoice.status || '').toLowerCase() === 'pending_payment' ? (
                  <>
                    {can('billing:read') && (
                      <Link to={`${invoice.id}/editar`} className="text-blue-600 hover:underline">
                        {t('common.view') || 'View'}
                      </Link>
                    )}
                    {can('billing:update') && (
                      <ProtectedButton permission="billing:update" variant="ghost" onClick={() => setMarkTarget(invoice)}>
                        {t('billing.markAsPaid')}
                      </ProtectedButton>
                    )}
                  </>
                ) : ['issued', 'posted', 'confirmed'].includes((invoice.status || '').toLowerCase()) ? (
                  <>
                    {can('billing:read') && (
                      <Link to={`${invoice.id}/editar`} className="text-blue-600 hover:underline">
                        {t('common.view') || 'View'}
                      </Link>
                    )}
                    <span className="text-gray-500 text-sm">{t('common.readonly') || 'Read-only'}</span>
                  </>
                ) : (
                  <>
                    {can('billing:update') && (
                      <Link to={`${invoice.id}/editar`} className="text-blue-600 hover:underline">
                        {t('common.edit')}
                      </Link>
                    )}
                  </>
                )}
                {can('billing:delete') && (
                  <ProtectedButton permission="billing:delete" variant="ghost" onClick={() => setDeleteTarget(invoice)}>
                    {t('common.delete')}
                  </ProtectedButton>
                )}
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr>
              <td className="py-3 px-3" colSpan={5}>
                {t('common.noRecords')}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />

      {markTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">{t('billing.confirmMarkAsPaid')}</h3>
            <p className="text-sm text-slate-600 mb-5">
              {t('billing.invoiceNumber')}: {markTarget.number || markTarget.id}
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setMarkTarget(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">
                {t('common.cancel')}
              </button>
              <button onClick={markPaid} className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm">
                {t('billing.markAsPaid')}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">{t('billing.deleteConfirm')}</h3>
            <p className="text-sm text-slate-600 mb-5">
              {t('billing.invoiceNumber')}: {deleteTarget.number || deleteTarget.id}
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">
                {t('common.cancel')}
              </button>
              <button onClick={handleDelete} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
