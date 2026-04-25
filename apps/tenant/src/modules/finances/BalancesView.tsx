import React, { useEffect, useState } from 'react'
import { getSaldos } from './services'
import type { SaldosResumen } from './types'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BackButton } from '@ui'
import PageContainer from '../../components/PageContainer'

export default function SaldosView() {
  const { t } = useTranslation(['finances', 'common'])
  const [saldos, setSaldos] = useState<SaldosResumen | null>(null)
  const [loading, setLoading] = useState(true)
  const { error } = useToast()
  const nav = useNavigate()

  useEffect(() => {
    loadSaldos()
  }, [])

  const loadSaldos = async () => {
    try {
      setLoading(true)
      const data = await getSaldos()
      setSaldos(data)
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <PageContainer>
        <div className="text-gray-500">{t('finances:balances.loadingBalances')}</div>
      </PageContainer>
    )
  }

  if (!saldos) {
    return (
      <PageContainer>
        <div className="text-red-600">{t('finances:balances.errorLoadingBalances')}</div>
      </PageContainer>
    )
  }

  const cajaTotal = saldos.caja_total ?? 0
  const bancosTotal = saldos.bancos_total ?? 0
  const totalDisponible = saldos.total_disponible ?? 0
  const pendienteConciliar = saldos.pendiente_conciliar ?? 0

  return (
    <PageContainer>
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-2xl font-semibold">{t('finances:balances.title')}</h2>
          <p className="text-sm text-gray-600 mt-1">
            {t('finances:balances.lastUpdated')}: {new Date(saldos.ultimo_update).toLocaleString()}
          </p>
        </div>
        <button
          onClick={loadSaldos}
          className="bg-gray-200 px-3 py-1 rounded hover:bg-gray-300"
        >
          {t('finances:balances.refresh')}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div
          className="bg-blue-50 border border-blue-200 rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => nav('/finance/cash-registers')}
        >
          <div className="text-sm text-gray-600 mb-2">{t('finances:balances.cash')}</div>
          <div className="text-3xl font-bold text-blue-900">
            ${cajaTotal.toFixed(2)}
          </div>
          <div className="text-xs text-blue-600 mt-2">{t('finances:balances.viewTransactions')}</div>
        </div>

        <div
          className="bg-green-50 border border-green-200 rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => nav('/finance/bank-accounts')}
        >
          <div className="text-sm text-gray-600 mb-2">{t('finances:balances.banks')}</div>
          <div className="text-3xl font-bold text-green-900">
            ${bancosTotal.toFixed(2)}
          </div>
          <div className="text-xs text-green-600 mt-2">{t('finances:balances.viewTransactions')}</div>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
          <div className="text-sm text-gray-600 mb-2">{t('finances:balances.totalAvailable')}</div>
          <div className="text-3xl font-bold text-purple-900">
            ${totalDisponible.toFixed(2)}
          </div>
          <div className="text-xs text-gray-500 mt-2">{t('finances:balances.cashPlusBanks')}</div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="text-sm text-gray-600 mb-2">{t('finances:balances.pendingReconciliation')}</div>
          <div className="text-3xl font-bold text-yellow-900">
            ${pendienteConciliar.toFixed(2)}
          </div>
          <div className="text-xs text-yellow-600 mt-2">{t('finances:balances.requiresAttention')}</div>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">{t('finances:balances.balanceDistribution')}</h3>

        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>{t('finances:balances.cash')}</span>
              <span className="font-medium">
                {saldos.total_disponible > 0
                  ? ((saldos.caja_total / saldos.total_disponible) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{
                  width: saldos.total_disponible > 0
                    ? `${(saldos.caja_total / saldos.total_disponible) * 100}%`
                    : '0%'
                }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>{t('finances:balances.banks')}</span>
              <span className="font-medium">
                {saldos.total_disponible > 0
                  ? ((saldos.bancos_total / saldos.total_disponible) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{
                  width: saldos.total_disponible > 0
                    ? `${(saldos.bancos_total / saldos.total_disponible) * 100}%`
                    : '0%'
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-50 border rounded-lg p-4">
          <h4 className="font-medium mb-3">{t('finances:balances.quickActions')}</h4>
          <div className="space-y-2">
            <button
              onClick={() => nav('/finance/cash-registers')}
              className="w-full text-left px-3 py-2 bg-white border rounded hover:bg-gray-50"
            >
              📥 {t('finances:balances.recordCashIncome')}
            </button>
            <button
              onClick={() => nav('/finance/cash-registers')}
              className="w-full text-left px-3 py-2 bg-white border rounded hover:bg-gray-50"
            >
              📤 {t('finances:balances.recordCashExpense')}
            </button>
            <button
              onClick={() => nav('/finance/bank-accounts')}
              className="w-full text-left px-3 py-2 bg-white border rounded hover:bg-gray-50"
            >
              🏦 {t('finances:balances.viewBankTransactions')}
            </button>
          </div>
        </div>

        <div className="bg-gray-50 border rounded-lg p-4">
          <h4 className="font-medium mb-3">{t('finances:balances.alerts')}</h4>
          {saldos.pendiente_conciliar > 0 ? (
            <div className="bg-yellow-100 border border-yellow-300 rounded px-3 py-2 text-sm">
              ⚠️ {t('finances:balances.pendingReconciliationAmount', { amount: saldos.pendiente_conciliar.toFixed(2) })}
            </div>
          ) : (
            <div className="bg-green-100 border border-green-300 rounded px-3 py-2 text-sm">
              ✓ {t('finances:balances.allReconciled')}
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
