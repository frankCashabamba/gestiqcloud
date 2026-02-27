import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useToast } from '../../shared/toast'
import { listStatements, getSummary, BankStatement, ReconciliationSummary } from './services'
import ImportForm from './ImportForm'

const statusStyles: Record<string, { bg: string; text: string }> = {
  imported: { bg: 'bg-blue-100', text: 'text-blue-800' },
  processing: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
  reconciled: { bg: 'bg-green-100', text: 'text-green-800' },
  partial: { bg: 'bg-orange-100', text: 'text-orange-800' },
}

function formatAmount(value: number): string {
  return `$${value.toFixed(2)}`
}

export default function ReconciliationDashboard() {
  const navigate = useNavigate()
  const { t } = useTranslation(['reconciliation', 'common'])
  const { error: showError } = useToast()
  const [loading, setLoading] = useState(true)
  const [statements, setStatements] = useState<BankStatement[]>([])
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null)
  const [showImport, setShowImport] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [stmtData, summaryData] = await Promise.all([
        listStatements(),
        getSummary(),
      ])
      setStatements(stmtData.items)
      setSummary(summaryData)
    } catch {
      showError(t('reconciliation:errorLoading'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="p-6">{t('reconciliation:loading')}</div>

  const matchedPct = summary && summary.total_lines > 0
    ? Math.round((summary.matched / summary.total_lines) * 100)
    : 0

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{t('reconciliation:title')}</h1>
        <button
          onClick={() => setShowImport(!showImport)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {showImport ? t('reconciliation:cancel') : t('reconciliation:importStatement')}
        </button>
      </div>

      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">{t('reconciliation:totalStatements')}</p>
            <p className="text-2xl font-bold">{summary.total_statements}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">{t('reconciliation:reconciled')}</p>
            <p className="text-2xl font-bold text-green-600">{matchedPct}%</p>
            <p className="text-xs text-gray-400">{summary.matched} de {summary.total_lines} líneas</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">{t('reconciliation:unreconciled')}</p>
            <p className="text-2xl font-bold text-red-600">{summary.unmatched}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">{t('reconciliation:autoManual')}</p>
            <p className="text-2xl font-bold text-indigo-600">
              {summary.auto_matched} / {summary.manual_matched}
            </p>
          </div>
        </div>
      )}

      {showImport && (
        <ImportForm
          onSuccess={() => {
            setShowImport(false)
            loadData()
          }}
          onCancel={() => setShowImport(false)}
        />
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('reconciliation:bank')}</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('reconciliation:account')}</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('reconciliation:date')}</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('reconciliation:status')}</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('reconciliation:reconciledCol')}</th>
              <th className="px-6 py-3 text-right text-sm font-semibold">{t('reconciliation:actions')}</th>
            </tr>
          </thead>
          <tbody>
            {statements.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  {t('reconciliation:noStatements')}
                </td>
              </tr>
            ) : (
              statements.map(stmt => {
                const cfg = statusStyles[stmt.status] ?? statusStyles.imported
                return (
                  <tr
                    key={stmt.id}
                    className="border-b hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(stmt.id)}
                  >
                    <td className="px-6 py-4 text-sm font-medium">{stmt.bank_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{stmt.account_number}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(stmt.statement_date).toLocaleDateString('es-PE')}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
                        {t(`reconciliation:statuses.${stmt.status}`)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {stmt.matched_count} / {stmt.total_transactions}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={e => {
                          e.stopPropagation()
                          navigate(stmt.id)
                        }}
                        className="text-sm px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
                      >
                        {t('reconciliation:viewDetail')}
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
