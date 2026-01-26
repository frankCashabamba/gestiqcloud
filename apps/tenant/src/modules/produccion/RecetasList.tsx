import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { listRecipes, type Recipe } from '../../services/api/recetas'
import { listProducts, type Product } from '../../services/api/products'
import { getCompanySettings, getCurrencySymbol, getDefaultTaxRate, type CompanySettings } from '../../services/companySettings'
import tenantApi from '../../shared/api/client'

export default function RecetasList() {
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
  const [multiplier, setMultiplier] = useState<number>(2.5)
  const [markupPct, setMarkupPct] = useState<number>(150)
  const [useProductTax, setUseProductTax] = useState<boolean>(false)
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
          setRecipes(Array.isArray(rs) ? rs : [])
          setProducts(Array.isArray(ps) ? ps : [])
          setSettings(cfg)
          try {
            const fromSettings = (cfg as any)?.settings?.produccion_margin_multiplier as number | undefined
            const fromStorage = localStorage.getItem('produccion_margin_multiplier')
            const init = Number(fromSettings || (fromStorage ? parseFloat(fromStorage) : 2.5))
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

  const updateMultiplier = (val: number) => {
    const v = Number(val)
    if (Number.isFinite(v) && v > 0) {
      setMultiplier(v)
      setMarkupPct(Number(((v - 1) * 100).toFixed(0)))
      try { localStorage.setItem('produccion_margin_multiplier', String(v)) } catch {}
    }
  }
  const updateMarkupPct = (pct: number) => {
    const p = Number(pct)
    if (Number.isFinite(p)) {
      setMarkupPct(p)
      const v = 1 + p / 100
      setMultiplier(Number(v.toFixed(3)))
      try { localStorage.setItem('produccion_margin_multiplier', String(v)) } catch {}
    }
  }

  const priceIncludesTax = !!(settings?.pos_config?.tax?.price_includes_tax)
  const defaultTaxRate = getDefaultTaxRate(settings || undefined) || 0
  const applyTax = (amount: number, prod?: Product) => {
    if (!priceIncludesTax) return amount
    const rateCandidate = useProductTax && prod?.tax_rate != null ? Number(prod.tax_rate) : defaultTaxRate
    const rate = rateCandidate > 1 ? rateCandidate / 100 : rateCandidate
    return amount * (1 + (isFinite(rate) ? rate : defaultTaxRate))
  }

  if (loading) return <div className="p-6 text-gray-500">Loading recipes...</div>
  if (error) return <div className="p-6 text-red-600">{error}</div>

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="search"
            className="border rounded px-3 py-2 w-full md:w-80"
            placeholder="Search recipe or product…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Category</label>
            <select
              className="border rounded px-3 py-2"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="all">All</option>
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
            IVA por producto
          </label>

          <div className="flex items-center gap-2 border rounded px-2 py-1 bg-white">
            <label className="text-sm text-gray-600">Markup %</label>
            <input
              type="number"
              step={1}
              min={0}
              className="border rounded px-2 py-1 w-20"
              value={markupPct}
              onChange={(e) => updateMarkupPct(parseFloat(e.target.value))}
              title="Porcentaje sobre costo (150% = x2.5)"
            />
            <span className="text-gray-400">·</span>
            <label className="text-sm text-gray-600">Multiplicador</label>
            <input
              type="number"
              step={0.05}
              min={0.01}
              className="border rounded px-2 py-1 w-24"
              value={multiplier}
              onChange={(e) => updateMultiplier(parseFloat(e.target.value))}
              title="Precio sugerido = costo × multiplicador"
            />
          </div>

          <select
            className="border rounded px-3 py-2"
            onChange={(e) => e.target.value && navigate(`${basePath}/recetas/nueva?productId=${encodeURIComponent(e.target.value)}`)}
            defaultValue=""
          >
            <option value="" disabled>
              Crear receta desde producto…
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
            New recipe
          </button>
          <button
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded"
            title="Save margin as tenant setting"
            onClick={async () => {
              try {
                const { data: current } = await tenantApi.get<any>('/api/v1/company/settings/fiscal')
                const merged = { ...(current || {}), produccion_margin_multiplier: multiplier }
                await tenantApi.put('/api/v1/company/settings/fiscal', merged)
                alert('Margin saved to tenant settings')
              } catch (e: any) {
                console.error('Error saving margin:', e)
                alert('Could not save margin (requires admin permissions)')
              }
            }}
          >
            Save margin
          </button>
        </div>
      </div>

      {pageItems.length === 0 ? (
        <div className="p-10 text-center text-gray-500 border rounded">Sin recetas aún</div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {pageItems.map((r) => {
              const costoUnidad = r.unit_cost || 0
              const precio = precioSugerido(costoUnidad)
              const prod = products.find(p => p.id === r.product_id)
              const precioDisplay = applyTax(precio, prod)
              const margen = margenPct(costoUnidad, precio)
              return (
                <div key={r.id} className="border rounded-lg p-4 bg-white shadow-sm">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {prod?.image_url ? (
                        <img src={prod.image_url} alt={prod.name} className="w-10 h-10 rounded object-cover bg-gray-100" />
                      ) : (
                        <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center text-gray-500 text-sm">
                          {(r.product_name || 'P').charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <div className="text-sm text-gray-500">{r.product_name || 'Product'}</div>
                        <div className="font-semibold text-gray-900">{r.name}</div>
                      </div>
                    </div>
                    <span className="text-xs inline-flex items-center px-2 py-1 rounded bg-amber-100 text-amber-800">
                      Producción
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">Costo total</div>
                      <div className="font-semibold">{fmt(r.total_cost || costoUnidad * (r.yield_qty || 1))}</div>
                    </div>
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">Rendimiento</div>
                      <div className="font-semibold">{r.yield_qty} und</div>
                    </div>
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">Costo / unidad</div>
                      <div className="font-semibold">{fmt(costoUnidad, 3)}</div>
                    </div>
                    <div className="p-2 rounded bg-gray-50">
                      <div className="text-gray-500">Precio sugerido {priceIncludesTax ? '(IVA inc.)' : '(sin IVA)'}
                      </div>
                      <div className="font-semibold">{fmt(precioDisplay)}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <div className="text-xs text-gray-600 flex items-center gap-2">
                      {prod?.category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-700">{prod.category}</span>
                      )}
                      <span>Markup {((multiplier - 1) * 100).toFixed(0)}% · Margen {margen.toFixed(0)}%</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="text-blue-600 hover:underline text-sm"
                        onClick={() => navigate(`${basePath}/recetas/${r.id}`)}
                      >
                        Ver
                      </button>
                      <button
                        className="text-gray-700 hover:underline text-sm"
                        onClick={() => navigate(`${basePath}/recetas/${r.id}/editar`)}
                      >
                        Editar
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <div>
              Mostrando {Math.min((page - 1) * perPage + 1, filtered.length)}–{Math.min(page * perPage, filtered.length)} de {filtered.length}
            </div>
            <div className="flex items-center gap-2">
              <button disabled={page <= 1} className="px-2 py-1 border rounded disabled:opacity-50" onClick={() => setPage(p => Math.max(1, p - 1))}>Anterior</button>
              <span>Pagina {page} / {totalPages}</span>
              <button disabled={page >= totalPages} className="px-2 py-1 border rounded disabled:opacity-50" onClick={() => setPage(p => Math.min(totalPages, p + 1))}>Siguiente</button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
