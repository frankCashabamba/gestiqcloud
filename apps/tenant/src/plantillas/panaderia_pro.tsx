import React from 'react'
import { useParams } from 'react-router-dom'
import { usePanaderiaKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import './dashboard_pro.css'

interface KPIData {
  ventas_mostrador?: {
    hoy?: number
    ayer?: number
    variacion?: number
    moneda?: string
  }
  stock_critico?: {
    items?: number
    nombres?: string[]
    urgencia?: string
  }
  mermas?: {
    hoy?: number
    unidad?: string
    valor_estimado?: number
    moneda?: string
  }
  produccion?: {
    hornadas_completadas?: number
    hornadas_programadas?: number
    progreso?: number
  }
  ingredientes_caducar?: {
    proximos_7_dias?: number
    items?: string[]
  }
  top_productos?: Array<{
    name: string
    unidades: number
    ingresos: number
  }>
}

const PanaderiaDashboard: React.FC = () => {
  const { empresa } = useParams<{ empresa?: string }>()
  const { modules } = useMisModulos()

  const shouldLoadKPIs = modules.some((m) =>
    ['ventas', 'pos', 'produccion', 'inventario'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = usePanaderiaKPIs({ enabled: shouldLoadKPIs })

  const kpis = (kpisData || {}) as KPIData
  const ventas = kpis.ventas_mostrador || {}
  const stock = kpis.stock_critico || {}
  const mermas = kpis.mermas || {}
  const produccion = kpis.produccion || {}
  const ingredientes = kpis.ingredientes_caducar || {}
  const topProductos = kpis.top_productos || []

  const isModuleEnabled = (moduleName: string) => {
    return modules.some(
      (m) =>
        (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
        (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  const prefix = empresa ? `/${empresa}` : ''
  const customLinks = [
    isModuleEnabled('produccion') && { label: 'Recipes', href: `${prefix}/produccion/recetas`, icon: 'R' },
    isModuleEnabled('inventario') && { label: 'Inventory', href: `${prefix}/inventory`, icon: 'I' },
    isModuleEnabled('compras') && { label: 'Purchasing', href: `${prefix}/purchases`, icon: 'P' },
  ].filter(Boolean) as Array<{ label: string; href: string; icon: string }>

  return (
    <DashboardPro sectorName="Bakery ERP" sectorIcon="B" customLinks={customLinks}>
      <h1>Bakery overview</h1>

      {modules.length === 1 && isModuleEnabled('clientes') && (
        <section
          className="card full-width"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center' }}
        >
          <h2 style={{ margin: 0, fontSize: '24px' }}>Welcome to your ERP</h2>
          <p style={{ marginTop: '12px', opacity: 0.9 }}>
            Start by adding your customers. Other modules will unlock as you progress.
          </p>
          <a href={`${prefix}/clients`} className="btn" style={{ marginTop: '20px', display: 'inline-block', background: '#fff', color: 'var(--primary)', fontWeight: 600 }}>
            Go to Customers
          </a>
        </section>
      )}

      <div className="dashboard-grid">
        <section className="card full-width">
          <div className="card__header">
            <h3>Today status</h3>
            <div className="pills">
              <span className="pill pill--ok">Operational</span>
              {isModuleEnabled('ventas') && ventas.hoy && ventas.hoy > 0 && (
                <span className="pill">
                  Sales today: {ventas.moneda || '$'}
                  {ventas.hoy.toFixed(2)}
                </span>
              )}
            </div>
          </div>
          <div className="card__actions">
            {isModuleEnabled('pos') && (
              <a className="link" href={`${prefix}/pos`} target="_blank" rel="noopener noreferrer">
                Open POS
              </a>
            )}
            {isModuleEnabled('produccion') && <a className="link" href={`${prefix}/produccion/recetas`}>Recipes</a>}
            {isModuleEnabled('ventas') && <a className="link" href={`${prefix}/sales`}>Sales</a>}
            {isModuleEnabled('clientes') && <a className="link" href={`${prefix}/clients`}>Customers</a>}
          </div>
        </section>

        {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>Sales today</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">Today</span>
                <span className="kpi__value">{kpisLoading ? '...' : `$${ventas.hoy?.toFixed(2) || '0.00'}`}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Yesterday</span>
                <span className="kpi__value">${ventas.ayer?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="kpi">
                <span className={`kpi__value ${(ventas.variacion || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(ventas.variacion || 0) >= 0 ? '+' : ''}
                  {ventas.variacion?.toFixed(1) || '0'}%
                </span>
              </div>
            </div>
            <div className="card__footer">
              <a className="link" href="#sales-detail">View details</a>
            </div>
          </section>
        )}

        {isModuleEnabled('inventario') && (
          <section className="card col-3">
            <h3>Critical stock</h3>
            <div className="stat-large">
              <span className="stat-large__value">{stock.items || 0}</span>
              <span className="stat-large__label">products</span>
            </div>
            {stock.nombres && stock.nombres.length > 0 && (
              <ul className="list-compact">
                {stock.nombres.slice(0, 3).map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            )}
            <div className="card__footer">
              <a className="link" href="#stock">Review inventory</a>
            </div>
          </section>
        )}

        {isModuleEnabled('inventario') && (
          <section className="card col-3">
            <h3>Waste today</h3>
            <div className="stat-large">
              <span className="stat-large__value">{mermas.hoy || 0}</span>
              <span className="stat-large__label">kg</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Estimated value</span>
              <span className="kpi__value">${mermas.valor_estimado?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="card__footer">
              <a className="link" href="#waste">View details</a>
            </div>
          </section>
        )}

        {isModuleEnabled('produccion') && (
          <section className="card col-4">
            <h3>Production batches</h3>
            <div className="progress-stat">
              <div className="progress-stat__header">
                <span>
                  {produccion.hornadas_completadas || 0} / {produccion.hornadas_programadas || 0}
                </span>
                <span>{produccion.progreso?.toFixed(0) || 0}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${produccion.progreso || 0}%` }} />
              </div>
            </div>
            <div className="pills">
              <span className="pill pill--ok">On track</span>
              <span className="pill">2 pending</span>
            </div>
          </section>
        )}

        {isModuleEnabled('inventario') && (
          <section className="card col-4">
            <h3>Ingredients expiring</h3>
            <div className="stat-large">
              <span className="stat-large__value">{ingredientes.proximos_7_dias || 0}</span>
              <span className="stat-large__label">next 7 days</span>
            </div>
            {ingredientes.items && ingredientes.items.length > 0 && (
              <ul className="list-compact">
                {ingredientes.items.map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            )}
          </section>
        )}

        {isModuleEnabled('ventas') && (
          <section className="card col-4">
            <h3>Top products</h3>
            <div className="table-compact">
              {topProductos.length > 0 ? (
                <table>
                  <tbody>
                    {topProductos.map((prod: any, i: number) => (
                      <tr key={i}>
                        <td>{prod.name}</td>
                        <td className="text-right">{prod.unidades} units</td>
                        <td className="text-right">${prod.ingresos?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-state">No data</p>
              )}
            </div>
          </section>
        )}

        {isModuleEnabled('ventas') && (
          <section className="card col-8">
            <h3>Sales by hour</h3>
            <div className="chart-container">
              <div className="chart-placeholder">
                <canvas id="salesChart" height="200"></canvas>
                <p className="chart-empty">Chart in progress</p>
              </div>
            </div>
            <div className="pills">
              <span className="pill">Actual</span>
              <span className="pill">Forecast</span>
              <span className="pill">Target</span>
            </div>
          </section>
        )}

        <section className="card col-4">
          <h3>Quick actions</h3>
          <div className="action-grid">
            {isModuleEnabled('pos') && (
              <a href={`${prefix}/pos`} target="_blank" rel="noopener noreferrer" className="action-btn action-btn--primary">
                <span className="action-btn__icon">P</span>
                <span>Open POS</span>
              </a>
            )}
            {isModuleEnabled('inventario') && (
              <>
                <a href="#waste" className="action-btn">
                  <span className="action-btn__icon">W</span>
                  <span>Record waste</span>
                </a>
                <a href="#stock-adjust" className="action-btn">
                  <span className="action-btn__icon">S</span>
                  <span>Stock adjustment</span>
                </a>
              </>
            )}
            {isModuleEnabled('produccion') && (
              <a href="#new-batch" className="action-btn">
                <span className="action-btn__icon">B</span>
                <span>New batch</span>
              </a>
            )}
            {isModuleEnabled('clientes') && (
              <a href={`${prefix}/clients`} className="action-btn">
                <span className="action-btn__icon">@</span>
                <span>New customer</span>
              </a>
            )}
          </div>
        </section>
      </div>
    </DashboardPro>
  )
}

export default PanaderiaDashboard
