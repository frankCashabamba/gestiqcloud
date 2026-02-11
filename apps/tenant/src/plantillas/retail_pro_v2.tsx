import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
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

interface QuickAction {
  id: string
  label: string
  icon: string
  disabled: boolean
  action: () => void
  requiresModule: string | null
}

interface CustomLink {
  label: string
  href: string
  icon: string
}

const RetailDashboard: React.FC = () => {
  const navigate = useNavigate()
  const { empresa } = useParams()
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

  // ─────────────────────────────────────────────────────────
  // Load Shift Summary
  // ─────────────────────────────────────────────────────────
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

  // ─────────────────────────────────────────────────────────
  // Computed Values
  // ─────────────────────────────────────────────────────────
  const liveSalesTotal = openSummary?.sales_total ?? null
  const liveTickets = openSummary?.receipts_count ?? null
  const liveAvgTicket =
    liveSalesTotal !== null && liveTickets && liveTickets > 0 ? liveSalesTotal / liveTickets : null
  const ventasTotal = liveSalesTotal ?? ventas.total ?? 0
  const ventasTickets = liveTickets ?? ventas.tickets ?? 0
  const ventasTicketMedio = liveAvgTicket ?? ventas.ticket_medio ?? 0

  // ─────────────────────────────────────────────────────────
  // Navigation Handlers
  // ─────────────────────────────────────────────────────────
  const handleNewSale = () => {
    if (!isModuleEnabled('pos')) return
    navigate(`/${empresa}/pos/new`)
  }

  const handleCreatePromotion = () => {
    if (!isModuleEnabled('ventas')) return
    navigate(`/${empresa}/ventas/promotions`)
  }

  const handleNewCustomer = () => {
    if (!isModuleEnabled('clientes')) return
    navigate(`/${empresa}/clientes/new`)
  }

  const handleCashClose = () => {
    if (!isModuleEnabled('pos')) return
    // Opción A: Ruta directa
    navigate(`/${empresa}/pos/cash-close`)
    // Opción B: Abrir modal desde aquí (si prefieres)
    // setShowCashCloseModal(true)
  }

  const handleInventory = () => {
    if (!isModuleEnabled('inventario')) return
    navigate(`/${empresa}/inventario`)
  }

  const handleReplenishment = () => {
    if (!isModuleEnabled('inventario')) return
    navigate(`/${empresa}/inventario/replenishment`)
  }

  // ─────────────────────────────────────────────────────────
  // Quick Actions Array (eliminamos botones muertos)
  // ─────────────────────────────────────────────────────────
  const quickActions: QuickAction[] = [
    {
      id: 'new-sale',
      label: 'New sale',
      icon: '+',
      disabled: !isModuleEnabled('pos'),
      action: handleNewSale,
      requiresModule: 'pos',
    },
    {
      id: 'create-promotion',
      label: 'Create promotion',
      icon: '%',
      disabled: !isModuleEnabled('ventas'),
      action: handleCreatePromotion,
      requiresModule: 'ventas',
    },
    {
      id: 'new-customer',
      label: 'New customer',
      icon: '@',
      disabled: !isModuleEnabled('clientes'),
      action: handleNewCustomer,
      requiresModule: 'clientes',
    },
  ]
  // Nota: Eliminados "Price update" (#price-update) y "Cycle count" (#count)
  // Razón: No había handlers y no estaban conectados a módulos específicos.
  // Si necesitas agregar estas funciones, crear módulo específico.

  // ─────────────────────────────────────────────────────────
  // Custom Links (Sidebar)
  // ─────────────────────────────────────────────────────────
  const customLinks: CustomLink[] = [
    isModuleEnabled('inventario') && { label: 'Stock replenishment', href: `/${empresa}/inventario/replenishment`, icon: 'S' },
    isModuleEnabled('ventas') && { label: 'Promotions', href: `/${empresa}/ventas/promotions`, icon: 'P' },
    isModuleEnabled('reportes') && { label: 'Sales analysis', href: `/${empresa}/reportes/analysis`, icon: 'A' },
  ].filter(Boolean) as CustomLink[]

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
          <button
            onClick={() => navigate(`/${empresa}/clientes`)}
            style={{ marginTop: '20px', display: 'inline-block', background: '#fff', color: 'var(--primary)', fontWeight: 600, border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer' }}
          >
            Go to Customers
          </button>
        </section>
      )}

      <div className="dashboard-grid">
        {/* Today Overview Card */}
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
            <button
              onClick={handleCashClose}
              disabled={!isModuleEnabled('pos')}
              className="link"
              title={!isModuleEnabled('pos') ? 'POS module required' : ''}
            >
              Cash close
            </button>
            <button
              onClick={handleInventory}
              disabled={!isModuleEnabled('inventario')}
              className="link"
              title={!isModuleEnabled('inventario') ? 'Inventory module required' : ''}
            >
              Inventory
            </button>
            <button
              onClick={handleReplenishment}
              disabled={!isModuleEnabled('inventario')}
              className="link"
              title={!isModuleEnabled('inventario') ? 'Inventory module required' : ''}
            >
              Replenishment
            </button>
            <button
              onClick={() => navigate(`/${empresa}/clientes`)}
              disabled={!isModuleEnabled('clientes')}
              className="link"
              title={!isModuleEnabled('clientes') ? 'Customers module required' : ''}
            >
              Customers
            </button>
          </div>
        </section>

        {/* Sales Today Card */}
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

        {/* Weekly Comparison Card */}
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

        {/* Stock Rotation Card */}
        {isModuleEnabled('inventario') && (
          <section className="card col-4">
            <h3>Stock rotation</h3>
            <div className="list-compact">
              <li>High rotation: {stock.productos_alta_rotacion || 0} products</li>
              <li>Low rotation: {stock.productos_baja_rotacion || 0} products</li>
              <li>Replenish now: {stock.reposicion_necesaria || 0}</li>
            </div>
            <div className="card__footer">
              <button
                onClick={handleInventory}
                className="link"
              >
                Open inventory
              </button>
            </div>
          </section>
        )}

        {/* Quick Actions Card (MEJORADO: sin botones muertos) */}
        <section className="card col-8">
          <h3>Quick actions</h3>
          <div className="action-grid">
            {quickActions.map((action) => (
              <button
                key={action.id}
                onClick={action.action}
                disabled={action.disabled}
                className="action-btn"
                title={action.disabled ? `${action.requiresModule} module required` : ''}
                style={{
                  opacity: action.disabled ? 0.5 : 1,
                  cursor: action.disabled ? 'not-allowed' : 'pointer',
                }}
              >
                <span className="action-btn__icon">{action.icon}</span>
                <span>{action.label}</span>
              </button>
            ))}
          </div>
        </section>
      </div>
    </DashboardPro>
  )
}

export default RetailDashboard
