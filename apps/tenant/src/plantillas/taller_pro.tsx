import React from 'react'
import { useTallerKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import './taller_pro.css'

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
  
  // Solo cargar KPIs si hay módulos de finanzas/ventas activos
  const shouldLoadKPIs = modules.some(m => 
    ['ventas', 'finanzas', 'facturacion'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = useTallerKPIs({ enabled: shouldLoadKPIs })

  const kpis = (kpisData || {}) as KPIData
  const reparaciones = kpis.reparaciones_pendientes || {}
  const ingresos = kpis.ingresos_mes || {}
  const repuestos = kpis.repuestos_bajo_stock || {}
  const trabajos = kpis.trabajos_completados || {}

  const isModuleEnabled = (moduleName: string) => {
    return modules.some(m => 
      (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
      (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }

  const customLinks = [
    isModuleEnabled('ventas') && { label: 'Orden de trabajo', href: '#nueva-ot', icon: '🔧' },
    isModuleEnabled('facturacion') && { label: 'Presupuestos', href: '#presupuestos', icon: '💰' },
    isModuleEnabled('inventario') && { label: 'Control calidad', href: '#calidad', icon: '✅' }
  ].filter(Boolean) as Array<{ label: string; href: string; icon: string }>

  return (
    <DashboardPro 
      sectorName="TallerERP" 
      sectorIcon="🔧"
      customLinks={customLinks}
    >
      <h1>🔧 Panel del Taller Mecánico</h1>

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
            <h3>Estado operativo</h3>
            <div className="pills">
              <span className="pill pill--ok">Taller operativo</span>
              <span className="pill">{reparaciones.total || 0} trabajos en proceso</span>
              <span className="pill pill--warn">{reparaciones.urgentes || 0} urgentes</span>
            </div>
          </div>
          <div className="card__actions">
            {isModuleEnabled('ventas') && <a className="link" href="#ot">Nueva OT</a>}
            {isModuleEnabled('facturacion') && <a className="link" href="#presupuesto">Presupuesto</a>}
            {isModuleEnabled('inventario') && <a className="link" href="#inventario">Pedir repuestos</a>}
            {isModuleEnabled('clientes') && <a className="link" href="#clientes">Ver Clientes</a>}
          </div>
        </section>

        {/* Ingresos del mes */}
        {isModuleEnabled('finanzas') && (
        <section className="card col-6">
          <h3>💰 Ingresos del mes</h3>
          <div className="kpi-grid">
            <div className="kpi">
              <span className="kpi__label">Actual</span>
              <span className="kpi__value">
                {kpisLoading ? '...' : `€${ingresos.actual?.toFixed(2) || '0.00'}`}
              </span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Objetivo</span>
              <span className="kpi__value">€{ingresos.objetivo?.toFixed(2) || '0.00'}</span>
            </div>
          </div>
          <div className="progress-stat">
            <div className="progress-stat__header">
              <span>Progreso mensual</span>
              <span>{ingresos.progreso?.toFixed(0) || 0}%</span>
            </div>
            <div className="progress-bar">
              <div 
                className="progress-bar__fill" 
                style={{ width: `${ingresos.progreso || 0}%` }}
              />
            </div>
          </div>
        </section>
        )}

        {/* Repuestos bajo stock */}
        {isModuleEnabled('inventario') && (
        <section className="card col-3">
          <h3>⚠️ Repuestos críticos</h3>
          <div className="stat-large">
            <span className="stat-large__value">{repuestos.items || 0}</span>
            <span className="stat-large__label">repuestos</span>
          </div>
          {repuestos.nombres && repuestos.nombres.length > 0 && (
            <ul className="list-compact">
              {repuestos.nombres.slice(0, 3).map((item: string, i: number) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
          <div className="card__footer">
            <a className="link" href="#repuestos">Pedir ahora →</a>
          </div>
        </section>
        )}

        {/* Trabajos completados */}
        {isModuleEnabled('ventas') && (
        <section className="card col-3">
          <h3>✅ Trabajos completados</h3>
          <div className="kpi-grid">
            <div className="kpi">
              <span className="kpi__label">Hoy</span>
              <span className="kpi__value">{trabajos.hoy || 0}</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Este mes</span>
              <span className="kpi__value">{trabajos.mes || 0}</span>
            </div>
          </div>
        </section>
        )}

        {/* Reparaciones pendientes */}
        {isModuleEnabled('ventas') && (
        <section className="card col-4">
          <h3>🕐 Reparaciones pendientes</h3>
          <div className="stat-large">
            <span className="stat-large__value">{reparaciones.total || 0}</span>
            <span className="stat-large__label">órdenes</span>
          </div>
          <div className="pills">
            <span className="pill pill--err">{reparaciones.urgentes || 0} urgentes</span>
            <span className="pill">
              {reparaciones.tiempo_medio_espera?.toFixed(1) || '0'} días espera
            </span>
          </div>
        </section>
        )}

        {/* Acciones rápidas */}
        <section className="card col-8">
          <h3>⚡ Acciones rápidas</h3>
          <div className="action-grid">
            {isModuleEnabled('ventas') && (
              <a href="#nueva-ot" className="action-btn">
                <span className="action-btn__icon">🔧</span>
                <span>Nueva OT</span>
              </a>
            )}
            {isModuleEnabled('facturacion') && (
              <a href="#presupuesto" className="action-btn">
                <span className="action-btn__icon">💰</span>
                <span>Presupuesto</span>
              </a>
            )}
            {isModuleEnabled('ventas') && (
              <a href="#diagnostico" className="action-btn">
                <span className="action-btn__icon">🔍</span>
                <span>Diagnóstico</span>
              </a>
            )}
            {isModuleEnabled('ventas') && (
              <a href="#entrega" className="action-btn">
                <span className="action-btn__icon">🚗</span>
                <span>Entregar vehículo</span>
              </a>
            )}
            {isModuleEnabled('clientes') && (
              <a href="#clientes" className="action-btn">
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

export default TallerDashboard
