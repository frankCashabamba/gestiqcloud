import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDashboardKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import { getCurrentShift, getShiftSummary, listRegisters } from '../modules/pos/services'
import { useCurrency } from '../hooks/useCurrency'
import type { POSShift, ShiftSummary } from '../types/pos'
import DashboardPro from './components/DashboardPro'
import './dashboard_pro.css'

interface KPIData {
  ventas_dia?: {
    total?: number
    tickets?: number
    ticket_medio?: number
  }
  stock_rotacion?: {
    productos_alta_rotacion?: number
    productos_baja_rotacion?: number
    reposicion_necesaria?: number
  }
  comparativa_semana?: {
    actual?: number
    anterior?: number
    variacion?: number
  }
}

const RetailDashboard: React.FC = () => {
  const { t } = useTranslation(['dashboard', 'common'])
  const { modules } = useMisModulos()
  const { symbol: currencySymbol } = useCurrency()
  const [openShift, setOpenShift] = useState<POSShift | null>(null)
  const [openSummary, setOpenSummary] = useState<ShiftSummary | null>(null)

  const shouldLoadKPIs = modules.some((m) =>
    ['sales', 'pos', 'facturacion'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = useDashboardKPIs({ periodo: 'today', enabled: shouldLoadKPIs })

  const kpis = (kpisData || {}) as KPIData
  const ventas = kpis.ventas_dia || {}
  const stock = kpis.stock_rotacion || {}
  const comparativa = kpis.comparativa_semana || {}

  const isModuleEnabled = (moduleName: string) => {
    return modules.some(
      (m) =>
        (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
        (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  useEffect(() => {
    let cancelled = false
    const loadShiftSummary = async () => {
      if (!isModuleEnabled('pos')) return
      try {
        const regs = await listRegisters()
        const activeRegister = regs.find((r: any) => r.active) || regs[0]
        if (!activeRegister?.id) return
        const shift = await getCurrentShift(String(activeRegister.id))
        if (cancelled) return
        setOpenShift(shift)
        if (shift) {
          const summary = await getShiftSummary(shift.id)
          if (!cancelled) setOpenSummary(summary)
        } else {
          setOpenSummary(null)
        }
      } catch {
        if (!cancelled) {
          setOpenShift(null)
          setOpenSummary(null)
        }
      }
    }

    loadShiftSummary()
    return () => { cancelled = true }
  }, [modules])

  const liveSalesTotal = openSummary?.sales_total ?? null
  const liveTickets = openSummary?.receipts_count ?? null
  const liveAvgTicket =
    liveSalesTotal !== null && liveTickets && liveTickets > 0 ? liveSalesTotal / liveTickets : null
  const ventasTotal = liveSalesTotal ?? ventas.total ?? 0
  const ventasTickets = liveTickets ?? ventas.tickets ?? 0
  const ventasTicketMedio = liveAvgTicket ?? ventas.ticket_medio ?? 0

  const customLinks: Array<{ label: string; href: string; icon: string }> = []

  return (
    <DashboardPro sectorName={t('dashboard:retail.sectorName')} sectorIcon="R" customLinks={customLinks}>
      <h1>{t('dashboard:retail.title')}</h1>

      {modules.length === 1 && isModuleEnabled('customers') && (
        <section
          className="card full-width"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center' }}
        >
          <h2 style={{ margin: 0, fontSize: '24px' }}>{t('dashboard:retail.welcomeTitle')}</h2>
          <p style={{ marginTop: '12px', opacity: 0.9 }}>
            {t('dashboard:retail.welcomeDesc')}
          </p>
        </section>
      )}

      <div className="dashboard-grid">
        <section className="card full-width">
          <div className="card__header">
            <h3>{t('dashboard:retail.dayStatus')}</h3>
            <div className="pills">
              <span className={`pill ${openShift ? 'pill--ok' : ''}`}>
                {openShift ? t('dashboard:retail.storeOpen') : t('dashboard:retail.storeClosed')}
              </span>
              <span className="pill">{ventasTickets} tickets</span>
              <span className="pill">Avg ticket: {currencySymbol}{ventasTicketMedio.toFixed(2)}</span>
            </div>
          </div>
        </section>

        {isModuleEnabled('sales') && (
          <section className="card col-6">
            <h3>{t('dashboard:retail.salesToday')}</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">Total</span>
                <span className="kpi__value">
                  {kpisLoading && liveSalesTotal === null ? '...' : `${currencySymbol}${ventasTotal.toFixed(2)}`}
                </span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Tickets</span>
                <span className="kpi__value">{ventasTickets}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Avg ticket</span>
                <span className="kpi__value">{currencySymbol}{ventasTicketMedio.toFixed(2)}</span>
              </div>
            </div>
          </section>
        )}

        {isModuleEnabled('sales') && (
          <section className="card col-6">
            <h3>{t('dashboard:retail.weeklyComparison')}</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">{t('dashboard:retail.thisWeek')}</span>
                <span className="kpi__value">${comparativa.actual?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">{t('dashboard:retail.lastWeek')}</span>
                <span className="kpi__value">${comparativa.anterior?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="kpi">
                <span className={`kpi__value ${(comparativa.variacion || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(comparativa.variacion || 0) >= 0 ? '+' : ''}
                  {comparativa.variacion?.toFixed(1) || '0'}%
                </span>
              </div>
            </div>
          </section>
        )}

        {isModuleEnabled('inventory') && (
          <section className="card col-4">
            <h3>{t('dashboard:retail.stockRotation')}</h3>
            <div className="list-compact">
              <li>{t('dashboard:retail.highRotation')}: {stock.productos_alta_rotacion || 0} products</li>
              <li>{t('dashboard:retail.lowRotation')}: {stock.productos_baja_rotacion || 0} products</li>
              <li>{t('dashboard:retail.replenishNow')}: {stock.reposicion_necesaria || 0}</li>
            </div>
          </section>
        )}
      </div>
    </DashboardPro>
  )
}

export default RetailDashboard
