import React, { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMovimientos } from '../hooks/useMovimientos'

const PAGE_SIZE = 20

export function LibroDiario() {
  const { t } = useTranslation()
  const { asientos, loading, error } = useMovimientos()

  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    if (!q) return asientos
    return asientos.filter(
      (a) =>
        a.concepto.toLowerCase().includes(q) ||
        a.fecha.includes(q) ||
        a.apuntes.some((ap) => ap.cuenta.includes(q) || ap.description?.toLowerCase().includes(q)),
    )
  }, [asientos, search])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleSearch = (v: string) => {
    setSearch(v)
    setPage(0)
  }

  if (loading) {
    return (
      <div className="p-4 animate-pulse space-y-3">
        {[0, 1, 2, 3].map((i) => <div key={i} className="h-20 rounded-lg bg-gray-100" />)}
      </div>
    )
  }

  if (error) {
    return (
      <div className="m-4 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <h2 className="font-semibold text-lg flex-1">{t('accounting.nav.journal')}</h2>
        <input
          type="search"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder={t('common.search')}
          className="border rounded px-3 py-1.5 text-sm w-full sm:w-64 focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {pageItems.length === 0 ? (
        <div className="text-center text-gray-400 py-12 text-sm">
          {search ? t('common.noResults') : t('accounting.journalEntries.empty')}
        </div>
      ) : (
        <div className="space-y-4">
          {pageItems.map((a) => (
            <div key={a.id} className="rounded-lg border border-gray-200 overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 flex items-center gap-3 border-b border-gray-200">
                <span className="text-xs text-gray-400 font-mono">{a.fecha.slice(0, 10)}</span>
                <span className="text-sm font-medium text-gray-800 truncate">{a.concepto}</span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                    <th className="px-4 py-1.5 font-medium">{t('common.account')}</th>
                    <th className="px-4 py-1.5 font-medium">{t('common.description')}</th>
                    <th className="px-4 py-1.5 font-medium text-right">{t('accounting.journalEntries.columns.debit')}</th>
                    <th className="px-4 py-1.5 font-medium text-right">{t('accounting.journalEntries.columns.credit')}</th>
                  </tr>
                </thead>
                <tbody>
                  {a.apuntes.map((ap, i) => (
                    <tr key={i} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-1.5 font-mono text-xs text-blue-700">{ap.cuenta}</td>
                      <td className="px-4 py-1.5 text-gray-600 truncate max-w-xs">{ap.description}</td>
                      <td className="px-4 py-1.5 text-right font-mono text-gray-700">
                        {ap.debe > 0 ? ap.debe.toFixed(2) : ''}
                      </td>
                      <td className="px-4 py-1.5 text-right font-mono text-gray-700">
                        {ap.haber > 0 ? ap.haber.toFixed(2) : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
          <span>
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filtered.length)} {t('common.of')} {filtered.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-40"
            >
              ‹
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-40"
            >
              ›
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
