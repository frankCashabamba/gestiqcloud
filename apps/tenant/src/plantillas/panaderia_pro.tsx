import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { formatCurrency, usePanaderiaKPIs } from '../hooks/useDashboardKPIs'
import { useMisModulos } from '../hooks/useMisModulos'
import { canonicalizeCompanyModuleKey } from '../lib/companyModuleKeys'
import type { Modulo } from '../services/modules'
import DashboardPro from './components/DashboardPro'
import {
  calculateProduction,
  getRecipe,
  listRecipes,
  type ProductionCalculation,
  type Recipe,
  type RecipeIngredientResponse,
} from '../services/api/recetas'
import { getRecipeFullCost, listCostDrivers, type CostDriver, type FullCostSummary } from '../services/api/productionCosts'
import {
  createProductionOrder,
  startProductionOrder,
  completeProductionOrder,
  replaceProductionOrderCosts,
  type ProductionOrderCostInput,
} from '../modules/productions/services'
import { listWarehouses, listStockItems } from '../modules/inventory/services'
import { createVenta, checkoutOrder, type VentaLinea } from '../modules/sales/services'
import QuickOrderModal from '../modules/sales/components/QuickOrderModal'
import './dashboard_pro.css'
import './bakery_premium.css'

// ─── Types ────────────────────────────────────────────────────────────────────

interface KPIData {
  ventas_mostrador?: { hoy?: number; ayer?: number; variacion?: number; moneda?: string }
  stock_critico?: {
    items?: number
    nombres?: string[]
    urgencia?: string
    productos_venta?: { items?: number; nombres?: string[] }
    materias_primas?: { items?: number; nombres?: string[] }
  }
  mermas?: { hoy?: number; unidad?: string; valor_estimado?: number; moneda?: string }
  produccion?: { hornadas_completadas?: number; hornadas_programadas?: number; progreso?: number; pedidos_con_receta?: number }
  ingredientes_caducar?: { proximos_7_dias?: number; items?: string[] }
  top_productos?: Array<{ name: string; unidades: number; ingresos: number }>
  pedidos?: { pendientes_cobro?: number; pendientes_entrega?: number }
}

type StockAlertGroup = {
  items: number
  nombres: string[]
}

type QuickCostDraft = {
  key: string
  driver_id: string
  qty_actual: string
  headcount_actual: string
  rate_applied: string
  notes: string
}

// ─── Helpers (unchanged) ──────────────────────────────────────────────────────

const toNumber = (value: unknown): number => {
  const next = Number(value)
  return Number.isFinite(next) ? next : 0
}

const formatMoney = (value: unknown): string => `$${toNumber(value).toFixed(2)}`

const formatDashboardMoney = (value: unknown, currency?: string | null): string =>
  formatCurrency(toNumber(value), currency || undefined)

const WEIGHT_UNITS = ['g', 'kg', 'lb', 'oz']
const isWeightUnit = (unit: string) => WEIGHT_UNITS.includes((unit || '').toLowerCase())

const convertToGrams = (amount: number, unit: string): number => {
  switch ((unit || '').toLowerCase()) {
    case 'kg': return amount * 1000
    case 'lb': return amount * 453.592
    case 'oz': return amount * 28.3495
    default:   return amount
  }
}

const convertFromGrams = (grams: number, unit: string): number => {
  switch ((unit || '').toLowerCase()) {
    case 'kg': return grams / 1000
    case 'lb': return grams / 453.592
    case 'oz': return grams / 28.3495
    default:   return grams
  }
}

const buildQuickCostLines = (
  summary: FullCostSummary | null,
  selectedQty: number,
  recipeYield: number,
): QuickCostDraft[] => {
  if (!summary || !Array.isArray(summary.cost_lines) || summary.cost_lines.length === 0) return []
  const safeYield = recipeYield > 0 ? recipeYield : 1
  const scaleFactor = selectedQty > 0 ? selectedQty / safeYield : 1
  return summary.cost_lines.map((line, idx) => ({
    key: `base-${line.id || idx}`,
    driver_id: String(line.driver_id || ''),
    qty_actual: String((toNumber(line.qty_standard) * scaleFactor).toFixed(4)),
    headcount_actual: String(Math.max(toNumber(line.headcount) || 1, 1)),
    rate_applied: String(toNumber(line.effective_rate ?? line.driver_default_rate).toFixed(4)),
    notes: String(line.notes || ''),
  }))
}

