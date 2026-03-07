import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useMovimientos } from '../hooks/useMovimientos'

export const PerdidasGanancias: React.FC = () => {
  const { t } = useTranslation()
  const { asientos, loading } = useMovimientos()

  const { ventas, cogs, opex, resultado } = useMemo(() => {
    let ventas = 0
    let cogs = 0
    let opex = 0
    for (const a of asientos) {
      for (const ap of a.apuntes) {
        // Ingresos: 4.x (Ecuador/genérico) o 7.x (España PGC) — créditos
        if (ap.cuenta.startsWith('4') || ap.cuenta.startsWith('7')) ventas += ap.haber ?? 0
        // Costo de ventas: 5.1.x o 6.1.x
        if (ap.cuenta.startsWith('5.1') || ap.cuenta.startsWith('6.1')) cogs += ap.debe ?? 0
        // Gastos operativos: 5.2.x, 5.3.x... o 6.2.x...
        if (ap.cuenta.startsWith('5.2') || ap.cuenta.startsWith('5.3') ||
            ap.cuenta.startsWith('6.2') || ap.cuenta.startsWith('6.3')) opex += ap.debe ?? 0
      }
    }
    return { ventas, cogs, opex, resultado: ventas - cogs - opex }
  }, [asientos])

  const utilidadBruta = ventas - cogs
  const margenNeto = ventas > 0 ? (resultado / ventas) * 100 : 0

  if (loading) return <div style={{ padding: 16 }}>{t('accounting.pl.loading')}</div>

  return (
    <div style={{ padding: 16, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff', margin: 16 }}>
      <h2 style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>{t('accounting.pl.title')}</h2>
      <div style={{ display: 'grid', gap: 6, color: '#111827' }}>
        <div>{t('accounting.pl.totalSales')}: $ {ventas.toFixed(2)}</div>
        <div>{t('accounting.pl.cogs')}: $ {cogs.toFixed(2)}</div>
        <div>{t('accounting.pl.grossProfit')}: $ {utilidadBruta.toFixed(2)}</div>
        <div>{t('accounting.pl.expenses')}: $ {opex.toFixed(2)}</div>
        <div style={{ fontWeight: 600 }}>{t('accounting.pl.netResult')}: $ {resultado.toFixed(2)}</div>
        <div style={{ fontSize: 12, color: '#666' }}>
          {t('accounting.pl.netMargin')}: {margenNeto.toFixed(2)}%
        </div>
      </div>
    </div>
  )
}
