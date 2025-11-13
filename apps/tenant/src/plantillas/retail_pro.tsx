import React from 'react'
import { useDashboardKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import './retail_pro.css'

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
  
  // Solo cargar KPIs si hay módulos de ventas activos
  const shouldLoadKPIs = modules.some(m => 
    ['ventas', 'pos', 'facturacion'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = useDashboardKPIs({ periodo: 'today', enabled: shouldLoadKPIs })

  const kpis = (kpisData || {}) as KPIData
  const ventas = kpis.ventas_dia || {}
  const stock = kpis.stock_rotacion || {}
  const comparativa = kpis.comparativa_semana || {}

  const isModuleEnabled = (moduleName: string) => {
    return modules.some(m => 
      (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
      (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  const customLinks = [
    isModuleEnabled('inventario') && { label: 'Reposición stock', href: '#reposicion', icon: '📦' },
    isModuleEnabled('ventas') && { label: 'Promociones', href: '#promociones', icon: '🏷️' },
    isModuleEnabled('ventas') && { label: 'Análisis ventas', href: '#analisis', icon: '📈' }
  ].filter(Boolean) as Array<{ label: string; href: string; icon: string }>

  return (
    <DashboardPro 
      sectorName="RetailERP" 
      sectorIcon="🏪"
      customLinks={customLinks}
    >
      <h1>🏪 Dashboard Retail / Todo a 100</h1>

      {/* Mensaje de bienvenida si solo tiene clientes */}
      {modules.length === 1 && isModuleEnabled('clientes') && (
        <section className="card full-width" style={{background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center'}}>
          <h2 style={{margin: 0, fontSize: '24px'}}>👋 ¡Bienvenido a tu ERP!</h2>
          <p style={{marginTop: '12px', opacity: 0.9}}>Comienza agregando tus clientes. Los demás módulos se activarán progresivamente.</p>
          <a href="#clientes" className="btn" style={{marginTop: '20px', display: 'inline-block', background: '#fff', color: 'var(--primary)', fontWeight: 600}}>
            👥 Ir a Clientes
          </a>
        </section>
      )}

      <div className="dashboard-grid">
        {/* Estado del día */}
        <section className="card full-width">
          <div className="card__header">
            <h3>Resumen del día</h3>
            <div className="pills">
              <span className="pill pill--ok">Tienda abierta</span>
              <span className="pill">{ventas.tickets || 0} tickets</span>
              <span className="pill">Ticket medio: €{ventas.ticket_medio?.toFixed(2) || '0.00'}</span>
            </div>
          </div>
          <div className="card__actions">
            {isModuleEnabled('pos') && <a className="link" href="#cierre">Cierre de caja</a>}
            {isModuleEnabled('inventario') && <a className="link" href="#inventario">Inventario</a>}
            {isModuleEnabled('inventario') && <a className="link" href="#reposicion">Reposición</a>}
            {isModuleEnabled('clientes') && <a className="link" href="#clientes">Ver Clientes</a>}
          </div>
        </section>

        {/* Ventas del día */}
        {isModuleEnabled('ventas') && (
        <section className="card col-6">
          <h3>💰 Ventas del día</h3>
          <div className="kpi-grid">
            <div className="kpi">
              <span className="kpi__label">Total</span>
              <span className="kpi__value">
                {kpisLoading ? '...' : `€${ventas.total?.toFixed(2) || '0.00'}`}
              </span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Tickets</span>
              <span className="kpi__value">{ventas.tickets || 0}</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Ticket medio</span>
              <span className="kpi__value">€{ventas.ticket_medio?.toFixed(2) || '0.00'}</span>
            </div>
          </div>
        </section>
        )}

        {/* Comparativa semanal */}
        {isModuleEnabled('ventas') && (
        <section className="card col-6">
          <h3>📊 Comparativa semanal</h3>
          <div className="kpi-grid">
            <div className="kpi">
              <span className="kpi__label">Esta semana</span>
              <span className="kpi__value">€{comparativa.actual?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Semana anterior</span>
              <span className="kpi__value">€{comparativa.anterior?.toFixed(2) || '0.00'}</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Variación</span>
              <span className={`kpi__value ${(comparativa.variacion || 0) >= 0 ? 'positive' : 'negative'}`}>
                {(comparativa.variacion || 0) >= 0 ? '+' : ''}{comparativa.variacion?.toFixed(1) || '0'}%
              </span>
            </div>
          </div>
        </section>
        )}

        {/* Stock rotación */}
        {isModuleEnabled('inventario') && (
        <section className="card col-4">
          <h3>📦 Rotación de stock</h3>
          <div className="list-compact">
            <li>Alta rotación: {stock.productos_alta_rotacion || 0} productos</li>
            <li>Baja rotación: {stock.productos_baja_rotacion || 0} productos</li>
            <li>Necesita reposición: {stock.reposicion_necesaria || 0}</li>
          </div>
          <div className="card__footer">
            <a className="link" href="#stock">Ver inventario →</a>
          </div>
        </section>
        )}

        {/* Acciones rápidas */}
        <section className="card col-8">
          <h3>⚡ Acciones rápidas</h3>
          <div className="action-grid">
            {isModuleEnabled('pos') && (
              <a href="#nueva-venta" className="action-btn">
                <span className="action-btn__icon">💵</span>
                <span>Nueva venta</span>
              </a>
            )}
            {isModuleEnabled('ventas') && (
              <a href="#promocion" className="action-btn">
                <span className="action-btn__icon">🏷️</span>
                <span>Crear promoción</span>
              </a>
            )}
            {isModuleEnabled('clientes') && (
              <a href="#clientes" className="action-btn">
                <span className="action-btn__icon">👥</span>
                <span>Nuevo cliente</span>
              </a>
            )}
            <a href="#ajuste-precio" className="action-btn">
              <span className="action-btn__icon">💲</span>
              <span>Ajuste de precios</span>
            </a>
            <a href="#conteo" className="action-btn">
              <span className="action-btn__icon">📋</span>
              <span>Conteo físico</span>
            </a>
          </div>
        </section>

      </div>
    </DashboardPro>
  )
}

export default RetailDashboard
