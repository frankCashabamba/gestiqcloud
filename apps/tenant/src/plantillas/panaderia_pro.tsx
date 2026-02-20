import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { usePanaderiaKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import { listRecipes, type Recipe } from '../services/api/recetas'
import {
  createProductionOrder,
  startProductionOrder,
  completeProductionOrder,
} from '../modules/productions/services'
import { listWarehouses } from '../modules/inventory/services'
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
  const [quickOpen, setQuickOpen] = useState(false)
  const [quickLoading, setQuickLoading] = useState(false)
  const [quickSaving, setQuickSaving] = useState(false)
  const [quickError, setQuickError] = useState<string | null>(null)
  const [quickSuccess, setQuickSuccess] = useState<string | null>(null)
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [qtyMode, setQtyMode] = useState<'same' | 'other'>('same')
  const [otherQty, setOtherQty] = useState<string>('')

  const isModuleEnabled = (moduleName: string) => {
    return modules.some(
      (m) =>
        (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
        (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )
  }
  const isProductionEnabled = () =>
    modules.some((m) => {
      const slug = (m.slug || '').toLowerCase()
      const name = (m.name || '').toLowerCase()
      return (
        slug === 'produccion' ||
        slug === 'production' ||
        slug === 'productions' ||
        slug === 'manufacturing' ||
        name.includes('produccion') ||
        name.includes('production') ||
        name.includes('manufacturing')
      )
    })

  const prefix = empresa ? `/${empresa}` : ''
  const customLinks = [
    isProductionEnabled() && { label: 'Recipes', href: `${prefix}/produccion/recetas`, icon: 'R' },
    isModuleEnabled('inventario') && { label: 'Inventory', href: `${prefix}/inventory`, icon: 'I' },
    isModuleEnabled('compras') && { label: 'Purchasing', href: `${prefix}/purchases`, icon: 'P' },
  ].filter(Boolean) as Array<{ label: string; href: string; icon: string }>

  useEffect(() => {
    if (!quickOpen) return
    let cancelled = false
    ;(async () => {
      try {
        setQuickLoading(true)
        setQuickError(null)
        const data = await listRecipes({ limit: 500, activo: true })
        if (cancelled) return
        const list = Array.isArray(data) ? data : []
        setRecipes(list)
        if (!selectedRecipeId && list.length > 0) {
          setSelectedRecipeId(list[0].id)
          setOtherQty(String(Number(list[0].yield_qty || 1)))
        }
      } catch (e: any) {
        if (!cancelled) setQuickError(e?.message || 'Could not load recipes')
      } finally {
        if (!cancelled) setQuickLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [quickOpen])

  const selectedRecipe = useMemo(
    () => recipes.find((r) => r.id === selectedRecipeId) || null,
    [recipes, selectedRecipeId]
  )

  const effectiveQty = useMemo(() => {
    if (!selectedRecipe) return 0
    if (qtyMode === 'same') return Number(selectedRecipe.yield_qty || 0)
    return Number(otherQty || 0)
  }, [selectedRecipe, qtyMode, otherQty])

  const handleQuickProduction = async () => {
    if (!selectedRecipe) {
      setQuickError('Select a recipe')
      return
    }
    if (!effectiveQty || effectiveQty <= 0) {
      setQuickError('Quantity must be greater than 0')
      return
    }

    try {
      setQuickSaving(true)
      setQuickError(null)
      setQuickSuccess(null)

      const whs = await listWarehouses().catch(() => [])
      const wh = Array.isArray(whs) ? (whs.find((w) => w.is_active) || whs[0]) : null

      const order = await createProductionOrder({
        recipe_id: selectedRecipe.id,
        product_id: selectedRecipe.product_id,
        warehouse_id: wh ? String(wh.id) : undefined,
        qty_planned: effectiveQty,
        scheduled_date: new Date().toISOString(),
        status: 'draft',
      } as any)

      await startProductionOrder(order.id)
      await completeProductionOrder(order.id, { qty_produced: effectiveQty, waste_qty: 0 })

      setQuickSuccess(`Production completed. Inventory updated with qty ${effectiveQty}.`)
      setQuickOpen(false)
    } catch (e: any) {
      setQuickError(e?.message || 'Quick production failed')
    } finally {
      setQuickSaving(false)
    }
  }

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
            {isProductionEnabled() && (
              <button
                type="button"
                className="link"
                onClick={() => {
                  setQuickSuccess(null)
                  setQuickError(null)
                  setQuickOpen(true)
                }}
              >
                New production
              </button>
            )}
            {isProductionEnabled() && <a className="link" href={`${prefix}/produccion/recetas`}>Recipes</a>}
            {isModuleEnabled('ventas') && <a className="link" href={`${prefix}/sales`}>Sales</a>}
            {isModuleEnabled('clientes') && <a className="link" href={`${prefix}/clients`}>Customers</a>}
          </div>
          {quickSuccess && <p className="text-sm mt-2" style={{ color: '#166534' }}>{quickSuccess}</p>}
          {quickError && <p className="text-sm mt-2" style={{ color: '#b91c1c' }}>{quickError}</p>}
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
          </section>
        )}

        {isProductionEnabled() && (
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
            {isModuleEnabled('clientes') && (
              <a href={`${prefix}/clients`} className="action-btn">
                <span className="action-btn__icon">@</span>
                <span>New customer</span>
              </a>
            )}
          </div>
        </section>
      </div>

      {quickOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 3000,
            padding: 16,
          }}
          onClick={() => !quickSaving && setQuickOpen(false)}
        >
          <div
            className="card"
            style={{ width: '100%', maxWidth: 520 }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginTop: 0, marginBottom: 12 }}>Quick production</h3>
            {quickLoading ? (
              <p>Loading recipes...</p>
            ) : (
              <>
                <label style={{ display: 'block', fontSize: 14, marginBottom: 6 }}>Recipe</label>
                <select
                  style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #d1d5db', marginBottom: 12 }}
                  value={selectedRecipeId}
                  onChange={(e) => {
                    const rid = e.target.value
                    setSelectedRecipeId(rid)
                    const rec = recipes.find((r) => r.id === rid)
                    if (rec) setOtherQty(String(Number(rec.yield_qty || 1)))
                  }}
                  disabled={quickSaving}
                >
                  {recipes.length === 0 && <option value="">No recipes</option>}
                  {recipes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>

                <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                  <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                    <input
                      type="radio"
                      checked={qtyMode === 'same'}
                      onChange={() => setQtyMode('same')}
                      disabled={quickSaving}
                    />
                    Same recipe quantity ({selectedRecipe?.yield_qty || 0})
                  </label>
                  <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                    <input
                      type="radio"
                      checked={qtyMode === 'other'}
                      onChange={() => setQtyMode('other')}
                      disabled={quickSaving}
                    />
                    Other quantity
                  </label>
                </div>

                {qtyMode === 'other' && (
                  <input
                    type="number"
                    min={0.01}
                    step={0.01}
                    value={otherQty}
                    onChange={(e) => setOtherQty(e.target.value)}
                    disabled={quickSaving}
                    style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #d1d5db', marginBottom: 12 }}
                  />
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 13, color: '#4b5563' }}>
                    Final qty: <strong>{effectiveQty || 0}</strong>
                  </span>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      className="action-btn"
                      onClick={() => setQuickOpen(false)}
                      disabled={quickSaving}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="action-btn action-btn--primary"
                      onClick={handleQuickProduction}
                      disabled={quickSaving || !effectiveQty || effectiveQty <= 0}
                    >
                      {quickSaving ? 'Processing...' : 'Produce now'}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </DashboardPro>
  )
}

export default PanaderiaDashboard
