import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listRecipes, deleteRecipe, type Recipe } from '../../services/api/recetas'
import { listProducts, type Product } from '../../services/api/products'
import { getRecipeFullCost, type FullCostSummary } from '../../services/api/productionCosts'
import { getCompanySettings, getCurrencySymbol, getDefaultTaxRate, type CompanySettings } from '../../services/companySettings'
import tenantApi from '../../shared/api/client'

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
  const { t } = useTranslation(['costing', 'common'])
  const { success, error: toastError } = useToast()
  const navigate = useNavigate()
  const { empresa } = useParams()
  const basePath = `${empresa ? `/${empresa}` : ''}/produccion`
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
  const [fullCosts, setFullCosts] = useState<Record<string, FullCostSummary>>({})
  const [deleteModal, setDeleteModal] = useState<{ id: string; name: string } | null>(null)
  const [deleting, setDeleting] = useState(false)
  const currency = useMemo(() => getCurrencySymbol(settings || undefined), [settings])

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
          // Load full costs (with indirect) in background
          Promise.all(
            recipeList.map(r =>
              getRecipeFullCost(r.id).then(fc => [r.id, fc] as const).catch(() => null)
            )
          ).then(results => {
            if (cancelled) return
            const map: Record<string, FullCostSummary> = {}
            for (const entry of results) {
              if (entry) map[entry[0]] = entry[1]
            }
            setFullCosts(map)
          })
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
      list = list.filter(r => {
        const prod = products.find(p => p.id === r.product_id)
        const cat = (prod?.category || '').toLowerCase()
        return cat === category.toLowerCase()
      })
    }
    return list
  }, [q, recipes, category, products])

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

  const handleDeleteConfirm = async () => {
    if (!deleteModal) return
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

  if (loading) return <div className="p-6 text-gray-500">{t('recipesList.loading')}</div>
  if (error) return <div className="p-6 text-red-600">{error}</div>

  return (
    <>
      <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="search"
            className="border rounded px-3 py-2 w-full md:w-80"
            placeholder={t('recipesList.searchPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">{t('recipesList.category')}</label>
            <select
              className="border rounded px-3 py-2"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="all">{t('recipesList.categoryAll')}</option>
              {[...new Set(products.map(p => p.category).filter(Boolean))].map((c) => (
                <option key={String(c)} value={String(c)}>{String(c)}</option>
              ))}
            </select>
          </div>

          <label className="inline-flex items-center gap-2 text-sm text-gray-700 select-none">
            <input
              type="checkbox"
              checked={useProductTax}
              onChange={(e) => {
                setUseProductTax(e.target.checked)
                try { localStorage.setItem('produccion_use_product_tax', e.target.checked ? '1' : '0') } catch {}
              }}
            />
            {t('recipesList.taxPerProduct')}
          </label>

          <div className="flex items-center gap-2 border rounded px-2 py-1 bg-white" title={t('recipesList.profitTooltip')}>
            <label className="text-sm text-gray-600 whitespace-nowrap">{t('recipesList.profitPct')}</label>
            <input
              type="number"
              min="0"
              max="500"
              step="1"
              className="border rounded px-2 py-1 w-20 text-center"
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
            <span className="text-xs text-gray-400">×{multiplier}</span>
          </div>

          <select
            className="border rounded px-3 py-2"
            onChange={(e) => e.target.value && navigate(`${basePath}/recetas/nueva?productId=${encodeURIComponent(e.target.value)}`)}
            defaultValue=""
          >
            <option value="" disabled>
              {t('recipesList.createFromProduct')}
            </option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            onClick={() => navigate(`${basePath}/recetas/nueva`)}
          >
            {t('recipesList.newRecipe')}
          </button>
          <button
            className="border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded text-sm"
            onClick={() => navigate(`${basePath}/costos`)}
            title={t('recipesList.indirectCostsTooltip')}
          >
            ⚙️ {t('recipesList.indirectCosts')}
          </button>
          <button
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded"
            title={t('recipesList.saveTooltip')}
            onClick={async () => {
              try {
                const { data: current } = await tenantApi.get<any>('/api/v1/company/settings/fiscal')
                const merged = { ...(current || {}), produccion_margin_multiplier: multiplier, pricing_strategy: 'manual' }
                await tenantApi.put('/api/v1/company/settings/fiscal', merged)
                success(t('recipesList.profitSaved', { pct: markupPct }))
              } catch (e: any) {
                console.error('Error saving margin:', e)
                toastError(t('recipesList.saveError'))
              }
            }}
          >
            💾 {t('recipesList.save')}
          </button>
        </div>
      </div>

      {pageItems.length === 0 ? (
        <div className="p-10 text-center text-gray-500 border rounded">{t('recipesList.noRecipes')}</div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {pageItems.map((r) => {
              const fc = fullCosts[r.id]
              const costoUnidad = fc ? Number(fc.full_cost_unit || 0) : (r.unit_cost || 0)
              const costoTotal = fc ? Number(fc.full_cost_total || 0) : (r.total_cost || costoUnidad * (r.yield_qty || 1))
              const precio = precioSugerido(costoUnidad)
              const prod = products.find(p => p.id === r.product_id)
              const precioDisplay = applyTax(precio, prod)
              const margen = margenPct(costoUnidad, precio)
              return (
                <div key={r.id} className="border rounded-lg p-4 bg-white shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {prod?.image_url && safeImageUrl(prod.image_url) ? (
                        <img src={safeImageUrl(prod.image_url)!} alt={prod.name} className="w-10 h-10 rounded object-cover bg-gray-100" />
                      ) : (
                        <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center text-gray-500 text-sm">
                          {(r.product_name || 'P').charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <div className="text-sm text-gray-500">{r.product_name || t('recipesList.product')}</div>
                        <div className="font-semibold text-gray-900">{r.name}</div>
                      </div>
                    </div>
                    <span className="text-xs inline-flex items-center px-2 py-1 rounded bg-amber-100 text-amber-800">
                      {t('recipesList.production')}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">{t('recipesList.totalCost')}</div>
                      <div className="font-semibold">{fmt(costoTotal)}</div>
                    </div>
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">{t('recipesList.yield')}</div>
                      <div className="font-semibold">{r.yield_qty} {t('recipesList.units')}</div>
                    </div>
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">{t('recipesList.unitCost')}</div>
                      <div className="font-semibold">{fmt(costoUnidad, 3)}</div>
                    </div>
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">{t('recipesList.suggestedPrice')} {priceIncludesTax ? t('recipesList.taxIncluded') : t('recipesList.noTax')}
                      </div>
                      <div className="font-semibold">{fmt(precioDisplay)}</div>
                    </div>
                    <div className="p-2 rounded bg-emerald-50 col-span-2">
                      <div className="text-gray-500">{t('recipesList.profitPerUnit')}</div>
                      <div className="font-semibold text-emerald-700">{fmt(precio - costoUnidad, 3)}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <div className="text-xs text-gray-600 flex items-center gap-2">
                      {prod?.category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-700">{prod.category}</span>
                      )}
                      <span>{t('recipesList.markup')} {((multiplier - 1) * 100).toFixed(0)}% · {t('recipesList.margin')} {margen.toFixed(0)}%</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="text-blue-600 hover:underline text-sm"
                        onClick={() => navigate(`${basePath}/recetas/${r.id}`)}
                      >
                        {t('recipesList.view')}
                      </button>
                      <button
                        className="text-gray-700 hover:underline text-sm"
                        onClick={() => navigate(`${basePath}/recetas/${r.id}/editar`)}
                      >
                        {t('recipesList.edit')}
                      </button>
                      <button
                        className="text-red-600 hover:underline text-sm"
                        onClick={() => setDeleteModal({ id: r.id, name: r.name })}
                      >
                        {t('actions.deleteRecipe')}
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <div>
              {t('recipesList.showing')} {Math.min((page - 1) * perPage + 1, filtered.length)}–{Math.min(page * perPage, filtered.length)} {t('recipesList.of')} {filtered.length}
            </div>
            <div className="flex items-center gap-2">
              <button disabled={page <= 1} className="px-2 py-1 border rounded disabled:opacity-50" onClick={() => setPage(p => Math.max(1, p - 1))}>{t('recipesList.previous')}</button>
              <span>{t('recipesList.page')} {page} / {totalPages}</span>
              <button disabled={page >= totalPages} className="px-2 py-1 border rounded disabled:opacity-50" onClick={() => setPage(p => Math.min(totalPages, p + 1))}>{t('recipesList.next')}</button>
            </div>
          </div>
        </>
      )}
      </div>
      {deleteModal && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 50,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          onClick={() => !deleting && setDeleteModal(null)}
        >
          <div
            style={{
              background: '#fff', borderRadius: 12, padding: '1.5rem', maxWidth: 400, width: '90%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1rem' }}>
              <div style={{ width: 40, height: 40, borderRadius: '50%', background: '#FEF2F2', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <svg width="20" height="20" fill="none" stroke="#EF4444" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16, color: '#111827' }}>
                  {t('forms.confirmDelete', { name: deleteModal.name })}
                </div>
                <div style={{ fontSize: 13, color: '#6b7280', marginTop: 2 }}>
                  Esta acción no se puede deshacer.
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: '1rem' }}>
              <button
                disabled={deleting}
                onClick={() => setDeleteModal(null)}
                style={{ padding: '0.5rem 1rem', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 14, color: '#374151' }}
              >
                Cancelar
              </button>
              <button
                disabled={deleting}
                onClick={handleDeleteConfirm}
                style={{ padding: '0.5rem 1.25rem', borderRadius: 8, border: 'none', background: '#EF4444', color: '#fff', cursor: deleting ? 'not-allowed' : 'pointer', fontWeight: 600, fontSize: 14, opacity: deleting ? 0.7 : 1 }}
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
