/**
 * RetailDashboard - Professional v2 with i18n Support
 *
 * Features:
 * - Functional handlers for all actions (no dead buttons)
 * - React Router navigation (not hash-based)
 * - Module validation with tooltips
 * - Audit logging
 * - Full i18n support (EN/ES)
 * - Type-safe with dedicated types
 *
 * @version 2.0
 * @language TypeScript + React
 */

import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useDashboardKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import { getCurrentShift, getShiftSummary, listRegisters } from '../modules/pos/services'
import { useCurrency } from '../hooks/useCurrency'
import { useI18n } from '../i18n/I18nProvider'
import type { POSShift, ShiftSummary } from '../types/pos'
import DashboardPro from './components/DashboardPro'
import QuickActionsSection from './components/QuickActionsSection'
import {
  buildRoute,
  RETAIL_QUICK_ACTIONS,
  RETAIL_CUSTOM_LINKS,
  logDashboardAction,
} from './services/navigationService'
import type { QuickAction, KPIData, CustomLink } from './types/dashboard'
import './dashboard_pro.css'

// Helper para acceder a traducciones retail dashboard
const useRetailI18n = () => {
  const { t } = useI18n()
  return {
    t: (key: string, vars?: Record<string, string | number>) => 
      t(`retailDashboard:${key}`, vars),
  }
}

/**
 * Main Retail Dashboard Component
 *
 * Responsible for:
 * - Loading KPI data
 * - Managing shift state
 * - Rendering dashboard sections with i18n
 * - Handling navigation actions
 */
