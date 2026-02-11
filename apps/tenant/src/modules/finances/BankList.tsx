import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { listBancos, conciliarMovimiento } from './services'
import type { MovimientoBanco } from './types'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'

export default function BancoList() {
  const { t } = useTranslation(['finances', 'common'])
  const can = usePermission()
  const [items, setItems] = useState<MovimientoBanco[]>([])
  const [loading, setLoading] = useState(true)
  const { success, error } = useToast()

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')
  const [tipo, setTipo] = useState<'' | 'ingreso' | 'egreso'>('')
  const [conciliado, setConciliado] = useState<'' | 'true' | 'false'>('')
  const [per, setPer] = useState(25)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await listBancos()
      setItems(data)
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const filtered = useMemo(() => items.filter(m => {
    if (desde && m.fecha < desde) return false
    if (hasta && m.fecha > hasta) return false
    if (tipo && m.tipo !== tipo) return false
    if (conciliado === 'true' && !m.conciliado) return false
    if (conciliado === 'false' && m.conciliado) return false
    if (q) {
      const search = q.toLowerCase()
      const matches =
        m.concepto.toLowerCase().includes(search) ||
        (m.banco || '').toLowerCase().includes(search) ||
        (m.numero_cuenta || '').toLowerCase().includes(search)
      if (!matches) return false
    }
    return true
  }), [items, desde, hasta, tipo, conciliado, q])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(filtered, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const handleConciliar = async (id: number | string) => {
    try {
      await conciliarMovimiento(id)
      setItems(prev => prev.map(m => m.id === id ? { ...m, conciliado: true } : m))
      success(t('finances:messages.reconciled'))
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const totalPendiente = filtered
    .filter(m => !m.conciliado)
    .reduce((sum, m) => sum + m.monto, 0)

  const totalConciliado = filtered
    .filter(m => m.conciliado)
    .reduce((sum, m) => sum + m.monto, 0)

  if (!can('finances:read')) {
    return <PermissionDenied permission="finances:read" />
  }

  if (loading) return <div className="p-4 text-sm text-gray-500">{t('common.loading')}</div>

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-4">{t('finances:bankTransactions')}</h2>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <div className="text-sm text-gray-600">{t('finances:pending')}</div>
          <div className="text-xl font-bold text-yellow-700">${totalPendiente.toFixed(2)}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded p-3">
          <div className="text-sm text-gray-600">{t('finances:reconciled')}</div>
          <div className="text-xl font-bold text-green-700">${totalConciliado.toFixed(2)}</div>
        </div>
      </div>

      <div className="mb-3 flex gap-3 items-end text-sm flex-wrap">
        <div>
          <label className="block mb-1">{t('finances:filters.type')}</label>
          <select
            value={tipo}
            onChange={(e) => setTipo(e.target.value as any)}
            className="border px-2 py-1 rounded"
          >
            <option value="">{t('common.all')}</option>
            <option value="ingreso">{t('finances:type.income')}</option>
            <option value="egreso">{t('finances:type.expenses')}</option>
          </select>
        </div>
        <div>
          <label className="block mb-1">{t('finances:filters.reconciled')}</label>
          <select
            value={conciliado}
            onChange={(e) => setConciliado(e.target.value as any)}
            className="border px-2 py-1 rounded"
          >
            <option value="">{t('common.all')}</option>
            <option value="true">{t('common.yes')}</option>
            <option value="false">{t('common.no')}</option>
          </select>
        </div>
        <div>
          <label className="block mb-1">{t('finances:filters.from')}</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="border px-2 py-1 rounded"
          />
        </div>
        <div>
          <label className="block mb-1">{t('finances:filters.to')}</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="border px-2 py-1 rounded"
          />
        </div>
        <div>
          <label className="block mb-1">{t('common.search')}</label>
          <input
            placeholder={t('finances:filters.searchPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="border px-2 py-1 rounded"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 mb-2 text-sm">
        <label>{t('common.perPage')}</label>
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
            <tr className="text-left border-b bg-gray-50">
              <th className="py-2 px-3">{t('finances:table.date')}</th>
              <th className="py-2 px-3">{t('finances:table.bank')}</th>
              <th className="py-2 px-3">{t('finances:table.concept')}</th>
              <th className="py-2 px-3">{t('finances:table.type')}</th>
              <th className="py-2 px-3 text-right">{t('finances:table.amount')}</th>
              <th className="py-2 px-3 text-center">{t('finances:table.reconciled')}</th>
              <th className="py-2 px-3">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {view.map(m => (
              <tr key={m.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-3">{m.fecha}</td>
                <td className="py-2 px-3">
                  <div className="font-medium">{m.banco}</div>
                  <div className="text-xs text-gray-500">{m.numero_cuenta}</div>
                </td>
                <td className="py-2 px-3">{m.concepto}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    m.tipo === 'ingreso'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {m.tipo === 'ingreso' ? t('finances:type.income') : t('finances:type.expenses')}
                  </span>
                </td>
                <td className={`py-2 px-3 text-right font-medium ${
                  m.tipo === 'ingreso' ? 'text-green-700' : 'text-red-700'
                }`}>
                  {m.tipo === 'ingreso' ? '+' : '-'}${m.monto.toFixed(2)}
                </td>
                <td className="py-2 px-3 text-center">
                  {m.conciliado ? (
                    <span className="inline-block w-5 h-5 bg-green-500 rounded-full text-white text-xs leading-5">✓</span>
                  ) : (
                    <span className="inline-block w-5 h-5 bg-gray-300 rounded-full"></span>
                  )}
                </td>
                <td className="py-2 px-3">
                  {!m.conciliado && can('finances:update') && (
                    <button
                      onClick={() => handleConciliar(m.id)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      {t('finances:actions.reconcile')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {view.length === 0 && (
              <tr>
                <td className="py-3 px-3 text-center text-gray-500" colSpan={7}>
                  {t('finances:empty')}
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
