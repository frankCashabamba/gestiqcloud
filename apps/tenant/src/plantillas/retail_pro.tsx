import React, { useEffect, useState } from 'react'
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
  const { modules } = useMisModulos()
  const { symbol: currencySymbol } = useCurrency()
  const [openShift, setOpenShift] = useState<POSShift | null>(null)
  const [openSummary, setOpenSummary] = useState<ShiftSummary | null>(null)

  const shouldLoadKPIs = modules.some((m) =>
    ['ventas', 'pos', 'facturacion'].includes((m.slug || '').toLowerCase())
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

  const customLinks = [
    isModuleEnabled('inventario') && { label: 'Stock replenishment', href: '#replenish', icon: 'S' },
    isModuleEnabled('ventas') && { label: 'Promotions', href: '#promotions', icon: 'P' },
    isModuleEnabled('ventas') && { label: 'Sales analysis', href: '#analysis', icon: 'A' },
  ].filter(Boolean) as Array<{ label: string; href: string; icon: string }>

  return (
    <DashboardPro sectorName="Retail ERP" sectorIcon="R" customLinks={customLinks}>
      <h1>Retail dashboard</h1>

      {modules.length === 1 && isModuleEnabled('clientes') && (
        <section
          className="card full-width"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center' }}
        >
          <h2 style={{ margin: 0, fontSize: '24px' }}>Welcome to your ERP</h2>
          <p style={{ marginTop: '12px', opacity: 0.9 }}>
            Start by adding your customers. Other modules will unlock as you progress.
          </p>
          <a href="#customers" className="btn" style={{ marginTop: '20px', display: 'inline-block', background: '#fff', color: 'var(--primary)', fontWeight: 600 }}>
            Go to Customers
          </a>
        </section>
      )}

      <div className="dashboard-grid">
        <section className="card full-width">
          <div className="card__header">
            <h3>Today overview</h3>
            <div className="pills">
              <span className={`pill ${openShift ? 'pill--ok' : ''}`}>
                {openShift ? 'Store open' : 'Store closed'}
              </span>
              <span className="pill">{ventasTickets} tickets</span>
              <span className="pill">Avg ticket: {currencySymbol}{ventasTicketMedio.toFixed(2)}</span>
            </div>
          </div>
          <div className="card__actions">
            {isModuleEnabled('pos') && <a className="link" href="#close">Cash close</a>}
            {isModuleEnabled('inventario') && <a className="link" href="#inventory">Inventory</a>}
            {isModuleEnabled('inventario') && <a className="link" href="#replenish">Replenishment</a>}
            {isModuleEnabled('clientes') && <a className="link" href="#customers">Customers</a>}
          </div>
        </section>

        {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>Sales today</h3>
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

        {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>Weekly comparison</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">This week</span>
                <span className="kpi__value">${comparativa.actual?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Last week</span>
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

        {isModuleEnabled('inventario') && (
          <section className="card col-4">
            <h3>Stock rotation</h3>
            <div className="list-compact">
              <li>High rotation: {stock.productos_alta_rotacion || 0} products</li>
              <li>Low rotation: {stock.productos_baja_rotacion || 0} products</li>
              <li>Replenish now: {stock.reposicion_necesaria || 0}</li>
            </div>
            <div className="card__footer">
              <a className="link" href="#inventory">Open inventory</a>
            </div>
          </section>
        )}

        <section className="card col-8">
          <h3>Quick actions</h3>
          <div className="action-grid">
            {isModuleEnabled('pos') && (
              <a href="#new-sale" className="action-btn">
                <span className="action-btn__icon">+</span>
                <span>New sale</span>
              </a>
            )}
            {isModuleEnabled('ventas') && (
              <a href="#promotion" className="action-btn">
                <span className="action-btn__icon">%</span>
                <span>Create promotion</span>
              </a>
            )}
            {isModuleEnabled('clientes') && (
              <a href="#customers" className="action-btn">
                <span className="action-btn__icon">@</span>
                <span>New customer</span>
              </a>
            )}
            <a href="#price-update" className="action-btn">
              <span className="action-btn__icon">T</span>
              <span>Price update</span>
            </a>
            <a href="#count" className="action-btn">
              <span className="action-btn__icon">#</span>
              <span>Cycle count</span>
            </a>
          </div>
        </section>
      </div>
    </DashboardPro>
  )
}

export default RetailDashboard
