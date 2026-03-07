import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listGastos, removeGasto, getGastoStats, getProductionDetail, type Gasto, type GastoStats, type ProductionDetail } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import StatsCard from './components/StatsCard'

export default function GastosList() {
  const { t } = useTranslation(['expenses', 'common'])
  const can = usePermission()
  const formatUnitCost = (value: number) => `$${value < 1 ? value.toFixed(6) : value.toFixed(4)}`
  const [items, setItems] = useState<Gasto[]>([])
  const [stats, setStats] = useState<GastoStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState<'date' | 'amount'>('date')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [per, setPer] = useState(10)
  const [sourceFilter, setSourceFilter] = useState<'all' | 'manual' | 'production'>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detailData, setDetailData] = useState<ProductionDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [gastosData, statsData] = await Promise.all([
          listGastos(),
          getGastoStats(desde, hasta)
        ])
        setItems(gastosData)
        setStats(statsData)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [desde, hasta])

  const isProductionExpense = (expense: Gasto) =>
    expense.category === 'production' || String(expense.invoice_number || '').startsWith('PROD-')

  const filtered = useMemo(() => items.filter(v => {
    if (desde && v.date < desde) return false
    if (hasta && v.date > hasta) return false
    if (sourceFilter === 'production' && !isProductionExpense(v)) return false
    if (sourceFilter === 'manual' && isProductionExpense(v)) return false
    if (q) {
      const search = q.toLowerCase()
      const matches =
        String(v.id).includes(search) ||
        (v.concept || '').toLowerCase().includes(search) ||
        String(v.invoice_number || '').toLowerCase().includes(search)
      if (!matches) return false
    }
    return true
  }), [items, desde, hasta, q, sourceFilter])

  const totals = useMemo(() => {
    let all = 0
    let production = 0
    let manual = 0
    for (const expense of filtered) {
      const amount = Number(expense.amount || 0)
      all += amount
      if (isProductionExpense(expense)) production += amount
      else manual += amount
    }
    return { all, production, manual }
  }, [filtered])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      let av, bv
      if (sortKey === 'date') {
        av = a.date || ''
        bv = b.date || ''
      } else if (sortKey === 'amount') {
        av = a.amount || 0
        bv = b.amount || 0
        return ((av as number) - (bv as number)) * dir
      } else {
        av = (a as any)[sortKey] || ''
        bv = (b as any)[sortKey] || ''
      }
      return (av < bv ? -1 : av > bv ? 1 : 0) * dir
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const toggleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  async function toggleDetail(expense: Gasto) {
    if (expandedId === expense.id) {
      setExpandedId(null)
      setDetailData(null)
      return
    }
    setExpandedId(expense.id)
    setDetailData(null)
    setDetailLoading(true)
    try {
      const detail = await getProductionDetail(expense.id)
      setDetailData(detail)
      setItems((prev) => prev.map((item) => (
        item.id === expense.id
          ? { ...item, amount: detail.total_cost }
          : item
      )))
    } catch {
      setDetailData(null)
    } finally {
      setDetailLoading(false)
    }
  }

  function exportCSV(rows: Gasto[]) {
    const header = ['id', 'date', 'concept', 'amount']
    const body = rows.map(r => [
      r.id,
      r.date,
      r.concept || '',
      r.amount
    ])
    const csv = [header, ...body].map(line => line.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'gastos.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!can('expenses:read')) {
    return <PermissionDenied permission="expenses:read" />
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
         <h2 className="font-semibold text-lg">{t('expenses:title')}</h2>
         <div className="flex gap-2">
           {can('expenses:read') && (
             <button
               className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
               onClick={() => exportCSV(view)}
             >
               {t('exportCsv', { ns: 'common' })}
             </button>
           )}
           {can('expenses:create') && (
             <button
               className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
               onClick={() => nav('nuevo')}
             >
               {t('expenses:new')}
             </button>
           )}
         </div>
       </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <StatsCard
            title={t('expenses:stats.total')}
            value={`$${stats.total.toFixed(2)}`}
            color="blue"
          />
          <StatsCard
            title={t('expenses:stats.pending')}
            value={`$${stats.pending.toFixed(2)}`}
            color="red"
          />
          <StatsCard
            title={t('expenses:stats.production')}
            value={`$${totals.production.toFixed(2)}`}
            color="green"
          />
          <StatsCard
            title={t('expenses:stats.manual')}
            value={`$${totals.manual.toFixed(2)}`}
            color="yellow"
          />
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2">{t('expenses:filters.from')}</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">{t('expenses:filters.to')}</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">{t('search', { ns: 'common' })}</label>
          <input
            placeholder={t('expenses:filters.conceptPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          />
        </div>
        <div>
          <label className="text-sm mr-2">{t('expenses:filters.source')}</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as 'all' | 'manual' | 'production')}
            className="border px-2 py-1 rounded text-sm"
          >
            <option value="all">{t('expenses:filters.sourceAll')}</option>
            <option value="manual">{t('expenses:filters.sourceManual')}</option>
            <option value="production">{t('expenses:filters.sourceProduction')}</option>
          </select>
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">{t('loadingText', { ns: 'common' })}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>{t('perPage', { ns: 'common' })}</label>
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
                  {t('expenses:table.date')} {sortKey === 'date' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">{t('expenses:table.concept')}</th>
              <th className="py-2 px-2">{t('expenses:table.source')}</th>
              <th className="py-2 px-2">{t('expenses:table.paymentStatus', 'Estado pago')}</th>
              <th className="py-2 px-2">
                <button className="underline" onClick={() => toggleSort('amount')}>
                  {t('expenses:table.amount')} {sortKey === 'amount' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </button>
              </th>
              <th className="py-2 px-2">{t('actionsLabel', { ns: 'common' })}</th>
            </tr>
          </thead>
          <tbody>
            {view.map((v) => (
              <React.Fragment key={v.id}>
              <tr className="border-b hover:bg-gray-50">
                <td className="py-2 px-2">{v.date}</td>
                <td className="py-2 px-2">
                  {isProductionExpense(v) ? (
                    <button
                      className="text-left text-blue-600 hover:underline flex items-center gap-1"
                      onClick={() => toggleDetail(v)}
                    >
                      <span className={`inline-block transition-transform ${expandedId === v.id ? 'rotate-90' : ''}`}>▶</span>
                      {v.concept || '-'}
                    </button>
                  ) : (
                    v.concept || '-'
                  )}
                </td>
                <td className="py-2 px-2">
                  {isProductionExpense(v) ? (
                    <span className="inline-flex rounded-full px-2 py-1 text-xs font-medium bg-green-100 text-green-700 border border-green-200">
                      {t('expenses:source.production')}
                    </span>
                  ) : (
                    <span className="inline-flex rounded-full px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
                      {t('expenses:source.manual')}
                    </span>
                  )}
                </td>
                <td className="py-2 px-2">
                  {v.status === 'paid' ? (
                    <span className="inline-flex rounded-full px-2 py-1 text-xs font-medium bg-green-100 text-green-700 border border-green-200">
                      {t('expenses:paymentStatus.paid', 'Pagado')}
                    </span>
                  ) : v.status === 'partial' ? (
                    <span className="inline-flex rounded-full px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-700 border border-yellow-200">
                      {t('expenses:paymentStatus.partial', 'Parcial')} — ${(v.pending_amount ?? v.amount).toFixed(2)} pdte
                    </span>
                  ) : v.status === 'cancelled' ? (
                    <span className="inline-flex rounded-full px-2 py-1 text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
                      {t('expenses:paymentStatus.cancelled', 'Anulado')}
                    </span>
                  ) : (
                    <span className="inline-flex rounded-full px-2 py-1 text-xs font-medium bg-red-100 text-red-700 border border-red-200">
                      {t('expenses:paymentStatus.pending', 'Pdt. pago')}
                    </span>
                  )}
                </td>
                <td className="py-2 px-2 font-medium">${v.amount.toFixed(2)}</td>
                <td className="py-2 px-2">
                  {!isProductionExpense(v) && can('expenses:update') && (
                    <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">
                      {t('edit', { ns: 'common' })}
                    </Link>
                  )}
                  {can('expenses:delete') && (
                    <button
                      className="text-red-700 hover:underline"
                      onClick={async () => {
                        if (!confirm(t('expenses:confirmDelete'))) return
                        try {
                          await removeGasto(v.id)
                          setItems((p) => p.filter(x => x.id !== v.id))
                          success(t('expenses:messages.deleted'))
                        } catch (e: any) {
                          toastError(getErrorMessage(e))
                        }
                      }}
                    >
                      {t('delete', { ns: 'common' })}
                    </button>
                  )}
                </td>
              </tr>
              {expandedId === v.id && isProductionExpense(v) && (
                <tr className="bg-blue-50">
                  <td colSpan={6} className="py-3 px-4">
                    {detailLoading ? (
                      <div className="text-sm text-gray-500">{t('expenses:detail.loadingDetail')}</div>
                    ) : detailData ? (
                      <div className="space-y-3">
                        <div className="text-sm font-semibold mb-2">
                          {detailData.recipe_name} — {t('expenses:detail.order')}: {detailData.order_number} — {t('expenses:detail.produced')}: {detailData.qty_produced}
                        </div>
                        <table className="w-full text-xs border">
                          <thead>
                            <tr className="bg-blue-100 text-left">
                              <th className="py-1 px-2">{t('expenses:detail.ingredient')}</th>
                              <th className="py-1 px-2">{t('expenses:detail.quantity')}</th>
                              <th className="py-1 px-2">{t('expenses:detail.unit')}</th>
                              <th className="py-1 px-2">{t('expenses:detail.unitCost')}</th>
                              <th className="py-1 px-2">{t('expenses:detail.subtotal')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detailData.lines.map((line, idx) => (
                              <tr key={idx} className="border-t">
                                <td className="py-1 px-2">{line.ingredient_name}</td>
                                <td className="py-1 px-2">{line.qty_consumed.toFixed(3)}</td>
                                <td className="py-1 px-2">{line.unit}</td>
                                <td className="py-1 px-2">{formatUnitCost(line.cost_unit)}</td>
                                <td className="py-1 px-2 font-medium">${line.cost_total.toFixed(2)}</td>
                              </tr>
                            ))}
                          </tbody>
                          <tfoot>
                            <tr className="border-t font-semibold bg-blue-100">
                              <td colSpan={4} className="py-1 px-2 text-right">{t('expenses:detail.materialsTotal')}:</td>
                              <td className="py-1 px-2">${detailData.materials_total.toFixed(2)}</td>
                            </tr>
                          </tfoot>
                        </table>
                        {detailData.indirect_costs.length > 0 && (
                          <table className="w-full text-xs border">
                            <thead>
                              <tr className="bg-amber-100 text-left">
                                <th className="py-1 px-2">{t('expenses:detail.indirectCost')}</th>
                                <th className="py-1 px-2">{t('expenses:detail.quantityApplied')}</th>
                                <th className="py-1 px-2">{t('expenses:detail.headcount')}</th>
                                <th className="py-1 px-2">{t('expenses:detail.rateApplied')}</th>
                                <th className="py-1 px-2">{t('expenses:detail.subtotal')}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {detailData.indirect_costs.map((line, idx) => (
                                <tr key={idx} className="border-t">
                                  <td className="py-1 px-2">
                                    {line.driver_name}
                                    {line.notes ? <div className="text-[11px] text-gray-500">{line.notes}</div> : null}
                                  </td>
                                  <td className="py-1 px-2">
                                    {line.qty_actual.toFixed(4)}
                                    {line.driver_unit ? ` ${line.driver_unit}` : ''}
                                  </td>
                                  <td className="py-1 px-2">{line.headcount_actual}</td>
                                  <td className="py-1 px-2">${line.rate_applied.toFixed(4)}</td>
                                  <td className="py-1 px-2 font-medium">${line.cost_total.toFixed(2)}</td>
                                </tr>
                              ))}
                            </tbody>
                            <tfoot>
                              <tr className="border-t font-semibold bg-amber-100">
                                <td colSpan={4} className="py-1 px-2 text-right">{t('expenses:detail.indirectTotal')}:</td>
                                <td className="py-1 px-2">${detailData.indirect_total.toFixed(2)}</td>
                              </tr>
                            </tfoot>
                          </table>
                        )}
                        <table className="w-full text-xs border">
                          <tfoot>
                            <tr className="font-semibold bg-slate-100">
                              <td colSpan={4} className="py-2 px-2 text-right">{t('expenses:detail.grandTotal')}:</td>
                              <td className="py-2 px-2">${detailData.total_cost.toFixed(2)}</td>
                            </tr>
                          </tfoot>
                        </table>
                      </div>
                    ) : (
                      <div className="text-sm text-red-500">{t('expenses:detail.errorLoadingDetail')}</div>
                    )}
                  </td>
                </tr>
              )}
              </React.Fragment>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={5}>
                  {t('expenses:empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
