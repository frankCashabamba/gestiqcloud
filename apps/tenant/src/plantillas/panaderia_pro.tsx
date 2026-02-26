import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { usePanaderiaKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import DashboardPro from './components/DashboardPro'
import { listRecipes, getRecipe, type Recipe, type RecipeIngredientResponse } from '../services/api/recetas'
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
    ['sales', 'pos', 'produccion', 'inventario'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = usePanaderiaKPIs({ enabled: shouldLoadKPIs })

  const kpis = (kpisData || {}) as KPIData
  const ventas = kpis.ventas_mostrador || {}
  const stock = kpis.stock_critico || {}
  const mermas = kpis.mermas || {}
  const produccion = kpis.produccion || {}
  const hornadasPendientes = Math.max(
    (produccion.hornadas_programadas || 0) - (produccion.hornadas_completadas || 0),
    0
  )
  const ingredientes = kpis.ingredientes_caducar || {}
  const topProductos = kpis.top_productos || []
  const [quickOpen, setQuickOpen] = useState(false)
  const [quickLoading, setQuickLoading] = useState(false)
  const [quickSaving, setQuickSaving] = useState(false)
  const [quickError, setQuickError] = useState<string | null>(null)
  const [quickSuccess, setQuickSuccess] = useState<string | null>(null)
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [qtyMode, setQtyMode] = useState<'same' | 'other' | 'ingrediente'>('same')
  const [otherQty, setOtherQty] = useState<string>('')
  const [recipeDetail, setRecipeDetail] = useState<Recipe | null>(null)
  const [selectedIngredientId, setSelectedIngredientId] = useState('')
  const [ingredientAmount, setIngredientAmount] = useState('')
  const [ingredientInputUnit, setIngredientInputUnit] = useState('lb')

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

  const WEIGHT_UNITS = ['g', 'kg', 'lb', 'oz']
  const isWeightUnit = (unit: string) => WEIGHT_UNITS.includes((unit || '').toLowerCase())
  const convertToGrams = (amount: number, unit: string): number => {
    switch ((unit || '').toLowerCase()) {
      case 'kg': return amount * 1000
      case 'lb': return amount * 453.592
      case 'oz': return amount * 28.3495
      default: return amount
    }
  }
  const formatWeight = (grams: number) => {
    const lb = grams / 453.592
    const kg = grams / 1000
    return `${grams.toFixed(0)} g (${lb.toFixed(2)} lb / ${kg.toFixed(2)} kg)`
  }

  const prefix = empresa ? `/${empresa}` : ''
  const customLinks = [
    isProductionEnabled() && { label: 'Recetas', href: `${prefix}/produccion/recetas`, icon: 'R' },
    isModuleEnabled('inventario') && { label: 'Inventario', href: `${prefix}/inventory`, icon: 'I' },
    isModuleEnabled('compras') && { label: 'Compras', href: `${prefix}/purchases`, icon: 'P' },
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
        if (!cancelled) setQuickError(e?.message || 'No se pudieron cargar las recetas')
      } finally {
        if (!cancelled) setQuickLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [quickOpen])

  useEffect(() => {
    if (!selectedRecipeId || !quickOpen) return
    let cancelled = false
    ;(async () => {
      try {
        const detail = await getRecipe(selectedRecipeId)
        if (cancelled) return
        setRecipeDetail(detail)
        const ings = detail.ingredients || []
        if (ings.length > 0) {
          setSelectedIngredientId(ings[0].id)
        }
      } catch {}
    })()
    return () => { cancelled = true }
  }, [selectedRecipeId, quickOpen])

  const selectedRecipe = useMemo(
    () => recipes.find((r) => r.id === selectedRecipeId) || null,
    [recipes, selectedRecipeId]
  )

  const recipeIngredients = useMemo(
    () => recipeDetail?.ingredients || selectedRecipe?.ingredients || [],
    [recipeDetail, selectedRecipe]
  )

  const selectedIngredient = useMemo(
    () => recipeIngredients.find((i) => i.id === selectedIngredientId) || null,
    [recipeIngredients, selectedIngredientId]
  )

  const effectiveQty = useMemo(() => {
    if (!selectedRecipe) return 0
    if (qtyMode === 'same') return Number(selectedRecipe.yield_qty || 0)
    if (qtyMode === 'other') return Number(otherQty || 0)
    if (qtyMode === 'ingrediente') {
      if (!selectedIngredient || !ingredientAmount) return 0
      const inputAmount = Number(ingredientAmount)
      if (!inputAmount || inputAmount <= 0) return 0
      let ratio: number
      if (isWeightUnit(selectedIngredient.unit)) {
        const recipeQtyGrams = convertToGrams(selectedIngredient.qty, selectedIngredient.unit)
        const inputQtyGrams = convertToGrams(inputAmount, ingredientInputUnit)
        ratio = inputQtyGrams / recipeQtyGrams
      } else {
        ratio = inputAmount / selectedIngredient.qty
      }
      return Math.floor(ratio * (selectedRecipe.yield_qty || 0))
    }
    return 0
  }, [selectedRecipe, qtyMode, otherQty, selectedIngredient, ingredientAmount, ingredientInputUnit])

  const handleQuickProduction = async () => {
    if (!selectedRecipe) {
      setQuickError('Seleccione una receta')
      return
    }
    if (!effectiveQty || effectiveQty <= 0) {
      setQuickError('La cantidad debe ser mayor a 0')
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

      setQuickSuccess(`Producción completada. Inventario actualizado con ${effectiveQty} uds.`)
      setQuickOpen(false)
    } catch (e: any) {
      setQuickError(e?.message || 'Error en producción rápida')
    } finally {
      setQuickSaving(false)
    }
  }

  return (
    <DashboardPro sectorName="Panadería ERP" sectorIcon="B" customLinks={customLinks}>
      <h1>Resumen de Panadería</h1>

      {modules.length === 1 && isModuleEnabled('clientes') && (
        <section
          className="card full-width"
          style={{ background: 'linear-gradient(135deg, var(--primary), var(--focus))', color: '#fff', padding: '40px', textAlign: 'center' }}
        >
          <h2 style={{ margin: 0, fontSize: '24px' }}>Bienvenido a su ERP</h2>
          <p style={{ marginTop: '12px', opacity: 0.9 }}>
            Comience agregando sus clientes. Otros módulos se habilitarán a medida que avance.
          </p>
          <a href={`${prefix}/clients`} className="btn" style={{ marginTop: '20px', display: 'inline-block', background: '#fff', color: 'var(--primary)', fontWeight: 600 }}>
            Ir a Clientes
          </a>
        </section>
      )}

      <div className="dashboard-grid">
        <section className="card full-width">
          <div className="card__header">
            <h3>Estado del día</h3>
            <div className="pills">
              <span className="pill pill--ok">Operativo</span>
              {isModuleEnabled('ventas') && ventas.hoy && ventas.hoy > 0 && (
                <span className="pill">
                  Ventas hoy: {ventas.moneda || '$'}
                  {ventas.hoy.toFixed(2)}
                </span>
              )}
            </div>
          </div>
          <div className="card__actions">
            {isModuleEnabled('pos') && (
              <a className="link" href={`${prefix}/pos`}>
                Abrir POS
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
                Nueva producción
              </button>
            )}
            {isProductionEnabled() && <a className="link" href={`${prefix}/produccion/recetas`}>Recetas</a>}
            {isModuleEnabled('ventas') && <a className="link" href={`${prefix}/sales`}>Ventas</a>}
            {isModuleEnabled('clientes') && <a className="link" href={`${prefix}/clients`}>Clientes</a>}
          </div>
          {quickSuccess && <p className="text-sm mt-2" style={{ color: '#166534' }}>{quickSuccess}</p>}
          {quickError && <p className="text-sm mt-2" style={{ color: '#b91c1c' }}>{quickError}</p>}
        </section>

        {isModuleEnabled('ventas') && (
          <section className="card col-6">
            <h3>Ventas de hoy</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">Hoy</span>
                <span className="kpi__value">{kpisLoading ? '...' : `$${ventas.hoy?.toFixed(2) || '0.00'}`}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Ayer</span>
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
            <h3>Stock crítico</h3>
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
          </section>
        )}

        {isModuleEnabled('inventario') && (
          <section className="card col-3">
            <h3>Merma de hoy</h3>
            <div className="stat-large">
              <span className="stat-large__value">{mermas.hoy || 0}</span>
              <span className="stat-large__label">kg</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">Valor estimado</span>
              <span className="kpi__value">${mermas.valor_estimado?.toFixed(2) || '0.00'}</span>
            </div>
          </section>
        )}

        {isProductionEnabled() && (
          <section className="card col-4">
            <h3>Hornadas de producción</h3>
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
              <span className="pill pill--ok">En curso</span>
              <span className="pill">{hornadasPendientes} pendientes</span>
            </div>
          </section>
        )}

        {isModuleEnabled('inventario') && (
          <section className="card col-4">
            <h3>Ingredientes por vencer</h3>
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

        {isModuleEnabled('ventas') && (
          <section className="card col-4">
            <h3>Productos más vendidos</h3>
            <div className="table-compact">
              {topProductos.length > 0 ? (
                <table>
                  <tbody>
                    {topProductos.map((prod: any, i: number) => (
                      <tr key={i}>
                        <td>{prod.name}</td>
                        <td className="text-right">{prod.unidades} uds</td>
                        <td className="text-right">${prod.ingresos?.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-state">Sin datos</p>
              )}
            </div>
          </section>
        )}

        {isModuleEnabled('ventas') && (
          <section className="card col-8">
            <h3>Ventas por hora</h3>
            <div className="chart-container">
              <div className="chart-placeholder">
                <canvas id="salesChart" height="200"></canvas>
                <p className="chart-empty">Gráfico en proceso</p>
              </div>
            </div>
            <div className="pills">
              <span className="pill">Real</span>
              <span className="pill">Pronóstico</span>
              <span className="pill">Meta</span>
            </div>
          </section>
        )}

        <section className="card col-4">
          <h3>Acciones rápidas</h3>
          <div className="action-grid">
            {isModuleEnabled('pos') && (
              <a href={`${prefix}/pos`} className="action-btn action-btn--primary">
                <span className="action-btn__icon">P</span>
                <span>Abrir POS</span>
              </a>
            )}
            {isModuleEnabled('clientes') && (
              <a href={`${prefix}/clients`} className="action-btn">
                <span className="action-btn__icon">@</span>
                <span>Nuevo cliente</span>
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
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !quickSaving) setQuickOpen(false)
          }}
        >
          <div
            className="card"
            style={{ width: '100%', maxWidth: 560 }}
          >
            <h3 style={{ marginTop: 0, marginBottom: 12 }}>Producción rápida</h3>
            {quickLoading ? (
              <p>Cargando recetas...</p>
            ) : (
              <>
                <label style={{ display: 'block', fontSize: 14, marginBottom: 6 }}>Receta</label>
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
                  {recipes.length === 0 && <option value="">Sin recetas</option>}
                  {recipes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
                  <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontSize: 14 }}>
                    <input
                      type="radio"
                      checked={qtyMode === 'same'}
                      onChange={() => setQtyMode('same')}
                      disabled={quickSaving}
                    />
                    Misma cantidad ({selectedRecipe?.yield_qty || 0})
                  </label>
                  <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontSize: 14 }}>
                    <input
                      type="radio"
                      checked={qtyMode === 'other'}
                      onChange={() => setQtyMode('other')}
                      disabled={quickSaving}
                    />
                    Otra cantidad
                  </label>
                  <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontSize: 14 }}>
                    <input
                      type="radio"
                      checked={qtyMode === 'ingrediente'}
                      onChange={() => setQtyMode('ingrediente')}
                      disabled={quickSaving}
                    />
                    Por ingrediente
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
                    placeholder="Cantidad de unidades a producir"
                    style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #d1d5db', marginBottom: 12 }}
                  />
                )}

                {qtyMode === 'ingrediente' && (
                  <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 12 }}>
                    {recipeIngredients.length === 0 ? (
                      <p style={{ margin: 0, fontSize: 13, color: '#64748b' }}>Cargando ingredientes...</p>
                    ) : (
                      <>
                        <label style={{ display: 'block', fontSize: 13, marginBottom: 4, color: '#475569' }}>Ingrediente</label>
                        <select
                          style={{ width: '100%', padding: 8, borderRadius: 6, border: '1px solid #d1d5db', marginBottom: 8 }}
                          value={selectedIngredientId}
                          onChange={(e) => {
                            setSelectedIngredientId(e.target.value)
                            setIngredientAmount('')
                            const ing = recipeIngredients.find((i) => i.id === e.target.value)
                            if (ing && isWeightUnit(ing.unit)) {
                              setIngredientInputUnit('lb')
                            } else if (ing) {
                              setIngredientInputUnit(ing.unit)
                            }
                          }}
                          disabled={quickSaving}
                        >
                          {recipeIngredients.map((ing) => (
                            <option key={ing.id} value={ing.id}>
                              {ing.product_name || ing.product_id} — {ing.qty} {ing.unit}
                              {isWeightUnit(ing.unit) ? ` (${(convertToGrams(ing.qty, ing.unit) / 453.592).toFixed(2)} lb)` : ''}
                            </option>
                          ))}
                        </select>

                        {selectedIngredient && (
                          <>
                            <label style={{ display: 'block', fontSize: 13, marginBottom: 4, color: '#475569' }}>
                              Cantidad disponible
                            </label>
                            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                              <input
                                type="number"
                                min={0.01}
                                step={0.01}
                                value={ingredientAmount}
                                onChange={(e) => setIngredientAmount(e.target.value)}
                                disabled={quickSaving}
                                placeholder={`Ej: 10`}
                                style={{ flex: 1, padding: 8, borderRadius: 6, border: '1px solid #d1d5db' }}
                              />
                              {isWeightUnit(selectedIngredient.unit) ? (
                                <select
                                  style={{ width: 70, padding: 8, borderRadius: 6, border: '1px solid #d1d5db' }}
                                  value={ingredientInputUnit}
                                  onChange={(e) => setIngredientInputUnit(e.target.value)}
                                  disabled={quickSaving}
                                >
                                  <option value="lb">lb</option>
                                  <option value="kg">kg</option>
                                  <option value="g">g</option>
                                </select>
                              ) : (
                                <span style={{ padding: '8px 12px', background: '#e2e8f0', borderRadius: 6, fontSize: 14 }}>
                                  {selectedIngredient.unit}
                                </span>
                              )}
                            </div>
                            <p style={{ margin: 0, fontSize: 12, color: '#64748b' }}>
                              Receta usa: <strong>{selectedIngredient.qty} {selectedIngredient.unit}</strong>
                              {isWeightUnit(selectedIngredient.unit) &&
                                ` (${(convertToGrams(selectedIngredient.qty, selectedIngredient.unit) / 453.592).toFixed(2)} lb)`
                              }
                              {' → '}{selectedRecipe?.yield_qty || 0} uds
                            </p>
                          </>
                        )}
                      </>
                    )}
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 14, color: '#4b5563' }}>
                    Cantidad final: <strong style={{ fontSize: 18 }}>{effectiveQty || 0}</strong> uds
                  </span>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      className="action-btn"
                      onClick={() => setQuickOpen(false)}
                      disabled={quickSaving}
                    >
                      Cancelar
                    </button>
                    <button
                      type="button"
                      className="action-btn action-btn--primary"
                      onClick={handleQuickProduction}
                      disabled={quickSaving || !effectiveQty || effectiveQty <= 0}
                    >
                      {quickSaving ? 'Procesando...' : 'Producir ahora'}
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