const RetailDashboard: React.FC = () => {
  const navigate = useNavigate()
  const { empresa } = useParams()
  const { t } = useRetailI18n()
  const { modules } = useMisModulos()
  const { symbol: currencySymbol } = useCurrency()
  const [openShift, setOpenShift] = useState<POSShift | null>(null)
  const [openSummary, setOpenSummary] = useState<ShiftSummary | null>(null)

  // ─────────────────────────────────────────────────────────
  // Module Availability Check
  // ─────────────────────────────────────────────────────────
  const isModuleEnabled = (moduleName: string): boolean => {
    return modules.some(
      (m) =>
        (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
        (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  // ─────────────────────────────────────────────────────────
  // Load KPI Data
  // ─────────────────────────────────────────────────────────
  const shouldLoadKPIs = modules.some((m) =>
    ['ventas', 'pos', 'facturacion'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = useDashboardKPIs({
    periodo: 'today',
    enabled: shouldLoadKPIs,
  })

  const kpis = (kpisData || {}) as KPIData
  const ventas = kpis.ventas_dia || {}
  const stock = kpis.stock_rotacion || {}
  const comparativa = kpis.comparativa_semana || {}

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
    return () => {
      cancelled = true
    }
  }, [modules])

  // ─────────────────────────────────────────────────────────
  // Computed Values for KPIs
  // ─────────────────────────────────────────────────────────
  const liveSalesTotal = openSummary?.sales_total ?? null
  const liveTickets = openSummary?.receipts_count ?? null
  const liveAvgTicket =
    liveSalesTotal !== null && liveTickets && liveTickets > 0
      ? liveSalesTotal / liveTickets
      : null
  const ventasTotal = liveSalesTotal ?? ventas.total ?? 0
  const ventasTickets = liveTickets ?? ventas.tickets ?? 0
  const ventasTicketMedio = liveAvgTicket ?? ventas.ticket_medio ?? 0

  // ─────────────────────────────────────────────────────────
  // Navigation Handlers
  // ─────────────────────────────────────────────────────────
  const handleNewSale = () => {
    if (!isModuleEnabled('pos')) return
    logDashboardAction({ action: 'quick_action.new_sale' })
    navigate(buildRoute({ route: 'pos.new', empresa }))
  }

  const handleCreatePromotion = () => {
    if (!isModuleEnabled('ventas')) return
    logDashboardAction({ action: 'quick_action.create_promotion' })
    navigate(buildRoute({ route: 'ventas.promotions', empresa }))
  }

  const handleNewCustomer = () => {
    if (!isModuleEnabled('clientes')) return
    logDashboardAction({ action: 'quick_action.new_customer' })
    navigate(buildRoute({ route: 'clientes.new', empresa }))
  }

  const handleCashClose = () => {
    if (!isModuleEnabled('pos')) return
    logDashboardAction({ action: 'action.cash_close' })
    navigate(buildRoute({ route: 'pos.cash-close', empresa }))
  }

  const handleInventory = () => {
    if (!isModuleEnabled('inventario')) return
    logDashboardAction({ action: 'action.inventory' })
    navigate(buildRoute({ route: 'inventario.list', empresa }))
  }

  const handleReplenishment = () => {
    if (!isModuleEnabled('inventario')) return
    logDashboardAction({ action: 'action.replenishment' })
    navigate(buildRoute({ route: 'inventario.replenishment', empresa }))
  }

  const handleGoToCustomers = () => {
    if (!isModuleEnabled('clientes')) return
    logDashboardAction({ action: 'action.go_to_customers' })
    navigate(buildRoute({ route: 'clientes.list', empresa }))
  }

  // ─────────────────────────────────────────────────────────
  // Quick Actions Configuration (Dynamic)
  // ─────────────────────────────────────────────────────────
  const quickActions: QuickAction[] = [
    {
      id: 'new-sale',
      label: t('quickActions.newSale'),
      icon: '+',
      disabled: !isModuleEnabled('pos'),
      action: handleNewSale,
      requiresModule: 'pos',
    },
    {
      id: 'create-promotion',
      label: t('quickActions.createPromotion'),
      icon: '%',
      disabled: !isModuleEnabled('ventas'),
      action: handleCreatePromotion,
      requiresModule: 'ventas',
    },
    {
      id: 'new-customer',
      label: t('quickActions.newCustomer'),
      icon: '@',
      disabled: !isModuleEnabled('clientes'),
      action: handleNewCustomer,
      requiresModule: 'clientes',
    },
  ]

  // ─────────────────────────────────────────────────────────
  // Custom Links (Sidebar) Configuration
  // ─────────────────────────────────────────────────────────
  const customLinks: CustomLink[] = [
    isModuleEnabled('inventario') && {
      label: t('customLinks.stockReplenishment'),
      href: buildRoute({ route: 'inventario.replenishment', empresa }),
      icon: 'S',
    },
    isModuleEnabled('ventas') && {
      label: t('customLinks.promotions'),
      href: buildRoute({ route: 'ventas.promotions', empresa }),
      icon: 'P',
    },
    isModuleEnabled('reportes') && {
      label: t('customLinks.salesAnalysis'),
      href: buildRoute({ route: 'reportes.analysis', empresa }),
      icon: 'A',
    },
  ].filter(Boolean) as CustomLink[]

  // ─────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────
  return (
    <DashboardPro
      sectorName={t('sectorName')}
      sectorIcon="R"
      customLinks={customLinks}
    >
      <h1>{t('title')}</h1>

      {/* Welcome Card (Only when single module 'clientes' enabled) */}
      {modules.length === 1 && isModuleEnabled('clientes') && (
        <section
          className="card full-width"
          style={{
            background: 'linear-gradient(135deg, var(--primary), var(--focus))',
            color: '#fff',
            padding: '40px',
            textAlign: 'center',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '24px' }}>
            {t('welcome.title')}
          </h2>
          <p style={{ marginTop: '12px', opacity: 0.9 }}>
            {t('welcome.description')}
          </p>
          <button
            onClick={handleGoToCustomers}
            style={{
              marginTop: '20px',
              display: 'inline-block',
              background: '#fff',
              color: 'var(--primary)',
              fontWeight: 600,
              border: 'none',
              padding: '10px 20px',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            {t('welcome.button')}
          </button>
        </section>
      )}

      <div className="dashboard-grid">
        {/* Today Overview Card */}
        <section className="card full-width">
          <div className="card__header">
            <h3>{t('todayOverview.title')}</h3>
            <div className="pills">
              <span className={`pill ${openShift ? 'pill--ok' : ''}`}>
                {openShift ? t('todayOverview.storeOpen') : t('todayOverview.storeClosed')}
              </span>
              <span className="pill">
                {t('todayOverview.tickets', { count: ventasTickets })}
              </span>
              <span className="pill">
                {t('todayOverview.avgTicket', {
                  symbol: currencySymbol,
                  value: ventasTicketMedio.toFixed(2),
                })}
              </span>
            </div>
          </div>
          <div className="card__actions">
            <button
              onClick={handleCashClose}
              disabled={!isModuleEnabled('pos')}
              className="link"
              title={
                !isModuleEnabled('pos')
                  ? t('moduleRequired', { module: 'POS' })
                  : ''
              }
            >
              {t('cardActions.cashClose')}
            </button>
            <button
              onClick={handleInventory}
              disabled={!isModuleEnabled('inventario')}
              className="link"
              title={
                !isModuleEnabled('inventario')
                  ? t('moduleRequired', { module: 'Inventory' })
                  : ''
              }
            >
              {t('cardActions.inventory')}
            </button>
            <button
              onClick={handleReplenishment}
              disabled={!isModuleEnabled('inventario')}
              className="link"
              title={
                !isModuleEnabled('inventario')
                  ? t('moduleRequired', { module: 'Inventory' })
                  : ''
              }
            >
              {t('cardActions.replenishment')}
            </button>
            <button
              onClick={() => navigate(buildRoute({ route: 'clientes.list', empresa }))}
              disabled={!isModuleEnabled('clientes')}
              className="link"
              title={
                !isModuleEnabled('clientes')
                  ? t('moduleRequired', { module: 'Customers' })
                  : ''
              }
            >
              {t('cardActions.customers')}
            </button>
          </div>
        </section>

        {/* Sales Today Card */}
        {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>{t('cardHeaders.salesToday')}</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">{t('kpiLabels.total')}</span>
                <span className="kpi__value">
                  {kpisLoading && liveSalesTotal === null
                    ? '...'
                    : `${currencySymbol}${ventasTotal.toFixed(2)}`}
                </span>
              </div>
              <div className="kpi">
                <span className="kpi__label">{t('kpiLabels.tickets')}</span>
                <span className="kpi__value">{ventasTickets}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">{t('kpiLabels.avgTicket')}</span>
                <span className="kpi__value">
                  {currencySymbol}
                  {ventasTicketMedio.toFixed(2)}
                </span>
              </div>
            </div>
          </section>
        )}

        {/* Weekly Comparison Card */}
        {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>{t('cardHeaders.weeklyComparison')}</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">{t('kpiLabels.thisWeek')}</span>
                <span className="kpi__value">
                  ${comparativa.actual?.toFixed(2) || '0.00'}
                </span>
              </div>
              <div className="kpi">
                <span className="kpi__label">{t('kpiLabels.lastWeek')}</span>
                <span className="kpi__value">
                  ${comparativa.anterior?.toFixed(2) || '0.00'}
                </span>
              </div>
              <div
                className={`kpi__value ${
                  (comparativa.variacion || 0) >= 0 ? 'positive' : 'negative'
                }`}
              >
                {(comparativa.variacion || 0) >= 0 ? '+' : ''}
                {comparativa.variacion?.toFixed(1) || '0'}%
              </div>
            </div>
          </section>
        )}

        {/* Stock Rotation Card */}
        {isModuleEnabled('inventario') && (
          <section className="card col-4">
            <h3>{t('cardHeaders.stockRotation')}</h3>
            <div className="list-compact">
              <li>
                {t('stockLabels.highRotation')}: {stock.productos_alta_rotacion || 0}{' '}
                {t('stockLabels.products')}
              </li>
              <li>
                {t('stockLabels.lowRotation')}: {stock.productos_baja_rotacion || 0}{' '}
                {t('stockLabels.products')}
              </li>
              <li>
                {t('stockLabels.replenishNow')}: {stock.reposicion_necesaria || 0}
              </li>
            </div>
            <div className="card__footer">
              <button onClick={handleInventory} className="link">
                {t('stockLabels.openInventory')}
              </button>
            </div>
          </section>
        )}

        {/* Quick Actions Card */}
        <QuickActionsSection
          actions={quickActions}
          title={t('quickActions.title')}
          onAction={(actionId) => {
            logDashboardAction({ action: `action_completed.${actionId}` })
          }}
        />
      </div>
    </DashboardPro>
  )
}

export default RetailDashboard
