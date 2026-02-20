import React from 'react'
import { useTallerKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import './dashboard_pro.css'

interface KPIData {
  reparaciones_pendientes?: {
    total?: number
    urgentes?: number
    tiempo_medio_espera?: number
  }
  ingresos_mes?: {
    actual?: number
    objetivo?: number
    progreso?: number
  }
  repuestos_bajo_stock?: {
    items?: number
    nombres?: string[]
    urgencia?: string
  }
  trabajos_completados?: {
    hoy?: number
    semana?: number
    mes?: number
  }
}

const TallerDashboard: React.FC = () => {
  const { modules } = useMisModulos()

  const shouldLoadKPIs = modules.some((m) =>
    ['ventas', 'finanzas', 'facturacion'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = useTallerKPIs({ enabled: shouldLoadKPIs })

  const kpis = (kpisData || {}) as KPIData
  const reparaciones = kpis.reparaciones_pendientes || {}
  const ingresos = kpis.ingresos_mes || {}
  const repuestos = kpis.repuestos_bajo_stock || {}
  const trabajos = kpis.trabajos_completados || {}

  const isModuleEnabled = (moduleName: string) => {
    return modules.some(
      (m) =>
        (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
        (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  const customLinks: Array<{ label: string; href: string; icon: string }> = []

  return (
    <DashboardPro sectorName="Workshop ERP" sectorIcon="T" customLinks={customLinks}>
      <h1>Workshop dashboard</h1>

      {modules.length === 1 && isModuleEnabled('clientes') && (
        <section
          className="card full-width"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center' }}
        >
          <h2 style={{ margin: 0, fontSize: '24px' }}>Welcome to your ERP</h2>
          <p style={{ marginTop: '12px', opacity: 0.9 }}>
            Start by adding your customers. Other modules will unlock as you progress.
          </p>
        </section>
      )}

      <div className="dashboard-grid">
        <section className="card full-width">
          <div className="card__header">
            <h3>Operational status</h3>
            <div className="pills">
              <span className="pill pill--ok">Workshop open</span>
              <span className="pill">{reparaciones.total || 0} jobs in progress</span>
              <span className="pill pill--warn">{reparaciones.urgentes || 0} urgent</span>
            </div>
          </div>
        </section>

        {isModuleEnabled('finanzas') && (
          <section className="card col-6">
            <h3>Monthly revenue</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">Current</span>
                <span className="kpi__value">{kpisLoading ? '...' : `$${ingresos.actual?.toFixed(2) || '0.00'}`}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Target</span>
                <span className="kpi__value">${ingresos.objetivo?.toFixed(2) || '0.00'}</span>
              </div>
            </div>
            <div className="progress-stat">
              <div className="progress-stat__header">
                <span>Monthly progress</span>
                <span>{ingresos.progreso?.toFixed(0) || 0}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${ingresos.progreso || 0}%` }} />
              </div>
            </div>
          </section>
        )}

        {isModuleEnabled('inventario') && (
          <section className="card col-3">
            <h3>Critical parts</h3>
            <div className="stat-large">
              <span className="stat-large__value">{repuestos.items || 0}</span>
              <span className="stat-large__label">parts</span>
            </div>
            {repuestos.nombres && repuestos.nombres.length > 0 && (
              <ul className="list-compact">
                {repuestos.nombres.slice(0, 3).map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            )}
          </section>
        )}

        {isModuleEnabled('ventas') && (
          <section className="card col-3">
            <h3>Jobs completed</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">Today</span>
                <span className="kpi__value">{trabajos.hoy || 0}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">This month</span>
                <span className="kpi__value">{trabajos.mes || 0}</span>
              </div>
            </div>
          </section>
        )}

        {isModuleEnabled('ventas') && (
          <section className="card col-4">
            <h3>Pending repairs</h3>
            <div className="stat-large">
              <span className="stat-large__value">{reparaciones.total || 0}</span>
              <span className="stat-large__label">orders</span>
            </div>
            <div className="pills">
              <span className="pill pill--err">{reparaciones.urgentes || 0} urgent</span>
              <span className="pill">{reparaciones.tiempo_medio_espera?.toFixed(1) || '0'} days wait</span>
            </div>
          </section>
        )}

      </div>
    </DashboardPro>
  )
}

export default TallerDashboard
