import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listRecipes, deleteRecipe, type Recipe } from '../../services/api/recetas'
import { listProducts, type Product } from '../../services/api/products'
import { getBulkRecipeFullCosts } from '../../services/api/productionCosts'
import { getCompanySettings, getCurrencySymbol, getDefaultTaxRate, type CompanySettings } from '../../services/companySettings'
import tenantApi from '../../shared/api/client'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'
import { usePermission } from '../../hooks/usePermission'

function safeImageUrl(url: unknown): string | null {
  if (!url || typeof url !== 'string') return null
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return null
    return url
  } catch {
    return null
  }
}
import { useToast } from '../../shared/toast'

export default function RecetasList() {
  return (
    <ProductionAvailabilityGuard>
      <RecetasListContent />
    </ProductionAvailabilityGuard>
  )
}

function RecetasListContent() {
  const { t } = useTranslation(['costing', 'common'])
  const can = usePermission()
  const canWrite = can('produccion:write')
  const { success, error: toastError } = useToast()
  const navigate = useNavigate()
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [settings, setSettings] = useState<CompanySettings | null>(null)
  const [category, setCategory] = useState<string>('all')
  const [page, setPage] = useState<number>(1)
  const [perPage, setPerPage] = useState<number>(9)
  const [multiplier, setMultiplier] = useState<number>(1.25)
  const [markupPct, setMarkupPct] = useState<number>(25)
  const [useProductTax, setUseProductTax] = useState<boolean>(false)
  const [fullCosts, setFullCosts] = useState<Record<string, { indirect: number; wastePct: number; overheadPct: number }>>({})
  const [correctedCosts, setCorrectedCosts] = useState<Record<string, { total: number; unit: number }>>({})
  const [deleteModal, setDeleteModal] = useState<{ id: string; name: string } | null>(null)
  const [deleting, setDeleting] = useState(false)
  const currency = useMemo(() => getCurrencySymbol(settings || undefined), [settings])

  // ── Categorías de recetas (guardadas en localStorage) ──────────────────────
  const [recipeCategories, setRecipeCategories] = useState<Record<string, string>>(() => {
    try { return JSON.parse(localStorage.getItem('recipe_cats') || '{}') } catch { return {} }
  })
  const [categoryList, setCategoryList] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('recipe_cat_list') || '[]') } catch { return [] }
  })
  const [newCatName, setNewCatName] = useState('')
  const [addingCat, setAddingCat] = useState(false)
  const [assigningCat, setAssigningCat] = useState<string | null>(null)

  const persistCategories = (cats: Record<string, string>, list: string[]) => {
    try { localStorage.setItem('recipe_cats', JSON.stringify(cats)) } catch {}
    try { localStorage.setItem('recipe_cat_list', JSON.stringify(list)) } catch {}
  }
  const assignCategory = (recipeId: string, cat: string) => {
    const next = cat ? { ...recipeCategories, [recipeId]: cat } : (({ [recipeId]: _, ...rest }) => rest)(recipeCategories)
    setRecipeCategories(next)
    persistCategories(next, categoryList)
    setAssigningCat(null)
  }
  const addCategory = () => {
    const name = newCatName.trim()
    if (!name || categoryList.includes(name)) { setNewCatName(''); setAddingCat(false); return }
    const next = [...categoryList, name]
    setCategoryList(next)
    persistCategories(recipeCategories, next)
    setNewCatName('')
    setAddingCat(false)
  }
  const deleteCategory = (name: string) => {
    const nextList = categoryList.filter(c => c !== name)
    const nextCats = Object.fromEntries(Object.entries(recipeCategories).filter(([, c]) => c !== name))
    setCategoryList(nextList)
    setRecipeCategories(nextCats)
    persistCategories(nextCats, nextList)
    if (category === name) setCategory('all')
  }

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        setError(null)
        const [rs, ps, cfg] = await Promise.all([
          listRecipes({ limit: 500 }),
          listProducts({ limit: 500 }),
          getCompanySettings(),
        ])
        if (!cancelled) {
          const recipeList = Array.isArray(rs) ? rs : []
          setRecipes(recipeList)
          setProducts(Array.isArray(ps) ? ps : [])
          setSettings(cfg)
          // Carga costos completos en bulk (1 request POST) y usa total_cost/unit_cost
          // del listado para el mapa corregido — sin N+1 de getRecipe individual
          const bulkCosts = await getBulkRecipeFullCosts(recipeList.map(r => r.id))
            .catch(() => ({} as Record<string, any>))
          if (cancelled) return
          const fcMap: Record<string, { indirect: number; wastePct: number; overheadPct: number }> = {}
          const ccMap: Record<string, { total: number; unit: number }> = {}
          for (const r of recipeList) {
            const fc = bulkCosts[r.id] || null
            fcMap[r.id] = {
              indirect: Number(fc?.indirect_total || 0),
              wastePct: Number(fc?.waste_pct || 0),
              overheadPct: Number(fc?.overhead_pct || 0),
            }
            // Usar full_cost del bulk si existe, sino caer a total_cost de la lista
            if (fc?.full_cost_total != null) {
              const qty = Number(r.yield_qty || 1)
              ccMap[r.id] = {
                total: Number(fc.full_cost_total),
                unit: qty > 0 ? Number(fc.full_cost_unit ?? fc.full_cost_total / qty) : 0,
              }
            } else if (r.total_cost != null) {
              const qty = Number(r.yield_qty || 1)
              ccMap[r.id] = {
                total: Number(r.total_cost),
                unit: qty > 0 ? Number(r.unit_cost ?? r.total_cost / qty) : 0,
              }
            }
          }
          setFullCosts(fcMap)
          setCorrectedCosts(ccMap)
          try {
            const fromSettings = (cfg as any)?.settings?.produccion_margin_multiplier as number | undefined
            const fromStorage = localStorage.getItem('produccion_margin_multiplier')
            const init = Number(fromSettings || (fromStorage ? parseFloat(fromStorage) : 1.25))
            if (!Number.isNaN(init) && init > 0) {
              setMultiplier(init)
              setMarkupPct(Number(((init - 1) * 100).toFixed(0)))
            }
            const useTaxLS = localStorage.getItem('produccion_use_product_tax')
            if (useTaxLS != null) setUseProductTax(useTaxLS === '1')
          } catch {}
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Error loading recipes')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase()
    let list = recipes
    if (term) {
      list = list.filter(r =>
        (r.name || '').toLowerCase().includes(term) ||
        (r.product_name || '').toLowerCase().includes(term)
      )
    }
    if (category !== 'all') {
      list = list.filter(r => (recipeCategories[r.id] || '') === category)
    }
    return list
  }, [q, recipes, category, recipeCategories])

  const categoryCount = useMemo(() => {
    const counts: Record<string, number> = { all: recipes.length }
    for (const cat of categoryList) {
      counts[cat] = recipes.filter(r => recipeCategories[r.id] === cat).length
    }
    return counts
  }, [recipes, categoryList, recipeCategories])

  const totalPages = useMemo(() => Math.max(1, Math.ceil(filtered.length / perPage)), [filtered.length, perPage])
  const pageItems = useMemo(() => {
    const p = Math.min(Math.max(1, page), totalPages)
    const start = (p - 1) * perPage
    return filtered.slice(start, start + perPage)
  }, [filtered, page, perPage, totalPages])

  useEffect(() => {
    setPage(1)
  }, [q, category, perPage])

  const fmt = (n: number, digits = 2) => `${currency}${Number(n || 0).toFixed(digits)}`
  const precioSugerido = (costoPorUnidad: number) => costoPorUnidad * multiplier
  const margenPct = (costoPorUnidad: number, precio: number) => (precio > 0 ? ((precio - costoPorUnidad) / precio) * 100 : 0)

  // El multiplicador se controla manualmente por el usuario (% Utilidad Deseada)

  const priceIncludesTax = !!(settings?.pos_config?.tax?.price_includes_tax)
  const defaultTaxRate = getDefaultTaxRate(settings || undefined) || 0
  const applyTax = (amount: number, prod?: Product) => {
    if (!priceIncludesTax) return amount
    const rateCandidate = useProductTax && prod?.tax_rate != null ? Number(prod.tax_rate) : defaultTaxRate
    const rate = rateCandidate > 1 ? rateCandidate / 100 : rateCandidate
    return amount * (1 + (isFinite(rate) ? rate : defaultTaxRate))
  }

  const saveMarginConfig = async () => {
    try {
      const { data: current } = await tenantApi.get<any>('/api/v1/company/settings/fiscal')
      const merged = { ...(current || {}), produccion_margin_multiplier: multiplier, pricing_strategy: 'manual' }
      await tenantApi.put('/api/v1/company/settings/fiscal', merged)
      success(t('recipesList.profitSaved', { pct: markupPct }))
    } catch (e: any) {
      console.error('Error saving margin:', e)
      toastError(t('recipesList.saveError'))
    }
  }

  const handleDeleteConfirm = async () => {
    if (!canWrite || !deleteModal) return
    setDeleting(true)
    try {
      await deleteRecipe(deleteModal.id)
      setRecipes((prev) => prev.filter((r) => r.id !== deleteModal.id))
      success(t('forms.successDelete', { name: deleteModal.name }))
      setDeleteModal(null)
    } catch (e: any) {
      console.error('Error deleting recipe', e)
      toastError(t('errors.deletingRecipe'))
    } finally {
      setDeleting(false)
    }
  }

  if (loading) return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-gray-400">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <span className="text-sm">{t('recipesList.loading')}</span>
    </div>
  )
  if (error) return <div className="p-6 text-red-600">{error}</div>

  return (
    <>
      <div className="p-6 max-w-7xl mx-auto">

        {/* Page header */}
        <div className="mb-6 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Recetas de producción</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {filtered.length} receta{filtered.length !== 1 ? 's' : ''}
              {category !== 'all' && ` · ${category}`}
            </p>
          </div>
          {canWrite && (
            <button
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl font-semibold text-sm shadow-sm transition-colors"
              onClick={() => navigate('nueva')}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" /></svg>
              {t('recipesList.newRecipe')}
            </button>
          )}
        </div>

        {/* ── Toolbar ── */}
        <div className="mb-5 bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">

          {/* Fila 1: categorías + búsqueda + accesos */}
          <div className="px-3 pt-3 pb-2 flex flex-wrap items-center gap-2 border-b border-gray-100">
            {/* Search */}
            <div className="relative min-w-44 flex-1 max-w-64">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              <input
                type="search"
                className="w-full border border-gray-200 rounded-lg pl-9 pr-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder={t('recipesList.searchPlaceholder')}
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </div>

            <div className="h-5 w-px bg-gray-200" />

            {/* Category pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => setCategory('all')}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${category === 'all' ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                Todas <span className={`text-xs ml-0.5 ${category === 'all' ? 'text-blue-200' : 'text-gray-400'}`}>{categoryCount.all}</span>
              </button>
              {categoryList.map(cat => (
                <div key={cat} className="relative group flex items-center">
                  <button
                    onClick={() => setCategory(cat === category ? 'all' : cat)}
                    className={`pl-3 pr-6 py-1 rounded-full text-sm font-medium transition-colors ${category === cat ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                  >
                    {cat} <span className={`text-xs ml-0.5 ${category === cat ? 'text-blue-200' : 'text-gray-400'}`}>{categoryCount[cat] ?? 0}</span>
                  </button>
                  <button
                    onClick={() => deleteCategory(cat)}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500"
                    title="Eliminar categoría"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              ))}

              {/* Nueva categoría */}
              {addingCat ? (
                <div className="flex items-center gap-1">
                  <input
                    autoFocus
                    type="text"
                    className="border border-blue-300 rounded-full px-3 py-1 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-blue-400"
                    placeholder="Nombre…"
                    value={newCatName}
                    onChange={e => setNewCatName(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') addCategory(); if (e.key === 'Escape') { setAddingCat(false); setNewCatName('') }}}
                  />
                  <button onClick={addCategory} className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                  </button>
                  <button onClick={() => { setAddingCat(false); setNewCatName('') }} className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center hover:bg-gray-200">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setAddingCat(true)}
                  className="px-2.5 py-1 rounded-full border-2 border-dashed border-gray-300 text-xs text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors font-medium"
                >
                  + Categoría
                </button>
              )}
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Navigation shortcuts */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <button
                className="inline-flex items-center gap-1.5 border border-gray-200 hover:border-emerald-300 hover:text-emerald-700 text-gray-500 px-2.5 py-1.5 rounded-lg text-xs transition-colors"
                onClick={() => navigate('../ingredientes')}
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                Ingredientes
              </button>
              <button
                className="inline-flex items-center gap-1.5 border border-gray-200 hover:border-gray-400 text-gray-500 px-2.5 py-1.5 rounded-lg text-xs transition-colors"
                onClick={() => navigate('../costos')}
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                Costos
              </button>
            </div>
          </div>

          {/* Fila 2: configuración de precios */}
          <div className="px-3 py-2 flex flex-wrap items-center gap-3 bg-gray-50">
            {/* IVA toggle */}
            <label className="inline-flex items-center gap-2 text-xs text-gray-500 select-none cursor-pointer">
              <input
                type="checkbox"
                className="rounded"
                checked={useProductTax}
                onChange={(e) => {
                  setUseProductTax(e.target.checked)
                  try { localStorage.setItem('produccion_use_product_tax', e.target.checked ? '1' : '0') } catch {}
                }}
              />
              {t('recipesList.taxPerProduct')}
            </label>

            <div className="h-4 w-px bg-gray-200" />

            {/* Utilidad */}
            <div className="inline-flex items-center gap-1.5" title={t('recipesList.profitTooltip')}>
              <span className="text-xs text-gray-500 whitespace-nowrap">Utilidad</span>
              <input
                type="number"
                min="0" max="500" step="1"
                className="w-14 text-center text-sm font-semibold border border-gray-200 rounded-lg px-1 py-0.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                value={markupPct}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  if (!isNaN(v) && v >= 0) {
                    setMarkupPct(v)
                    const newMult = Number((1 + v / 100).toFixed(2))
                    setMultiplier(newMult)
                    try { localStorage.setItem('produccion_margin_multiplier', String(newMult)) } catch {}
                  }
                }}
              />
              <span className="text-xs text-gray-400">%</span>
            </div>

            <div className="h-4 w-px bg-gray-200" />

            {/* Create from product */}
            <select
              className="border border-gray-200 rounded-lg px-2 py-1 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-400 max-w-48"
              onChange={(e) => canWrite && e.target.value && navigate(`nueva?productId=${encodeURIComponent(e.target.value)}`)}
              value=""
              disabled={!canWrite}
            >
              <option value="">{t('recipesList.createFromProduct')}</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>

            {/* Guardar configuración */}
            {canWrite && (
              <>
                <div className="flex-1" />
                <button
                  className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                  title={t('recipesList.saveTooltip')}
                  onClick={saveMarginConfig}
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" /></svg>
                  Guardar utilidad
                </button>
              </>
            )}
          </div>
        </div>

        {/* Grid */}
        {pageItems.length === 0 ? (
          <div className="py-20 text-center border-2 border-dashed border-gray-200 rounded-2xl">
            <div className="text-4xl mb-3">🍞</div>
            <p className="text-gray-500 font-medium">{t('recipesList.noRecipes')}</p>
            {canWrite && (
              <button
                className="mt-4 inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-semibold"
                onClick={() => navigate('nueva')}
              >
                + {t('recipesList.newRecipe')}
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {pageItems.map((r) => {
                const cc = correctedCosts[r.id]
                const costoUnidad = cc ? cc.unit : (r.unit_cost || 0)
                const costoTotal = cc ? cc.total : (r.total_cost || costoUnidad * (r.yield_qty || 1))
                const precio = precioSugerido(costoUnidad)
                const prod = products.find(p => p.id === r.product_id)
                const precioDisplay = applyTax(precio, prod)
                const margen = margenPct(costoUnidad, precio)
                const beneficio = precio - costoUnidad
                const isLoaded = !!cc

                // Margin color
                const marginBg   = margen >= 30 ? 'bg-emerald-500' : margen >= 15 ? 'bg-amber-400' : 'bg-red-500'
                const marginText = margen >= 30 ? 'text-emerald-700 bg-emerald-50' : margen >= 15 ? 'text-amber-700 bg-amber-50' : 'text-red-700 bg-red-50'
                const borderAccent = margen >= 30 ? 'border-t-emerald-400' : margen >= 15 ? 'border-t-amber-400' : 'border-t-red-400'

                return (
                  <div
                    key={r.id}
                    className={`bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col border-t-4 ${isLoaded ? borderAccent : 'border-t-gray-200'}`}
                  >
                    {/* Card header */}
                    <div className="px-4 pt-4 pb-3 flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        {prod?.image_url && safeImageUrl(prod.image_url) ? (
                          <img src={safeImageUrl(prod.image_url)!} alt={prod.name} className="w-11 h-11 rounded-xl object-cover bg-gray-100 flex-shrink-0" />
                        ) : (
                          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center text-slate-500 font-bold text-lg flex-shrink-0">
                            {(r.product_name || 'P').charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="text-xs text-gray-400 truncate">{r.product_name || t('recipesList.product')}</p>
                          <h3 className="font-bold text-gray-900 truncate leading-tight">{r.name}</h3>
                        </div>
                      </div>
                      {/* Categoría de receta editable */}
                      <div className="relative flex-shrink-0">
                        {assigningCat === r.id ? (
                          <select
                            autoFocus
                            className="text-xs border border-blue-300 rounded-full px-2 py-0.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                            value={recipeCategories[r.id] || ''}
                            onChange={e => assignCategory(r.id, e.target.value)}
                            onBlur={() => setAssigningCat(null)}
                          >
                            <option value="">Sin categoría</option>
                            {categoryList.map(c => <option key={c} value={c}>{c}</option>)}
                          </select>
                        ) : (
                          <button
                            onClick={() => setAssigningCat(r.id)}
                            className={`text-xs px-2 py-0.5 rounded-full transition-colors ${recipeCategories[r.id] ? 'bg-violet-100 text-violet-700 hover:bg-violet-200' : 'bg-gray-100 text-gray-400 hover:bg-gray-200'}`}
                            title="Clic para cambiar categoría"
                          >
                            {recipeCategories[r.id] || '+ categoría'}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Divider */}
                    <div className="mx-4 border-t border-gray-100" />

                    {/* Key metrics */}
                    <div className="px-4 py-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                      <div>
                        <p className="text-xs text-gray-400">Costo lote</p>
                        <p className="font-semibold text-gray-900">{fmt(costoTotal)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Rendimiento</p>
                        <p className="font-semibold text-gray-900">{r.yield_qty} <span className="text-gray-400 font-normal text-xs">und</span></p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Costo / und</p>
                        <p className="font-semibold text-gray-900">{fmt(costoUnidad, 3)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Precio sugerido</p>
                        <p className="font-semibold text-gray-900">{fmt(precioDisplay)}</p>
                      </div>
                    </div>

                    {/* Profit highlight */}
                    <div className="mx-4 mb-3 rounded-xl bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-100 px-3 py-2 flex items-center justify-between">
                      <div>
                        <p className="text-xs text-emerald-600">Beneficio / unidad</p>
                        <p className="font-bold text-emerald-700 text-base">{fmt(beneficio, 3)}</p>
                      </div>
                      {isLoaded && (
                        <div className="text-right">
                          <span className={`inline-block text-xs font-bold px-2.5 py-1 rounded-full ${marginText}`}>
                            {margen.toFixed(0)}% margen
                          </span>
                          {/* Mini bar */}
                          <div className="mt-1.5 w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${marginBg}`} style={{ width: `${Math.min(margen, 100)}%` }} />
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Footer */}
                    <div className="mt-auto px-4 py-2.5 border-t border-gray-100 flex items-center justify-between">
                      <p className="text-xs text-gray-400">
                        Markup {((multiplier - 1) * 100).toFixed(0)}%{priceIncludesTax ? ' · IVA inc.' : ''}
                      </p>
                      <div className="flex items-center gap-1">
                        <button
                          className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors"
                          onClick={() => navigate(r.id)}
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                          Ver
                        </button>
                        {canWrite && (
                          <button
                            className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                            onClick={() => navigate(`${r.id}/editar`)}
                            title={t('actions.editRecipe')}
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                          </button>
                        )}
                        {canWrite && (
                          <button
                            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                            onClick={() => setDeleteModal({ id: r.id, name: r.name })}
                            title={t('actions.deleteRecipe')}
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Pagination */}
            <div className="mt-6 flex items-center justify-between text-sm text-gray-500">
              <p>Mostrando {Math.min((page - 1) * perPage + 1, filtered.length)}–{Math.min(page * perPage, filtered.length)} de {filtered.length}</p>
              <div className="flex items-center gap-1">
                <button
                  disabled={page <= 1}
                  className="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                >
                  ‹ Anterior
                </button>
                <span className="px-3 py-1.5 text-gray-700 font-medium">{page} / {totalPages}</span>
                <button
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                >
                  Siguiente ›
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Delete modal */}
      {canWrite && deleteModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => !deleting && setDeleteModal(null)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start gap-3 mb-5">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </div>
              <div>
                <h3 className="font-bold text-gray-900">{t('forms.confirmDelete', { name: deleteModal.name })}</h3>
                <p className="text-sm text-gray-500 mt-0.5">Esta acción no se puede deshacer.</p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                disabled={deleting}
                onClick={() => setDeleteModal(null)}
                className="px-4 py-2 rounded-xl border border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                disabled={deleting}
                onClick={handleDeleteConfirm}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
              >
                {deleting ? 'Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
