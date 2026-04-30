import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getCuentaMayor, listCuentas, type CuentaMayor, type PlanCuenta } from '../services'

function toNumber(value: number | string | null | undefined) {
  const n = Number(value ?? 0)
  return Number.isFinite(n) ? n : 0
}

function fmt(value: number | string | null | undefined) {
  return toNumber(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function LibroMayor() {
  const { t } = useTranslation()
  const today = useMemo(() => new Date().toISOString().slice(0, 10), [])
  const firstOfYear = useMemo(() => `${new Date().getFullYear()}-01-01`, [])
  const [cuentas, setCuentas] = useState<PlanCuenta[]>([])
  const [cuentaId, setCuentaId] = useState('')
  const [fechaDesde, setFechaDesde] = useState(firstOfYear)
  const [fechaHasta, setFechaHasta] = useState(today)
  const [ledger, setLedger] = useState<CuentaMayor | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listCuentas()
      .then((items) => {
        if (cancelled) return
        setCuentas(items)
        setCuentaId((current) => current || items[0]?.id || '')
      })
      .catch(() => {
        if (!cancelled) setError(t('accounting.errors.loadTransactions'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [t])

  useEffect(() => {
    if (!cuentaId) {
      setLedger(null)
      return
    }
    let cancelled = false
    setLoading(true)
    getCuentaMayor(cuentaId, fechaDesde, fechaHasta)
      .then((data) => {
        if (!cancelled) {
          setLedger(data)
          setError(null)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLedger(null)
          setError(t('accounting.errors.loadTransactions'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [cuentaId, fechaDesde, fechaHasta, t])

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <h2 className="font-semibold text-lg flex-1">{t('accounting.generalLedger.title')}</h2>
        <label className="text-sm">
          <span className="block text-gray-500 mb-1">{t('common.account')}</span>
          <select
            value={cuentaId}
            onChange={(event) => setCuentaId(event.target.value)}
            className="border rounded px-2 py-1 min-w-64"
          >
            <option value="">{t('accounting.generalLedger.selectAccount')}</option>
            {cuentas.map((cuenta) => (
              <option key={cuenta.id} value={cuenta.id}>
                {cuenta.codigo} - {cuenta.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-gray-500 mb-1">{t('common.from')}</span>
          <input
            type="date"
            value={fechaDesde}
            onChange={(event) => setFechaDesde(event.target.value)}
            className="border rounded px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-gray-500 mb-1">{t('common.to')}</span>
          <input
            type="date"
            value={fechaHasta}
            onChange={(event) => setFechaHasta(event.target.value)}
            className="border rounded px-2 py-1"
          />
        </label>
      </div>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && <div className="text-sm text-gray-500">{t('accounting.generalLedger.loading')}</div>}

      {!loading && ledger && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="border rounded p-3">
              <div className="text-xs text-gray-500">{t('accounting.generalLedger.initialBalance')}</div>
              <div className="font-mono font-semibold">{fmt(ledger.saldo_inicial)}</div>
            </div>
            <div className="border rounded p-3">
              <div className="text-xs text-gray-500">{t('accounting.generalLedger.totalMovement')}</div>
              <div className="font-mono font-semibold">{fmt(toNumber(ledger.total_debe) - toNumber(ledger.total_haber))}</div>
            </div>
            <div className="border rounded p-3">
              <div className="text-xs text-gray-500">{t('accounting.generalLedger.finalBalance')}</div>
              <div className="font-mono font-semibold">{fmt(ledger.saldo_final)}</div>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="py-2 pr-3">{t('common.date')}</th>
                  <th className="py-2 pr-3">{t('accounting.journalEntries.columns.number')}</th>
                  <th className="py-2 pr-3">{t('common.description')}</th>
                  <th className="py-2 pr-3 text-right">{t('accounting.journalEntries.columns.debit')}</th>
                  <th className="py-2 pr-3 text-right">{t('accounting.journalEntries.columns.credit')}</th>
                  <th className="py-2 text-right">{t('accounting.generalLedger.columns.balance')}</th>
                </tr>
              </thead>
              <tbody>
                {ledger.movimientos.map((mov, index) => (
                  <tr key={`${mov.asiento_numero}-${index}`} className="border-b">
                    <td className="py-2 pr-3 whitespace-nowrap">{mov.fecha}</td>
                    <td className="py-2 pr-3 whitespace-nowrap">{mov.asiento_numero}</td>
                    <td className="py-2 pr-3">{mov.descripcion}</td>
                    <td className="py-2 pr-3 text-right font-mono">{fmt(mov.debe)}</td>
                    <td className="py-2 pr-3 text-right font-mono">{fmt(mov.haber)}</td>
                    <td className="py-2 text-right font-mono">{fmt(mov.saldo)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="font-semibold">
                  <td className="py-2 pr-3" colSpan={3}>{t('common.total')}</td>
                  <td className="py-2 pr-3 text-right font-mono">{fmt(ledger.total_debe)}</td>
                  <td className="py-2 pr-3 text-right font-mono">{fmt(ledger.total_haber)}</td>
                  <td className="py-2 text-right font-mono">{fmt(ledger.saldo_final)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