const createEmptyQuickCost = (driverId = ''): QuickCostDraft => ({
  key: `custom-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  driver_id: driverId,
  qty_actual: '',
  headcount_actual: '1',
  rate_applied: '',
  notes: '',
})

const getQuickErrorMessage = (error: any): string => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const flat = detail.map((item: any) => String(item?.msg || item)).filter(Boolean)
    if (flat.length > 0) return flat.join('; ')
  }
  if (typeof error?.message === 'string' && error.message.trim()) return error.message
  return ''
}

const normalizeModuleToken = (value: string): string =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '')

const buildModuleHref = (prefix: string, module: Pick<Modulo, 'slug' | 'name'>): string => {
  const slug = canonicalizeCompanyModuleKey(module.slug || module.name || '')
  return `${prefix}/${slug}`
}

type FocusModuleAppearance = {
  eyebrow: string
  summary: string
  actionLabel: string
  accent: 'amber' | 'blue' | 'slate' | 'olive'
}

const getFocusModuleAppearance = (module: Pick<Modulo, 'slug' | 'name'>): FocusModuleAppearance => {
  const slug = normalizeModuleToken(module.slug || '')
  const name = normalizeModuleToken(module.name || '')
  const key = slug || name

  if (key.includes('pos') || key.includes('puntodeventa') || key.includes('puntoventa') || name.includes('caja')) {
    return {
      eyebrow: 'Venta directa',
      summary: 'Caja, cobro y atencion del mostrador listos para trabajar sin pasos extra.',
      actionLabel: 'Abrir POS',
      accent: 'amber',
    }
  }

  if (key.includes('import') || key.includes('document')) {
    return {
      eyebrow: 'Carga documental',
      summary: 'Revisa importaciones, adjunta soportes y deja la documentacion operativa al dia.',
      actionLabel: 'Abrir importaciones',
      accent: 'blue',
    }
  }

  if (key.includes('rrhh') || key === 'hr' || name.includes('personal') || name.includes('jornada')) {
    return {
      eyebrow: 'Equipo',
      summary: 'Accede a jornada, fichajes y tareas de RRHH desde un panel mas claro para empleado.',
      actionLabel: 'Abrir RRHH',
      accent: 'slate',
    }
  }

  return {
    eyebrow: 'Modulo habilitado',
    summary: 'Acceso directo al espacio de trabajo asignado para este turno.',
    actionLabel: 'Abrir modulo',
    accent: 'olive',
  }
}

const BakeryEmployeeWorkspace: React.FC<{
  modules: Modulo[]
  prefix: string
}> = ({ modules, prefix }) => {
  const dayLabel = new Date().toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' })
  const cards = modules.map((module) => ({
    ...getFocusModuleAppearance(module),
    id: module.id,
    name: module.name,
    href: buildModuleHref(prefix, module),
  }))

  return (
    <section className="bakery-workspace">
      <div className="bakery-workspace__intro">
        <div>
          <span className="bakery-workspace__eyebrow">Acceso operativo</span>
          <h2 className="bakery-workspace__title">Panel de empleado enfocado en el turno</h2>
          <p className="bakery-workspace__desc">
            Esta cuenta trabaja con {cards.length} modulos. Priorizamos accesos directos y tareas concretas para evitar un panel vacio o demasiado administrativo.
          </p>
        </div>
        <div className="bakery-workspace__meta">
          <span className="bakery-workspace__pill">{cards.length} modulos activos</span>
          <span className="bakery-workspace__pill bakery-workspace__pill--soft">{dayLabel}</span>
        </div>
      </div>

      <div className="bakery-workspace__grid">
        {cards.map((card) => (
          <Link
            key={card.id}
            to={card.href}
            className={`bakery-workspace-card bakery-workspace-card--${card.accent}`}
          >
            <div className="bakery-workspace-card__header">
              <span className="bakery-workspace-card__eyebrow">{card.eyebrow}</span>
              <span className="bakery-workspace-card__status">Disponible</span>
            </div>
            <div className="bakery-workspace-card__body">
              <h3>{card.name}</h3>
              <p>{card.summary}</p>
            </div>
            <div className="bakery-workspace-card__footer">
              <span>{card.actionLabel}</span>
              <span className="bakery-workspace-card__arrow">-&gt;</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}

// ─── BakeryHero ───────────────────────────────────────────────────────────────

interface BakeryHeroProps {
  ventas: { hoy?: number; moneda?: string }
  hornadasPendientes: number
  stockVenta: StockAlertGroup
  stockMateriaPrima: StockAlertGroup
  loading: boolean
  isModuleEnabled: (s: string) => boolean
  isProductionEnabled: () => boolean
  prefix: string
  onNuevaProduccion: () => void
  onNuevoPedido: () => void
  hidePosShortcut?: boolean
}

const BakeryHero: React.FC<BakeryHeroProps> = ({
  ventas, hornadasPendientes, stockVenta, stockMateriaPrima, loading,
  isModuleEnabled, isProductionEnabled, prefix, onNuevaProduccion, onNuevoPedido,
  hidePosShortcut = false,
}) => {
  const dayName = new Date().toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' })
  const showSalesAction = isModuleEnabled('sales')
  const showProductionAction = isProductionEnabled()
  const showPosAction = isModuleEnabled('pos') && !hidePosShortcut
  const hasActions = showSalesAction || showProductionAction || showPosAction
  return (
    <div className="bakery-hero">
      <div className="bakery-hero__left">
        <div className="bakery-hero__meta">
          <span className="pill pill--ok">Operativo</span>
          <span className="bakery-hero__date">{dayName}</span>
        </div>
        <div className="bakery-hero__kpi-row">
          {isModuleEnabled('sales') && (
            <div className="bakery-hero__kpi">
              <span className="bakery-hero__kpi-value">
                {loading ? '—' : formatDashboardMoney(ventas.hoy, ventas.moneda)}
              </span>
              <span className="bakery-hero__kpi-label">Ventas hoy</span>
            </div>
          )}
          {isProductionEnabled() && (
            <>
              <div className="bakery-hero__kpi-divider" />
              <div className="bakery-hero__kpi">
                <span className={`bakery-hero__kpi-value${hornadasPendientes > 0 ? ' bakery-hero__kpi-value--warn' : ''}`}>
                  {hornadasPendientes}
                </span>
                <span className="bakery-hero__kpi-label">Hornadas pendientes</span>
              </div>
            </>
          )}
          {isModuleEnabled('inventory') && (
            <>
              <div className="bakery-hero__kpi-divider" />
              <div className="bakery-hero__kpi">
                <span className={`bakery-hero__kpi-value${stockVenta.items > 0 ? ' bakery-hero__kpi-value--err' : ''}`}>
                  {stockVenta.items}
                </span>
                <span className="bakery-hero__kpi-label">Prod. venta crítico</span>
              </div>
              <div className="bakery-hero__kpi-divider" />
              <div className="bakery-hero__kpi">
                <span className={`bakery-hero__kpi-value${stockMateriaPrima.items > 0 ? ' bakery-hero__kpi-value--err' : ''}`}>
                  {stockMateriaPrima.items}
                </span>
                <span className="bakery-hero__kpi-label">Mat. prima crítica</span>
              </div>
            </>
          )}
        </div>
      </div>
      {hasActions && (
      <div className="bakery-hero__actions">
        {showSalesAction && (
          <button className="btn btn--primary" onClick={onNuevoPedido}>
            🎂 Nuevo pedido
          </button>
        )}
        {showProductionAction && (
          <button className="btn" onClick={onNuevaProduccion}>
            + Nueva producción
          </button>
        )}
        {showPosAction && (
          <a className="btn" href={`${prefix}/pos`}>Abrir POS</a>
        )}
        {showProductionAction && (
          <a className="btn" href={`${prefix}/manufacturing/recetas`}>Ver recetas</a>
        )}
      </div>
      )}
    </div>
  )
}

// ─── BakeryUrgentBar ──────────────────────────────────────────────────────────

interface BakeryUrgentBarProps {
  hornadasPendientes: number
  stockVenta: StockAlertGroup
  stockMateriaPrima: StockAlertGroup
  stockUrgencia?: string
  ingredientesCaducar: number
  ingredientesItems: string[]
  pedidosPendientesCobro: number
  pedidosPendientesEntrega: number
}

const BakeryUrgentBar: React.FC<BakeryUrgentBarProps> = ({
  hornadasPendientes, stockVenta, stockMateriaPrima, stockUrgencia,
  ingredientesCaducar, ingredientesItems,
  pedidosPendientesCobro, pedidosPendientesEntrega,
}) => {
  if (!hornadasPendientes && !stockVenta.items && !stockMateriaPrima.items && !ingredientesCaducar && !pedidosPendientesCobro && !pedidosPendientesEntrega) return null
  return (
    <div className="bakery-urgent">
      <span className="bakery-urgent__title">⚡ Urgente ahora</span>
      {pedidosPendientesCobro > 0 && (
        <span className="bakery-urgent__badge bakery-urgent__badge--warn">
          💵 {pedidosPendientesCobro} pedido{pedidosPendientesCobro !== 1 ? 's' : ''} pdt. de cobro
        </span>
      )}
      {pedidosPendientesEntrega > 0 && (
        <span className="bakery-urgent__badge bakery-urgent__badge--info">
          🚚 {pedidosPendientesEntrega} pedido{pedidosPendientesEntrega !== 1 ? 's' : ''} pdt. de entregar
        </span>
      )}
      {hornadasPendientes > 0 && (
        <span className="bakery-urgent__badge bakery-urgent__badge--warn">
          🔥 {hornadasPendientes} hornada{hornadasPendientes !== 1 ? 's' : ''} pendiente{hornadasPendientes !== 1 ? 's' : ''}
        </span>
      )}
      {stockVenta.items > 0 && (
        <span className="bakery-urgent__badge bakery-urgent__badge--err" title={stockVenta.nombres.join(', ')}>
          📦 {stockVenta.items} producto{stockVenta.items !== 1 ? 's' : ''} de venta sin stock
          {stockUrgencia === 'alta' ? ' · crítico' : ''}
        </span>
      )}
      {stockMateriaPrima.items > 0 && (
        <span className="bakery-urgent__badge bakery-urgent__badge--err" title={stockMateriaPrima.nombres.join(', ')}>
          🧂 {stockMateriaPrima.items} materia{stockMateriaPrima.items !== 1 ? 's primas' : ' prima'} en crítico
          {stockUrgencia === 'alta' ? ' · crítico' : ''}
        </span>
      )}
      {ingredientesCaducar > 0 && (
        <span className="bakery-urgent__badge bakery-urgent__badge--warn" title={ingredientesItems.join(', ')}>
          ⏰ {ingredientesCaducar} ingrediente{ingredientesCaducar !== 1 ? 's' : ''} por caducar
        </span>
      )}
    </div>
  )
}

// ─── BakerySalesViz ───────────────────────────────────────────────────────────

const BakerySalesViz: React.FC<{
  hoy: number; ayer: number; variacion?: number; loading: boolean; currency?: string
}> = ({ hoy, ayer, variacion, loading, currency }) => {
  if (loading) {
    return (
      <div className="bakery-compare bakery-compare--loading">
        <div className="bakery-compare__skeleton" />
        <div className="bakery-compare__skeleton bakery-compare__skeleton--short" />
      </div>
    )
  }
  if (!hoy && !ayer) {
    return (
      <div className="bakery-sales-empty">
        <div className="bakery-sales-empty__icon">📊</div>
        <p>Los datos se acumulan durante el turno activo</p>
        <span>Abre el POS para empezar a registrar ventas</span>
      </div>
    )
  }
  const max = Math.max(hoy, ayer, 1)
  const todayPct = Math.round((hoy / max) * 100)
  const yestPct  = Math.round((ayer / max) * 100)
  const positive  = (variacion ?? 0) >= 0
  return (
    <div className="bakery-compare">
      <div className="bakery-compare__row">
        <span className="bakery-compare__label">Hoy</span>
        <div className="bakery-compare__track">
          <div className="bakery-compare__fill bakery-compare__fill--today" style={{ width: `${todayPct}%` }} />
        </div>
        <span className="bakery-compare__val">{formatDashboardMoney(hoy, currency)}</span>
      </div>
      <div className="bakery-compare__row">
        <span className="bakery-compare__label">Ayer</span>
        <div className="bakery-compare__track">
          <div className="bakery-compare__fill" style={{ width: `${yestPct}%` }} />
        </div>
        <span className="bakery-compare__val bakery-compare__val--muted">{formatDashboardMoney(ayer, currency)}</span>
      </div>
      <div className="bakery-compare__footer">
        <span className={positive ? 'bakery-compare__delta--up' : 'bakery-compare__delta--down'}>
          {positive ? '↑' : '↓'} {Math.abs(variacion ?? 0).toFixed(1)}% vs ayer
        </span>
      </div>
    </div>
  )
}

// ─── QuickProductionModal ─────────────────────────────────────────────────────

interface QuickProductionModalProps {
  saving: boolean
  loading: boolean
  error: string | null
  recipes: Recipe[]
  selectedRecipeId: string
  selectedRecipe: Recipe | null
  recipeIngredients: RecipeIngredientResponse[]
  qtyMode: 'same' | 'other' | 'ingrediente'
  otherQty: string
  effectiveQty: number
  selectedIngredientId: string
  selectedIngredient: RecipeIngredientResponse | null
  ingredientAmount: string
  ingredientInputUnit: string
  ingredientStock: number | null
  stockLoading: boolean
  quickCalculation: ProductionCalculation | null
  calcLoading: boolean
  quickMaterialsTotal: number
  quickIndirectTotal: number
  quickEstimatedTotal: number
  quickUnitEstimated: number
  advancedOpen: boolean
  costLines: QuickCostDraft[]
  drivers: CostDriver[]
  wasteQty: string
  notes: string
  onSelectRecipe: (id: string) => void
  onQtyMode: (m: 'same' | 'other' | 'ingrediente') => void
  onOtherQty: (v: string) => void
  onSelectIngredient: (id: string, ing: RecipeIngredientResponse | null) => void
  onIngredientAmount: (v: string) => void
  onIngredientUnit: (u: string) => void
  onUseAllStock: () => void
  onToggleAdvanced: () => void
  onUpdateCostLine: (key: string, patch: Partial<QuickCostDraft>) => void
  onAddCostLine: () => void
  onRemoveCostLine: (key: string) => void
  onWasteQty: (v: string) => void
  onNotes: (v: string) => void
  onClose: () => void
  onSubmit: () => void
}

const QuickProductionModal: React.FC<QuickProductionModalProps> = (p) => {
  const { t } = useTranslation(['dashboard', 'common'])

  const stockInsufficient = (() => {
    if (p.qtyMode !== 'ingrediente' || p.ingredientStock === null || !p.selectedIngredient) return false
    const inputG = isWeightUnit(p.selectedIngredient.unit)
      ? convertToGrams(Number(p.ingredientAmount || 0), p.ingredientInputUnit)
      : Number(p.ingredientAmount || 0)
    const stockG = isWeightUnit(p.selectedIngredient.unit)
      ? convertToGrams(p.ingredientStock, p.selectedIngredient.unit)
      : p.ingredientStock
    return inputG > stockG && inputG > 0
  })()

  return (
    <div
      className="qp-overlay"
      onMouseDown={(e) => { if (e.target === e.currentTarget && !p.saving) p.onClose() }}
    >
      <div className="qp-panel">
        <div className="qp-panel__header">
          <h3 className="qp-panel__title">{t('dashboard:panaderia.quickProduction')}</h3>
          <p className="qp-panel__desc">{t('dashboard:panaderia.quickProductionDesc')}</p>
        </div>

        {p.loading ? (
          <div className="qp-panel__body">
            <p className="qp-empty-msg">{t('dashboard:panaderia.loadingRecipes')}</p>
          </div>
        ) : (
          <>
            <div className="qp-panel__body">

              {/* 1 — Receta */}
              <div className="qp-section">
                <div className="qp-section-title">Receta</div>
                <div className="qp-recipe-grid">
                  <div className="qp-field">
                    <label>{t('dashboard:panaderia.recipe')}</label>
                    <select
                      className="qp-select"
                      value={p.selectedRecipeId}
                      onChange={(e) => p.onSelectRecipe(e.target.value)}
                      disabled={p.saving}
                    >
                      {p.recipes.length === 0 && <option value="">{t('dashboard:panaderia.noRecipes')}</option>}
                      {p.recipes.map((r) => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="qp-recipe-info">
                    <div className="qp-recipe-info__tag">{t('dashboard:panaderia.product')}</div>
                    <div className="qp-recipe-info__name">{p.selectedRecipe?.name || '—'}</div>
                    <div className="qp-recipe-info__yield">
                      {t('dashboard:panaderia.baseYield')} <strong>{toNumber(p.selectedRecipe?.yield_qty).toFixed(0)} uds</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* 2 — Cantidad */}
              <div className="qp-section">
                <div className="qp-section-title">Cantidad a producir</div>
                <div className="qp-qty-options">
                  {(['same', 'other', 'ingrediente'] as const).map((mode) => (
                    <label
                      key={mode}
                      className={`qp-qty-opt${p.qtyMode === mode ? ' qp-qty-opt--active' : ''}`}
                    >
                      <input
                        type="radio"
                        checked={p.qtyMode === mode}
                        onChange={() => p.onQtyMode(mode)}
                        disabled={p.saving}
                        style={{ display: 'none' }}
                      />
                      {mode === 'same'        && `${t('dashboard:panaderia.sameQuantity')} (${p.selectedRecipe?.yield_qty || 0})`}
                      {mode === 'other'       && t('dashboard:panaderia.otherQuantity')}
                      {mode === 'ingrediente' && t('dashboard:panaderia.byIngredient')}
                    </label>
                  ))}
                </div>

                {p.qtyMode === 'other' && (
                  <div className="qp-field">
                    <label>Unidades a producir</label>
                    <input
                      type="number" min={0.01} step={0.01}
                      className="qp-input"
                      value={p.otherQty}
                      onChange={(e) => p.onOtherQty(e.target.value)}
                      disabled={p.saving}
                      placeholder="Ej: 50"
                    />
                  </div>
                )}

                {p.qtyMode === 'ingrediente' && (
                  <div className="qp-ingredient-block">
                    {p.recipeIngredients.length === 0 ? (
                      <p className="qp-empty-msg">{t('dashboard:panaderia.loadingIngredients')}</p>
                    ) : (
                      <>
                        <div className="qp-field">
                          <label>{t('dashboard:panaderia.baseIngredient')}</label>
                          <select
                            className="qp-select"
                            value={p.selectedIngredientId}
                            onChange={(e) => {
                              const ing = p.recipeIngredients.find((i) => i.id === e.target.value) || null
                              p.onSelectIngredient(e.target.value, ing)
                            }}
                            disabled={p.saving}
                          >
                            {p.recipeIngredients.map((ing) => (
                              <option key={ing.id} value={ing.id}>
                                {ing.product_name || ing.product_id} — {ing.qty} {ing.unit}
                                {isWeightUnit(ing.unit) ? ` (${(convertToGrams(ing.qty, ing.unit) / 453.592).toFixed(2)} lb)` : ''}
                              </option>
                            ))}
                          </select>
                        </div>

                        {p.selectedIngredient && (
                          <div className="qp-field">
                            <label>{t('dashboard:panaderia.availableQty')}</label>
                            <div className="qp-unit-row">
                              <input
                                type="number" min={0.01} step={0.01}
                                className="qp-input"
                                value={p.ingredientAmount}
                                onChange={(e) => p.onIngredientAmount(e.target.value)}
                                disabled={p.saving}
                                placeholder="Ej: 10"
                              />
                              {isWeightUnit(p.selectedIngredient.unit) ? (
                                <select
                                  className="qp-unit-select"
                                  value={p.ingredientInputUnit}
                                  onChange={(e) => p.onIngredientUnit(e.target.value)}
                                  disabled={p.saving}
                                >
                                  <option value="lb">lb</option>
                                  <option value="kg">kg</option>
                                  <option value="g">g</option>
                                </select>
                              ) : (
                                <span className="qp-unit-badge">{p.selectedIngredient.unit}</span>
                              )}
                            </div>
                            <div className="qp-ing-meta">
                              <span className="qp-ing-formula">
                                Receta usa <strong>{p.selectedIngredient.qty} {p.selectedIngredient.unit}</strong> → {p.selectedRecipe?.yield_qty || 0} uds
                              </span>
                              {p.stockLoading ? (
                                <span className="qp-cost-sub">Verificando stock…</span>
                              ) : p.ingredientStock !== null && (
                                <div className="qp-stock-row">
                                  <span className={p.ingredientStock < toNumber(p.selectedIngredient.qty) ? 'qp-stock-low' : 'qp-stock-ok'}>
                                    Stock: {p.ingredientStock.toFixed(2)} {p.selectedIngredient.unit}
                                  </span>
                                  <button type="button" className="link" onClick={p.onUseAllStock} disabled={p.saving} style={{ fontSize: 12 }}>
                                    {t('dashboard:panaderia.useAll')}
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* 3 — Resumen de costos */}
              <div className="qp-section">
                <div className="qp-section-title">Resumen de costos</div>
                <div className="qp-cost-grid">
                  <div className="qp-cost-cell">
                    <span className="qp-cost-label">{t('dashboard:panaderia.finalQuantity')}</span>
                    <span className="qp-cost-value">{p.effectiveQty || 0}</span>
                    <span className="qp-cost-sub">uds</span>
                  </div>
                  <div className="qp-cost-cell">
                    <span className="qp-cost-label">{t('dashboard:panaderia.materials')}</span>
                    <span className="qp-cost-value">{formatMoney(p.quickMaterialsTotal)}</span>
                    <span className="qp-cost-sub">{p.calcLoading ? 'Calculando…' : t('dashboard:panaderia.perRecipe')}</span>
                  </div>
                  <div className="qp-cost-cell">
                    <span className="qp-cost-label">Indirectos</span>
                    <span className="qp-cost-value">{formatMoney(p.quickIndirectTotal)}</span>
                    <span className="qp-cost-sub">{t('dashboard:panaderia.editable')}</span>
                  </div>
                  <div className="qp-cost-cell qp-cost-cell--primary">
                    <span className="qp-cost-label">{t('dashboard:panaderia.estimatedCostPerUnit')}</span>
                    <span className="qp-cost-value">{formatMoney(p.quickUnitEstimated)}</span>
                    <span className="qp-cost-sub">{formatMoney(p.quickEstimatedTotal)} total</span>
                  </div>
                </div>
              </div>

              {stockInsufficient && (
                <div className="qp-stock-warn">
                  {t('dashboard:panaderia.stockWarning', {
                    available: `${p.ingredientStock?.toFixed(2)} ${p.selectedIngredient?.unit}`,
                  })}
                </div>
              )}

              {/* 4 — Merma */}
              <div className="qp-section">
                <div className="qp-section-title">Merma estimada</div>
                <div className="qp-waste-row">
                  <label>{t('dashboard:panaderia.wasteUnits')}</label>
                  <input
                    type="number" min={0} step={1}
                    className="qp-waste-input"
                    value={p.wasteQty}
                    onChange={(e) => p.onWasteQty(e.target.value)}
                    disabled={p.saving}
                    placeholder="0"
                  />
                  <span className="qp-waste-desc">{t('dashboard:panaderia.wasteDesc')}</span>
                </div>
              </div>

              {/* 5 — Toggle avanzado */}
              <div className="qp-info-strip">
                <span className="qp-info-strip__text">
                  {p.quickCalculation?.tiempo_estimado
                    ? `${t('dashboard:panaderia.estimatedTime')} ${toNumber(p.quickCalculation.tiempo_estimado.tiempo_total_horas).toFixed(1)} h`
                    : t('dashboard:panaderia.autoCompleteDesc')}
                </span>
                <button type="button" className="link" onClick={p.onToggleAdvanced} disabled={p.saving}>
                  {p.advancedOpen ? t('dashboard:panaderia.hideSettings') : t('dashboard:panaderia.showSettings')}
                </button>
              </div>

              {/* 6 — Avanzado: materiales + costos indirectos + notas */}
              {p.advancedOpen && (
                <>
                  <div className="qp-adv-block">
                    <div className="qp-adv-header">
                      <div className="qp-adv-header__title">{t('dashboard:panaderia.materialsToConsume')}</div>
                    </div>
                    <div className="qp-adv-body">
                      {p.calcLoading ? (
                        <p className="qp-empty-msg" style={{ padding: 14 }}>{t('dashboard:panaderia.calculatingMaterials')}</p>
                      ) : p.quickCalculation?.ingredientes?.length ? (
                        p.quickCalculation.ingredientes.map((item, idx) => (
                          <div key={`${item.producto_id}-${idx}`} className="qp-mat-row">
                            <div>
                              <div className="qp-mat-name">{item.producto}</div>
                              <div className="qp-mat-detail">{item.presentacion_compra}</div>
                            </div>
                            <div className="qp-mat-qty">{toNumber(item.qty_necesaria).toFixed(2)} {item.unidad}</div>
                            <div className="qp-mat-cost">{formatMoney(item.costo_estimado)}</div>
                          </div>
                        ))
                      ) : (
                        <p className="qp-empty-msg" style={{ padding: 14 }}>{t('dashboard:panaderia.selectRecipeAndQty')}</p>
                      )}
                    </div>
                  </div>

                  <div className="qp-adv-block">
                    <div className="qp-adv-header">
                      <div>
                        <div className="qp-adv-header__title">Gastos indirectos</div>
                        <div className="qp-adv-header__sub">Mano de obra, energía u otros cargos</div>
                      </div>
                      <button
                        type="button" className="link"
                        onClick={p.onAddCostLine}
                        disabled={p.saving || p.drivers.length === 0}
                      >
                        + Añadir
                      </button>
                    </div>
                    <div className="qp-adv-body--padded">
                      {p.costLines.length === 0 ? (
                        <p className="qp-empty-msg">
                          {p.drivers.length === 0 ? t('dashboard:panaderia.noCostDrivers') : t('dashboard:panaderia.noIndirectCosts')}
                        </p>
                      ) : (
                        p.costLines.map((line) => (
                          <div key={line.key} className="qp-cost-row">
                            <select
                              className="qp-select"
                              value={line.driver_id}
                              onChange={(e) => p.onUpdateCostLine(line.key, { driver_id: e.target.value })}
                              disabled={p.saving}
                            >
                              <option value="">Seleccionar gasto</option>
                              {p.drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                            </select>
                            <input type="number" min={0} step={0.0001} className="qp-input"
                              value={line.qty_actual} placeholder="Cant."
                              onChange={(e) => p.onUpdateCostLine(line.key, { qty_actual: e.target.value })}
                              disabled={p.saving} />
                            <input type="number" min={1} step={1} className="qp-input"
                              value={line.headcount_actual} placeholder="Pers."
                              onChange={(e) => p.onUpdateCostLine(line.key, { headcount_actual: e.target.value })}
                              disabled={p.saving} />
                            <input type="number" min={0} step={0.0001} className="qp-input"
                              value={line.rate_applied} placeholder="Tarifa"
                              onChange={(e) => p.onUpdateCostLine(line.key, { rate_applied: e.target.value })}
                              disabled={p.saving} />
                            <button type="button" className="link" onClick={() => p.onRemoveCostLine(line.key)} disabled={p.saving}>✕</button>
                            <input type="text" className="qp-input qp-cost-row__notes"
                              value={line.notes} placeholder="Notas del gasto"
                              onChange={(e) => p.onUpdateCostLine(line.key, { notes: e.target.value })}
                              disabled={p.saving} />
                            <div className="qp-cost-row__total">
                              {formatMoney(toNumber(line.qty_actual) * Math.max(toNumber(line.headcount_actual), 1) * toNumber(line.rate_applied))}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="qp-section">
                    <div className="qp-section-title">Notas</div>
                    <textarea
                      className="qp-textarea"
                      value={p.notes}
                      onChange={(e) => p.onNotes(e.target.value)}
                      disabled={p.saving}
                      rows={3}
                      placeholder="Observaciones para esta producción"
                    />
                  </div>
                </>
              )}
            </div>

            {/* Footer fijo */}
            <div className="qp-panel__footer">
              <span className={p.error ? 'qp-panel__footer-err' : 'qp-panel__footer-info'}>
                {p.error
                  ? p.error
                  : p.effectiveQty > 0
                    ? `Listo para producir ${p.effectiveQty} uds`
                    : 'Selecciona receta y cantidad'}
              </span>
              <div className="qp-panel__footer-actions">
                <button type="button" className="btn" onClick={p.onClose} disabled={p.saving}>
                  Cancelar
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={p.onSubmit}
                  disabled={p.saving || !p.effectiveQty || p.effectiveQty <= 0}
                >
                  {p.saving ? 'Procesando…' : 'Producir ahora'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─── PanaderiaDashboard ───────────────────────────────────────────────────────

const PanaderiaDashboard: React.FC = () => {
  const { empresa } = useParams<{ empresa?: string }>()
  const { t } = useTranslation(['dashboard', 'common'])
  const { modules } = useMisModulos()

  const shouldLoadKPIs = modules.some((m) =>
    ['sales', 'pos', 'produccion', 'inventario'].includes((m.slug || '').toLowerCase())
  )
  const { data: kpisData, loading: kpisLoading } = usePanaderiaKPIs({ enabled: shouldLoadKPIs })

  const kpis         = (kpisData || {}) as KPIData
  const ventas       = kpis.ventas_mostrador || {}
  const stock        = kpis.stock_critico || {}
  const mermas       = kpis.mermas || {}
  const produccion   = kpis.produccion || {}
  const ingredientes = kpis.ingredientes_caducar || {}
  const topProductos = kpis.top_productos || []
  const pedidos      = kpis.pedidos || {}
  const stockNombres = Array.isArray(stock.nombres) ? stock.nombres || [] : []
  const hasSplitStock = Boolean(stock.productos_venta || stock.materias_primas)
  const stockVenta: StockAlertGroup = {
    items: hasSplitStock ? toNumber(stock.productos_venta?.items) : toNumber(stock.items),
    nombres: hasSplitStock
      ? (Array.isArray(stock.productos_venta?.nombres) ? stock.productos_venta?.nombres || [] : [])
      : stockNombres,
  }
  const stockMateriaPrima: StockAlertGroup = {
    items: toNumber(stock.materias_primas?.items),
    nombres: Array.isArray(stock.materias_primas?.nombres) ? stock.materias_primas?.nombres || [] : [],
  }
  const stockItemsTotal = stockVenta.items + stockMateriaPrima.items

  const hornadasPendientes = Math.max(
    (produccion.hornadas_programadas || 0) - (produccion.hornadas_completadas || 0),
    0
  ) + (produccion.pedidos_con_receta || 0)

  // ── Quick order state ──────────────────────────────────
  const [orderOpen, setOrderOpen]               = useState(false)
  const [orderSaving, setOrderSaving]           = useState(false)
  const [orderError, setOrderError]             = useState<string | null>(null)
  const [orderLineas, setOrderLineas]           = useState<VentaLinea[]>([])
  const [orderClienteId, setOrderClienteId]     = useState<string | undefined>(undefined)
  const [orderClienteName, setOrderClienteName] = useState('')
  const [orderDeliveryDate, setOrderDeliveryDate] = useState('')
  const [orderNotes, setOrderNotes]             = useState('')
  const [orderDeposit, setOrderDeposit]         = useState(0)
  const [orderDepositPaid, setOrderDepositPaid] = useState(false)
  const [orderPaymentMethod, setOrderPaymentMethod] = useState('')
  const [orderShowPicker, setOrderShowPicker]   = useState(false)
  const [orderYaCobrado, setOrderYaCobrado]     = useState(false)

  const openQuickOrder = () => {
    setOrderLineas([])
    setOrderClienteId(undefined)
    setOrderClienteName('')
    setOrderDeliveryDate('')
    setOrderNotes('')
    setOrderDeposit(0)
    setOrderDepositPaid(false)
    setOrderPaymentMethod('')
    setOrderShowPicker(false)
    setOrderYaCobrado(false)
    setOrderError(null)
    setOrderOpen(true)
  }

  const handleSaveOrder = async () => {
    if (!orderDeliveryDate) { setOrderError('La fecha de entrega es obligatoria'); return }
    if (orderLineas.length === 0) { setOrderError('Agrega al menos un producto'); return }
    setOrderSaving(true)
    setOrderError(null)
    try {
      const venta = await createVenta({
        fecha: new Date().toISOString().slice(0, 10),
        cliente_id: orderClienteId,
        estado: 'borrador',
        notas: orderNotes || undefined,
        lineas: orderLineas,
        delivery_date: orderDeliveryDate,
        deposit_amount: orderYaCobrado ? 0 : orderDeposit,
        deposit_paid: orderYaCobrado ? false : orderDepositPaid,
        payment_method: orderPaymentMethod || undefined,
      } as any)
      if (orderYaCobrado) {
        await checkoutOrder(String(venta.id), { payment_method: orderPaymentMethod || undefined })
        setQuickSuccess(`✓ Pedido cobrado y facturado — entrega el ${orderDeliveryDate}`)
      } else {
        setQuickSuccess(`✓ Pedido registrado para el ${orderDeliveryDate}`)
      }
      setOrderOpen(false)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setOrderError(typeof detail === 'string' ? detail : (e?.message || 'Error al guardar'))
    } finally {
      setOrderSaving(false)
    }
  }

  // ── Quick production state (unchanged) ────────────────
  const [quickOpen, setQuickOpen]               = useState(false)
  const [quickLoading, setQuickLoading]         = useState(false)
  const [quickSaving, setQuickSaving]           = useState(false)
  const [quickError, setQuickError]             = useState<string | null>(null)
  const [quickSuccess, setQuickSuccess]         = useState<string | null>(null)
  const [recipes, setRecipes]                   = useState<Recipe[]>([])
  const [selectedRecipeId, setSelectedRecipeId] = useState('')
  const [qtyMode, setQtyMode]                   = useState<'same' | 'other' | 'ingrediente'>('same')
  const [otherQty, setOtherQty]                 = useState<string>('')
  const [recipeDetail, setRecipeDetail]         = useState<Recipe | null>(null)
  const [selectedIngredientId, setSelectedIngredientId] = useState('')
  const [ingredientAmount, setIngredientAmount] = useState('')
  const [ingredientInputUnit, setIngredientInputUnit]   = useState('lb')
  const [quickNotes, setQuickNotes]             = useState('')
  const [quickCalculation, setQuickCalculation] = useState<ProductionCalculation | null>(null)
  const [quickCalcLoading, setQuickCalcLoading] = useState(false)
  const [quickFullCost, setQuickFullCost]       = useState<FullCostSummary | null>(null)
  const [quickDrivers, setQuickDrivers]         = useState<CostDriver[]>([])
  const [quickCostLines, setQuickCostLines]     = useState<QuickCostDraft[]>([])
  const [quickAdvancedOpen, setQuickAdvancedOpen] = useState(false)
  const [ingredientStock, setIngredientStock]   = useState<number | null>(null)
  const [stockLoading, setStockLoading]         = useState(false)
  const [quickWasteQty, setQuickWasteQty]       = useState<string>('0')

  const isModuleEnabled = (moduleName: string) =>
    modules.some(
      (m) =>
        (m.slug || '').toLowerCase() === moduleName.toLowerCase() ||
        (m.name || '').toLowerCase().includes(moduleName.toLowerCase())
    )

  const isProductionEnabled = () =>
    modules.some((m) => {
      const slug = (m.slug || '').toLowerCase()
      const name = (m.name || '').toLowerCase()
      return (
        slug === 'produccion' || slug === 'production' || slug === 'productions' || slug === 'manufacturing' ||
        name.includes('produccion') || name.includes('production') || name.includes('manufacturing')
      )
    })

  const prefix      = empresa ? `/${empresa}` : ''
  const customLinks: Array<{ label: string; href: string; icon: string }> = []
  const hasOperationalKpis = isModuleEnabled('sales') || isModuleEnabled('inventory') || isProductionEnabled()
  const useFocusedEmployeeWorkspace = modules.length > 1 && modules.length <= 4 && !hasOperationalKpis

  // ── Effects (all unchanged) ────────────────────────────

  useEffect(() => {
    if (!quickOpen) return
    let cancelled = false
    ;(async () => {
      try {
        setQuickLoading(true)
        setQuickError(null)
        const [data, drivers] = await Promise.all([
          listRecipes({ limit: 500, activo: true }),
          listCostDrivers().catch(() => []),
        ])
        if (cancelled) return
        const list = Array.isArray(data) ? data : []
        setRecipes(list)
        setQuickDrivers(Array.isArray(drivers) ? drivers.filter((d) => d.is_active !== false) : [])
        if (!selectedRecipeId && list.length > 0) {
          setSelectedRecipeId(list[0].id)
          setOtherQty(String(Number(list[0].yield_qty || 1)))
        }
      } catch (e: any) {
        if (!cancelled) setQuickError(getQuickErrorMessage(e) || t('dashboard:panaderia.recipesLoadError'))
      } finally {
        if (!cancelled) setQuickLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [quickOpen])

  useEffect(() => {
    if (!selectedRecipeId || !quickOpen) return
    let cancelled = false
    ;(async () => {
      try {
        const [detail, fullCost] = await Promise.all([
          getRecipe(selectedRecipeId),
          getRecipeFullCost(selectedRecipeId).catch(() => null),
        ])
        if (cancelled) return
        setRecipeDetail(detail)
        setQuickFullCost(fullCost)
        const ings = detail.ingredients || []
        if (ings.length > 0) setSelectedIngredientId(ings[0].id)
      } catch (e: any) {
        if (!cancelled) setQuickError(getQuickErrorMessage(e))
      }
    })()
    return () => { cancelled = true }
  }, [selectedRecipeId, quickOpen])

  useEffect(() => {
    if (!quickOpen || qtyMode !== 'ingrediente' || !selectedIngredientId) {
      setIngredientStock(null)
      return
    }
    const ing = (recipeDetail?.ingredients || []).find((i) => i.id === selectedIngredientId)
    if (!ing) return
    let cancelled = false
    setStockLoading(true)
    listStockItems({ product_id: ing.product_id })
      .then((items) => { if (!cancelled) setIngredientStock(items.reduce((s, i) => s + i.qty, 0)) })
      .catch(() => { if (!cancelled) setIngredientStock(null) })
      .finally(() => { if (!cancelled) setStockLoading(false) })
    return () => { cancelled = true }
  }, [selectedIngredientId, qtyMode, quickOpen, recipeDetail])

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
        ratio = convertToGrams(inputAmount, ingredientInputUnit) / convertToGrams(selectedIngredient.qty, selectedIngredient.unit)
      } else {
        ratio = inputAmount / selectedIngredient.qty
      }
      return Math.floor(Math.round(ratio * (selectedRecipe.yield_qty || 0) * 1e6) / 1e6)
    }
    return 0
  }, [selectedRecipe, qtyMode, otherQty, selectedIngredient, ingredientAmount, ingredientInputUnit])

  useEffect(() => {
    if (!quickOpen || !selectedRecipeId || !effectiveQty || effectiveQty <= 0) {
      setQuickCalculation(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        setQuickCalcLoading(true)
        const calc = await calculateProduction(selectedRecipeId, effectiveQty, 1)
        if (!cancelled) setQuickCalculation(calc)
      } catch (e: any) {
        if (!cancelled) setQuickError(getQuickErrorMessage(e))
      } finally {
        if (!cancelled) setQuickCalcLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [quickOpen, selectedRecipeId, effectiveQty])

  useEffect(() => {
    if (!quickOpen) return
    setQuickCostLines(buildQuickCostLines(quickFullCost, effectiveQty, toNumber(selectedRecipe?.yield_qty || 0)))
  }, [quickOpen, quickFullCost, effectiveQty, selectedRecipe])

  const quickIndirectTotal = useMemo(
    () => quickCostLines.reduce((sum, l) =>
      sum + toNumber(l.qty_actual) * Math.max(toNumber(l.headcount_actual), 1) * toNumber(l.rate_applied), 0),
    [quickCostLines]
  )
  const quickMaterialsTotal  = useMemo(() => toNumber(quickCalculation?.costo_total_produccion), [quickCalculation])
  const quickEstimatedTotal  = quickMaterialsTotal + quickIndirectTotal
  const quickUnitEstimated   = effectiveQty > 0 ? quickEstimatedTotal / effectiveQty : 0

  // ── Handlers ──────────────────────────────────────────

  const openQuickProduction = () => {
    setQuickSuccess(null)
    setQuickError(null)
    setQuickNotes('')
    setQuickCalculation(null)
    setQuickFullCost(null)
    setQuickCostLines([])
    setQuickAdvancedOpen(false)
    setQuickWasteQty('0')
    setIngredientStock(null)
    setQuickOpen(true)
  }

  const handleSelectRecipe = (rid: string) => {
    setSelectedRecipeId(rid)
    const rec = recipes.find((r) => r.id === rid)
    if (rec) setOtherQty(String(Number(rec.yield_qty || 1)))
  }

  const handleSelectIngredient = (id: string, ing: RecipeIngredientResponse | null) => {
    setSelectedIngredientId(id)
    setIngredientAmount('')
    if (ing && isWeightUnit(ing.unit)) setIngredientInputUnit('lb')
    else if (ing) setIngredientInputUnit(ing.unit)
  }

  const handleUseAllStock = () => {
    if (ingredientStock === null || !selectedIngredient) return
    if (isWeightUnit(selectedIngredient.unit) && isWeightUnit(ingredientInputUnit)) {
      setIngredientAmount(convertFromGrams(convertToGrams(ingredientStock, selectedIngredient.unit), ingredientInputUnit).toFixed(2))
    } else {
      setIngredientAmount(String(ingredientStock))
    }
  }

  const updateQuickCostLine = (key: string, patch: Partial<QuickCostDraft>) =>
    setQuickCostLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const handleQuickProduction = async () => {
    if (!selectedRecipe) { setQuickError(t('dashboard:panaderia.selectRecipe')); return }
    if (!effectiveQty || effectiveQty <= 0) { setQuickError(t('dashboard:panaderia.quantityGtZero')); return }
    try {
      setQuickSaving(true)
      setQuickError(null)
      setQuickSuccess(null)
      const whs = await listWarehouses().catch(() => [])
      const wh  = Array.isArray(whs) ? (whs.find((w) => w.is_active) || whs[0]) : null
      const order = await createProductionOrder({
        recipe_id: selectedRecipe.id,
        product_id: selectedRecipe.product_id,
        warehouse_id: wh ? String(wh.id) : undefined,
        qty_planned: effectiveQty,
        scheduled_date: new Date().toISOString(),
        status: 'draft',
        notes: quickNotes || undefined,
      } as any)
      const normalizedCosts: ProductionOrderCostInput[] = quickCostLines
        .map((l) => ({
          driver_id: String(l.driver_id || '').trim(),
          qty_actual: toNumber(l.qty_actual),
          headcount_actual: Math.max(toNumber(l.headcount_actual) || 1, 1),
          rate_applied: toNumber(l.rate_applied),
          notes: l.notes?.trim() || undefined,
        }))
        .filter((l) => l.driver_id && (l.qty_actual > 0 || l.rate_applied > 0))
      if (quickAdvancedOpen && normalizedCosts.length > 0) {
        try { await replaceProductionOrderCosts(order.id, normalizedCosts) } catch { /* non-blocking */ }
      }
      await startProductionOrder(order.id)
      await completeProductionOrder(order.id, { qty_produced: effectiveQty, waste_qty: Math.max(toNumber(quickWasteQty), 0) })
      setQuickSuccess(`✓ ${effectiveQty} uds producidas · costo estimado ${formatMoney(quickEstimatedTotal)}`)
      setQuickOpen(false)
    } catch (e: any) {
      setQuickError(getQuickErrorMessage(e) || t('dashboard:panaderia.quickProductionError'))
    } finally {
      setQuickSaving(false)
    }
  }

  // ── Render ─────────────────────────────────────────────

  return (
    <DashboardPro
      sectorName={t('dashboard:panaderia.sectorName')}
      sectorIcon="🍞"
      customLinks={customLinks}
      hideSidebar={useFocusedEmployeeWorkspace}
    >

      {/* Onboarding: solo customers habilitado */}
      {modules.length === 1 && isModuleEnabled('customers') && (
        <section className="card full-width bakery-welcome">
          <h2>{t('dashboard:panaderia.welcomeTitle')}</h2>
          <p>{t('dashboard:panaderia.welcomeDesc')}</p>
          <a href={`${prefix}/customers`} className="btn btn--primary">
            {t('dashboard:panaderia.goToCustomers')}
          </a>
        </section>
      )}

      {/* Hero command bar */}
      <BakeryHero
        ventas={ventas}
        hornadasPendientes={hornadasPendientes}
        stockVenta={stockVenta}
        stockMateriaPrima={stockMateriaPrima}
        loading={kpisLoading}
        isModuleEnabled={isModuleEnabled}
        isProductionEnabled={isProductionEnabled}
        prefix={prefix}
        onNuevaProduccion={openQuickProduction}
        onNuevoPedido={openQuickOrder}
        hidePosShortcut={useFocusedEmployeeWorkspace}
      />

      {/* Toast de éxito post-producción */}
      {quickSuccess && (
        <div className="bakery-toast bakery-toast--ok">{quickSuccess}</div>
      )}

      {/* Urgencias activas */}
      <BakeryUrgentBar
        hornadasPendientes={hornadasPendientes}
        stockVenta={stockVenta}
        stockMateriaPrima={stockMateriaPrima}
        stockUrgencia={stock.urgencia}
        ingredientesCaducar={ingredientes.proximos_7_dias || 0}
        ingredientesItems={ingredientes.items || []}
        pedidosPendientesCobro={pedidos.pendientes_cobro || 0}
        pedidosPendientesEntrega={pedidos.pendientes_entrega || 0}
      />

      {useFocusedEmployeeWorkspace && (
        <BakeryEmployeeWorkspace modules={modules} prefix={prefix} />
      )}

      {!useFocusedEmployeeWorkspace && (
      <div className="dashboard-grid">

        {/* ── Fila 1: Producción + Ventas ── */}

        {isProductionEnabled() && (
          <section className="card col-6">
            <div className="card__header">
              <h3>{t('dashboard:panaderia.productionBatches')}</h3>
              {hornadasPendientes > 0 && (
                <span className="pill pill--warn">
                  {hornadasPendientes} pendiente{hornadasPendientes !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            <div className="progress-stat">
              <div className="progress-stat__header">
                <span>{produccion.hornadas_completadas || 0} de {produccion.hornadas_programadas || 0} hornadas</span>
                <span>{produccion.progreso?.toFixed(0) || 0}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar__fill" style={{ width: `${produccion.progreso || 0}%` }} />
              </div>
            </div>
            <div className="pills">
              <span className="pill pill--ok">✓ {produccion.hornadas_completadas || 0} hechas</span>
              {hornadasPendientes > 0 && (
                <span className="pill pill--warn">⏳ {hornadasPendientes} pendientes</span>
              )}
            </div>
            <div className="card__footer">
              <button className="btn btn--primary" onClick={openQuickProduction} style={{ width: '100%' }}>
                + Nueva hornada
              </button>
            </div>
          </section>
        )}

        {isModuleEnabled('sales') && (
          <section className="card col-6">
            <h3>{t('dashboard:panaderia.salesTodayCard')}</h3>
            <div className="kpi-grid">
              <div className="kpi">
                <span className="kpi__label">{t('dashboard:panaderia.today')}</span>
                <span className="kpi__value">
                  {kpisLoading ? '—' : formatDashboardMoney(ventas.hoy, ventas.moneda)}
                </span>
              </div>
              <div className="kpi">
                <span className="kpi__label">{t('dashboard:panaderia.yesterday')}</span>
                <span className="kpi__value">{formatDashboardMoney(ventas.ayer, ventas.moneda)}</span>
              </div>
              <div className="kpi">
                <span className="kpi__label">Variación</span>
                <span className={`kpi__value ${(ventas.variacion || 0) >= 0 ? 'positive' : 'negative'}`}>
                  {(ventas.variacion || 0) >= 0 ? '+' : ''}{ventas.variacion?.toFixed(1) || '0'}%
                </span>
              </div>
            </div>
          </section>
        )}

        {/* ── Fila 2: Stock crítico + Ingredientes + Mermas ── */}

        {isModuleEnabled('inventory') && (
          <section className="card col-4">
            <h3>{t('dashboard:panaderia.criticalStock')}</h3>
            <div className="stat-large">
              <span className="stat-large__value">{stockItemsTotal}</span>
              <span className="stat-large__label">Alertas totales</span>
            </div>
            {(stockVenta.items > 0 || stockMateriaPrima.items > 0) && (
              <div className="kpi-grid" style={{ marginTop: 12 }}>
                <div className="kpi">
                  <span className="kpi__label">Productos de venta</span>
                  <span className="kpi__value">{stockVenta.items}</span>
                </div>
                <div className="kpi">
                  <span className="kpi__label">Materias primas</span>
                  <span className="kpi__value">{stockMateriaPrima.items}</span>
                </div>
              </div>
            )}
            {stockVenta.nombres.length > 0 && (
              <ul className="list-compact" style={{ marginTop: 12 }}>
                {stockVenta.nombres.slice(0, 3).map((item, i) => <li key={`sale-${i}`}>Venta: {item}</li>)}
              </ul>
            )}
            {stockMateriaPrima.nombres.length > 0 && (
              <ul className="list-compact" style={{ marginTop: stockVenta.nombres.length > 0 ? 8 : 12 }}>
                {stockMateriaPrima.nombres.slice(0, 3).map((item, i) => <li key={`raw-${i}`}>Materia prima: {item}</li>)}
              </ul>
            )}
            {!stockItemsTotal && (
              <p className="empty-state" style={{ padding: 0 }}>Sin alertas de stock 👍</p>
            )}
          </section>
        )}

        {isModuleEnabled('inventory') && (
          <section className="card col-4">
            <h3>{t('dashboard:panaderia.expiringIngredients')}</h3>
            <div className="stat-large">
              <span className="stat-large__value">{ingredientes.proximos_7_dias || 0}</span>
              <span className="stat-large__label">{t('dashboard:panaderia.next7Days')}</span>
            </div>
            {ingredientes.items && ingredientes.items.length > 0 ? (
              <ul className="list-compact">
                {ingredientes.items.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : (
              <p className="empty-state" style={{ padding: 0 }}>Sin vencimientos próximos 👍</p>
            )}
          </section>
        )}

        {isModuleEnabled('inventory') && (
          <section className="card col-4">
            <h3>{t('dashboard:panaderia.wasteToday')}</h3>
            <div className="stat-large">
              <span className="stat-large__value">{mermas.hoy || 0}</span>
              <span className="stat-large__label">{mermas.unidad || t('dashboard:panaderia.units')}</span>
            </div>
            <div className="kpi">
              <span className="kpi__label">{t('dashboard:panaderia.estimatedValue')}</span>
              <span className="kpi__value">
                {formatDashboardMoney(mermas.valor_estimado, mermas.moneda || ventas.moneda)}
              </span>
            </div>
          </section>
        )}

        {/* ── Fila 3: Comparativa ventas + Top productos ── */}

        {isModuleEnabled('sales') && (
          <section className="card col-8">
            <div className="card__header">
              <h3>Ventas hoy vs ayer</h3>
              <span className="pill">En tiempo real</span>
            </div>
            <BakerySalesViz
              hoy={ventas.hoy || 0}
              ayer={ventas.ayer || 0}
              variacion={ventas.variacion}
              loading={kpisLoading}
              currency={ventas.moneda}
            />
          </section>
        )}

        {isModuleEnabled('sales') && (
          <section className="card col-4">
            <h3>{t('dashboard:panaderia.topProducts')}</h3>
            <div className="table-compact">
              {topProductos.length > 0 ? (
                <table>
                  <tbody>
                    {topProductos.map((prod, i) => (
                      <tr key={i}>
                        <td>{prod.name}</td>
                        <td className="text-right">{prod.unidades} uds</td>
                        <td className="text-right">{formatDashboardMoney(prod.ingresos, ventas.moneda)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="empty-state">{t('dashboard:panaderia.noData')}</p>
              )}
            </div>
          </section>
        )}

      </div>
      )}

      {/* Modal de pedido rápido */}
      {orderOpen && (
        <QuickOrderModal
          saving={orderSaving}
          error={orderError}
          lineas={orderLineas}
          clienteId={orderClienteId}
          clienteName={orderClienteName}
          deliveryDate={orderDeliveryDate}
          notes={orderNotes}
          deposit={orderDeposit}
          depositPaid={orderDepositPaid}
          paymentMethod={orderPaymentMethod}
          showPicker={orderShowPicker}
          yaCobrado={orderYaCobrado}
          onClienteChange={(id, name) => { setOrderClienteId(id ? String(id) : undefined); setOrderClienteName(name) }}
          onDeliveryDate={setOrderDeliveryDate}
          onNotes={setOrderNotes}
          onDeposit={setOrderDeposit}
          onDepositPaid={setOrderDepositPaid}
          onPaymentMethod={setOrderPaymentMethod}
          onAddLinea={l => {
            setOrderLineas(prev => {
              const idx = prev.findIndex(x => String(x.producto_id) === String(l.producto_id))
              if (idx !== -1) {
                const next = [...prev]
                next[idx] = { ...next[idx], cantidad: next[idx].cantidad + (l.cantidad ?? 1) }
                return next
              }
              return [...prev, l]
            })
          }}
          onUpdateLinea={(idx, field, val) => setOrderLineas(prev => { const n = [...prev]; n[idx] = { ...n[idx], [field]: val }; return n })}
          onRemoveLinea={idx => setOrderLineas(prev => prev.filter((_, i) => i !== idx))}
          onYaCobrado={setOrderYaCobrado}
          onTogglePicker={() => setOrderShowPicker(v => !v)}
          onClose={() => setOrderOpen(false)}
          onSubmit={handleSaveOrder}
        />
      )}

      {/* Modal de producción rápida */}
      {quickOpen && (
        <QuickProductionModal
          saving={quickSaving}
          loading={quickLoading}
          error={quickError}
          recipes={recipes}
          selectedRecipeId={selectedRecipeId}
          selectedRecipe={selectedRecipe}
          recipeIngredients={recipeIngredients}
          qtyMode={qtyMode}
          otherQty={otherQty}
          effectiveQty={effectiveQty}
          selectedIngredientId={selectedIngredientId}
          selectedIngredient={selectedIngredient}
          ingredientAmount={ingredientAmount}
          ingredientInputUnit={ingredientInputUnit}
          ingredientStock={ingredientStock}
          stockLoading={stockLoading}
          quickCalculation={quickCalculation}
          calcLoading={quickCalcLoading}
          quickMaterialsTotal={quickMaterialsTotal}
          quickIndirectTotal={quickIndirectTotal}
          quickEstimatedTotal={quickEstimatedTotal}
          quickUnitEstimated={quickUnitEstimated}
          advancedOpen={quickAdvancedOpen}
          costLines={quickCostLines}
          drivers={quickDrivers}
          wasteQty={quickWasteQty}
          notes={quickNotes}
          onSelectRecipe={handleSelectRecipe}
          onQtyMode={setQtyMode}
          onOtherQty={setOtherQty}
          onSelectIngredient={handleSelectIngredient}
          onIngredientAmount={setIngredientAmount}
          onIngredientUnit={setIngredientInputUnit}
          onUseAllStock={handleUseAllStock}
          onToggleAdvanced={() => setQuickAdvancedOpen((v) => !v)}
          onUpdateCostLine={updateQuickCostLine}
          onAddCostLine={() => setQuickCostLines((prev) => [...prev, createEmptyQuickCost(quickDrivers[0]?.id || '')])}
          onRemoveCostLine={(key) => setQuickCostLines((prev) => prev.filter((l) => l.key !== key))}
          onWasteQty={setQuickWasteQty}
          onNotes={setQuickNotes}
          onClose={() => setQuickOpen(false)}
          onSubmit={handleQuickProduction}
        />
      )}
    </DashboardPro>
  )
}

export default PanaderiaDashboard
