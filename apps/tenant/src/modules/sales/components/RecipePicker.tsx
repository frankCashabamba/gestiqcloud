import React, { useEffect, useState } from 'react'
import { listRecipes, type Recipe } from '../../productions/services'
import { listProductos, type Producto } from '../../products/productsApi'
import type { VentaLinea } from '../services'

let _recipes: Recipe[] | null = null
let _products: Record<string, Producto> | null = null
let _promise: Promise<void> | null = null

async function loadData() {
  if (_recipes && _products) return
  if (!_promise) {
    _promise = Promise.all([listRecipes(), listProductos()])
      .then(([recipes, products]) => {
        _recipes = recipes
        _products = Object.fromEntries(products.map(p => [p.id, p]))
      })
      .catch(() => { _promise = null })
  }
  return _promise
}

interface Props {
  onAdd: (linea: Omit<VentaLinea, never>) => void
  onClose: () => void
  currentLines: VentaLinea[]
}

export default function RecipePicker({ onAdd, onClose, currentLines }: Props) {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [products, setProducts] = useState<Record<string, Producto>>({})
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [added, setAdded] = useState<Record<string, number>>({}) // recipeId → count added

  useEffect(() => {
    loadData().then(() => {
      setRecipes(_recipes || [])
      setProducts(_products || {})
      setLoading(false)
    })
    // Pre-cargar counts desde las líneas actuales
    const counts: Record<string, number> = {}
    currentLines.forEach(l => {
      if (l.producto_id) counts[String(l.producto_id)] = (counts[String(l.producto_id)] || 0) + (l.cantidad || 1)
    })
    setAdded(counts)
  }, [])

  const filtered = q.trim()
    ? recipes.filter(r => r.name.toLowerCase().includes(q.toLowerCase()))
    : recipes

  function handleSelect(r: Recipe) {
    const product = products[r.product_id]
    onAdd({
      producto_id: r.product_id,
      producto_nombre: r.name,
      cantidad: 1,
      precio_unitario: product?.price ?? 0,
      impuesto_tasa: product?.tax_rate != null ? Number(product.tax_rate) : 0,
      descuento: 0,
    })
    setAdded(prev => ({ ...prev, [r.product_id]: (prev[r.product_id] || 0) + 1 }))
  }

  return (
    <div className="border rounded-lg bg-white shadow-sm mb-3">
      <div className="flex justify-between items-center px-3 py-2 border-b bg-slate-50 rounded-t-lg">
        <span className="text-sm font-semibold text-slate-700">Seleccionar recetas</span>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg leading-none">✕</button>
      </div>

      <div className="p-3">
        <input
          autoFocus
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Buscar receta..."
          className="gc-input w-full mb-2"
        />

        {loading && <p className="text-sm text-slate-500 py-2">Cargando recetas…</p>}

        <div className="divide-y max-h-64 overflow-y-auto rounded border">
          {!loading && filtered.length === 0 && (
            <p className="text-sm text-slate-500 px-3 py-3">Sin resultados</p>
          )}
          {filtered.map(r => {
            const product = products[r.product_id]
            const count = added[r.product_id] || 0
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => handleSelect(r)}
                className="w-full text-left px-3 py-2.5 hover:bg-blue-50 flex items-center justify-between gap-3 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium block">{r.name}</span>
                  {r.rendimiento > 1 && (
                    <span className="text-xs text-slate-400">rinde {r.rendimiento} uds.</span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {product?.price != null && (
                    <span className="text-sm font-semibold text-blue-700">
                      ${Number(product.price).toFixed(2)}
                    </span>
                  )}
                  {count > 0 && (
                    <span className="bg-blue-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                      {count}
                    </span>
                  )}
                  <span className="text-blue-500 text-lg font-bold">+</span>
                </div>
              </button>
            )
          })}
        </div>

        <p className="text-xs text-slate-400 mt-2">
          Haz clic en una receta para agregar la línea. Puedes agregar varias.
        </p>
      </div>
    </div>
  )
}
