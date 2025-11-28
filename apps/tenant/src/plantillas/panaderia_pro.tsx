import React from 'react'
import { useParams } from 'react-router-dom'
import { usePanaderiaKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import './panaderia_pro.css'

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

  // Solo cargar KPIs si hay módulos de ventas/producción activos
  const shouldLoadKPIs = modules.some(m =>
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

  // Helper: verificar si un módulo está activo
  const isModuleEnabled = (moduleName: string) => {
    return modules.some(m =>
      (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
      (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  // Enlaces personalizados solo para módulos activos
  const prefix = empresa ? `/${empresa}` : ''
  const customLinks = [
    isModuleEnabled('produccion') && { label: 'Recetas', href: `${prefix}/produccion/recetas`, icon: '🍞' },
    isModuleEnabled('inventario') && { label: 'Inventory', href: `${prefix}/inventario`, icon: '📦' },
    isModuleEnabled('compras') && { label: 'Compras', href: `${prefix}/compras`, icon: '🛍️' }
  ].filter(Boolean) as Array<{ label: string; href: string; icon: string }>

  return (
    <DashboardPro
      sectorName="PanERP"
      sectorIcon="🥖"
      customLinks={customLinks}
    >
      <h1>🥖 Hoy en tu panadería</h1>

        {/* Mensaje de bienvenida si solo tiene clientes */}
        {modules.length === 1 && isModuleEnabled('clientes') && (
          <section className="card full-width" style={{background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center'}}>
            <h2 style={{margin: 0, fontSize: '24px'}}>👋 ¡Bienvenido a tu ERP!</h2>
            <p style={{marginTop: '12px', opacity: 0.9}}>Comienza agregando tus clientes. Los demás módulos se activarán progresivamente.</p>
            <a href={`${prefix}/clientes`} className="btn" style={{marginTop: '20px', display: 'inline-block', background: '#fff', color: 'var(--primary)', fontWeight: 600}}>
              👥 Ir a Clientes
            </a>
          </section>
        )}

        <div className="dashboard-grid">
          {/* Estado del día */}
          <section className="card full-width">
            <div className="card__header">
              <h3>Estado del día</h3>
              <div className="pills">
              <span className="pill pill--ok">Sistema operativo</span>
              {isModuleEnabled('ventas') && ventas.hoy && ventas.hoy > 0 && (
                <span className="pill">Ventas hoy: {ventas.moneda || '$'}{ventas.hoy.toFixed(2)}</span>
              )}
              </div>
            </div>
            <div className="card__actions">
              {isModuleEnabled('pos') && <a className="link" href={`${prefix}/pos`} target="_blank" rel="noopener noreferrer">Ir al POS ↗</a>}
              {isModuleEnabled('produccion') && <a className="link" href={`${prefix}/produccion/recetas`}>Ver Recetas</a>}
              {isModuleEnabled('ventas') && <a className="link" href={`${prefix}/ventas`}>Ver Ventas</a>}
              {isModuleEnabled('clientes') && <a className="link" href={`${prefix}/clientes`}>Ver Clientes</a>}
            </div>
          </section>

          {/* Ventas del día - solo si módulo ventas activo */}
          {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>💰 Ventas del día</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">Hoy</span>
                <span className="kpi__value">
                  {kpisLoading ? '...' : `€${ventas.hoy?.toFixed(2) || '0.00'}`}
                </span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Ayer</span>
                <span className="kpi__value">€{ventas.ayer?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Variación</span>
                <span className={`kpi__value ${(ventas.variacion || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(ventas.variacion || 0) >= 0 ? '+' : ''}{ventas.variacion?.toFixed(1) || '0'}%
                </span>
              </div>
            </div>
            <div className="card__footer">
              <a className="link" href="#detalle-ventas">Ver detalle →</a>
            </div>
          </section>
          )}

          {/* Stock crítico - solo si inventario activo */}
          {isModuleEnabled('inventario') && (
          <section className="card col-3">
            <h3>⚠️ Stock crítico</h3>
            <div className="stat-large">
              <span className="stat-large__value">{stock.items || 0}</span>
              <span className="stat-large__label">productos</span>
            </div>
            {stock.nombres && stock.nombres.length > 0 && (
              <ul className="list-compact">
                {stock.nombres.slice(0, 3).map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            )}
            <div className="card__footer">
              <a className="link" href="#stock">Revisar inventario →</a>
            </div>
          </section>
          )}

          {/* Mermas - solo si inventario activo */}
          {isModuleEnabled('inventario') && (
          <section className="card col-3">
            <h3>📉 Mermas del día</h3>
            <div className="stat-large">
              <span className="stat-large__value">{mermas.hoy || 0}</span>
              <span className="stat-large__label">kg</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Valor estimado</span>
              <span className="kpi__value">€{mermas.valor_estimado?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="card__footer">
              <a className="link" href="#mermas">Ver detalles →</a>
            </div>
          </section>
          )}

          {/* Producción - solo si produccion activo */}
          {isModuleEnabled('produccion') && (
          <section className="card col-4">
            <h3>🔥 Producción de hornadas</h3>
            <div className="progress-stat">
              <div className="progress-stat__header">
                <span>{produccion.hornadas_completadas || 0} / {produccion.hornadas_programadas || 0}</span>
                <span>{produccion.progreso?.toFixed(0) || 0}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-bar__fill"
                  style={{ width: `${produccion.progreso || 0}%` }}
                />
              </div>
            </div>
            <div className="pills">
              <span className="pill pill--ok">En horario</span>
              <span className="pill">2 pendientes</span>
            </div>
          </section>
          )}

          {/* Ingredientes a caducar - solo si inventario activo */}
          {isModuleEnabled('inventario') && (
          <section className="card col-4">
            <h3>📅 Ingredientes a caducar</h3>
            <div className="stat-large">
              <span className="stat-large__value">{ingredientes.proximos_7_dias || 0}</span>
              <span className="stat-large__label">próximos 7 días</span>
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

          {/* Top productos - solo si ventas activo */}
          {isModuleEnabled('ventas') && (
          <section className="card col-4">
            <h3>🏆 Top productos</h3>
            <div className="table-compact">
              {topProductos.length > 0 ? (
                <table>
                  <tbody>
                    {topProductos.map((prod: any, i: number) => (
                      <tr key={i}>
                        <td>{prod.name}</td>
                        <td className="text-right">{prod.unidades} un.</td>
                        <td className="text-right">€{prod.ingresos?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-state">No hay datos</p>
              )}
            </div>
          </section>
          )}

          {/* Ventas por hora - solo si ventas activo */}
          {isModuleEnabled('ventas') && (
          <section className="card col-8">
            <h3>📊 Ventas por hora</h3>
            <div className="chart-container">
              <div className="chart-placeholder">
                <canvas id="ventasChart" height="200"></canvas>
                <p className="chart-empty">Gráfico en desarrollo</p>
              </div>
            </div>
            <div className="pills">
              <span className="pill">Real</span>
              <span className="pill">Previsión</span>
              <span className="pill">Objetivo</span>
            </div>
          </section>
          )}

          {/* Acciones rápidas - dinámicas según módulos */}
          <section className="card col-4">
            <h3>⚡ Acciones rápidas</h3>
            <div className="action-grid">
              {isModuleEnabled('pos') && (
                <a href={`${prefix}/pos`} target="_blank" rel="noopener noreferrer" className="action-btn action-btn--primary">
                  <span className="action-btn__icon">🏪</span>
                  <span>Abrir TPV</span>
                </a>
              )}
              {isModuleEnabled('inventario') && (
                <>
                  <a href="#registro-merma" className="action-btn">
                    <span className="action-btn__icon">📝</span>
                    <span>Registrar merma</span>
                  </a>
                  <a href="#ajuste-stock" className="action-btn">
                    <span className="action-btn__icon">📦</span>
                    <span>Ajuste stock</span>
                  </a>
                </>
              )}
              {isModuleEnabled('produccion') && (
                <a href="#nueva-hornada" className="action-btn">
                  <span className="action-btn__icon">🔥</span>
                  <span>Nueva hornada</span>
                </a>
              )}
              {isModuleEnabled('clientes') && (
                <a href={`${prefix}/clientes`} className="action-btn">
                  <span className="action-btn__icon">👥</span>
                  <span>Nuevo cliente</span>
                </a>
              )}
            </div>
          </section>

        </div>
    </DashboardPro>
  )
}

export default PanaderiaDashboard
