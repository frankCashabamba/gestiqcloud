import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import { listRecipes, addIngredient, updateIngredient, deleteIngredient } from '../../services/api/recetas'
import { listProducts, createProduct, updateProduct, type Product } from '../../services/api/products'
import { getCompanySettings, getCurrencySymbol, type CompanySettings } from '../../services/companySettings'
import { useUnits } from '../../hooks/useUnits'
import { normalizeUnitCode } from '../../services/unitService'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'
import { useToast } from '../../shared/toast'

interface IngredientRef {
  recipe_id: string
  ingredient_id: string
  recipe_name: string
  qty: number
  unit: string
}

interface IngredienteRow {
  product_id: string
  product_name: string
  inventory_product?: Product
  unit: string
  purchase_packaging: string
  qty_per_package: number
  package_unit: string
  package_cost: number
  refs: IngredientRef[]
  hasDivergence: boolean
}

type DraftMap = Record<string, {
  purchase_packaging: string
  qty_per_package: number
  package_unit: string
  package_cost: number
}>

export default function IngredientesMaestros() {
  return (
    <ProductionAvailabilityGuard>
      <IngredientesMaestrosContent />
    </ProductionAvailabilityGuard>
  )
}

function IngredientesMaestrosContent() {
  const navigate = useNavigate()
  const { success, error: toastError } = useToast()
  const { units } = useUnits()

  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [rows, setRows] = useState<IngredienteRow[]>([])
  const [allProducts, setAllProducts] = useState<Product[]>([])
  const [recipesList, setRecipesList] = useState<Array<{ id: string; name: string }>>([])
  const [settings, setSettings] = useState<CompanySettings | null>(null)
  const [q, setQ] = useState('')
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null)
  const [drafts, setDrafts] = useState<DraftMap>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [deleteConfirm, setDeleteConfirm] = useState<IngredienteRow | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [newIngOpen, setNewIngOpen] = useState(false)
  const [reload, setReload] = useState(0)
  const [editingNameId, setEditingNameId] = useState<string | null>(null)
  const [editingNameValue, setEditingNameValue] = useState('')
  const [savingName, setSavingName] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        setErr(null)
        const [recipeList, productArr, cfg] = await Promise.all([
          listRecipes({ limit: 500, include_ingredients: true }),
          listProducts({ limit: 500 }),
          getCompanySettings(),
        ])
        if (cancelled) return

        const recipes = Array.isArray(recipeList) ? recipeList : []
        const products = Array.isArray(productArr) ? productArr : []
        setProgress({ done: recipes.length, total: recipes.length })
        setAllProducts(products)
        setRecipesList(recipes.map(r => ({ id: r.id, name: r.name })))

        if (cancelled) return

        setSettings(cfg)
        setProgress(null)

        const productMap = new Map<string, Product>()
        for (const p of products) productMap.set(p.id, p)

        const map = new Map<string, {
          product_name: string; inventory_product?: Product; unit: string
          firstValues: { purchase_packaging: string; qty_per_package: number; package_unit: string; package_cost: number }
          refs: IngredientRef[]; hasDivergence: boolean
        }>()

        for (const recipe of recipes) {
          for (const ing of (recipe.ingredients || [])) {
            const invProd = productMap.get(ing.product_id)
            const productName = ing.product_name || invProd?.name || ing.product_id
            const ingValues = {
              purchase_packaging: ing.purchase_packaging ?? '',
              qty_per_package: ing.qty_per_package ?? 1,
              package_unit: ing.package_unit ?? ing.unit,
              package_cost: ing.package_cost ?? 0,
            }
            if (!map.has(ing.product_id)) {
              map.set(ing.product_id, { product_name: productName, inventory_product: invProd, unit: ing.unit, firstValues: ingValues, refs: [], hasDivergence: false })
            }
            const entry = map.get(ing.product_id)!
            const fv = entry.firstValues
            if (fv.purchase_packaging !== ingValues.purchase_packaging || fv.qty_per_package !== ingValues.qty_per_package || fv.package_cost !== ingValues.package_cost) {
              entry.hasDivergence = true
            }
            entry.refs.push({ recipe_id: recipe.id, ingredient_id: (ing as any).id ?? '', recipe_name: recipe.name, qty: ing.qty, unit: ing.unit })
          }
        }

        const built: IngredienteRow[] = []
        for (const [pid, entry] of map.entries()) {
          built.push({ product_id: pid, product_name: entry.product_name, inventory_product: entry.inventory_product, unit: entry.unit, ...entry.firstValues, refs: entry.refs, hasDivergence: entry.hasDivergence })
        }
        built.sort((a, b) => a.product_name.localeCompare(b.product_name))
        setRows(built)
      } catch (e: any) {
        if (!cancelled) setErr(e?.message || 'Error cargando ingredientes')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [reload])

  const currency = useMemo(() => getCurrencySymbol(settings || undefined), [settings])
  const fmt = (n: number, d = 2) => `${currency}${Number(n || 0).toFixed(d)}`

  const totalRecipes = useMemo(() => {
    const ids = new Set<string>()
    rows.forEach(r => r.refs.forEach(ref => ids.add(ref.recipe_id)))
    return ids.size
  }, [rows])

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase()
    if (!term) return rows
    return rows.filter(r =>
      r.product_name.toLowerCase().includes(term) ||
      r.purchase_packaging.toLowerCase().includes(term) ||
      r.refs.some(re => re.recipe_name.toLowerCase().includes(term))
    )
  }, [rows, q])

  const startEdit = (row: IngredienteRow) => {
    setDrafts(prev => ({
      ...prev,
      [row.product_id]: { purchase_packaging: row.purchase_packaging, qty_per_package: row.qty_per_package, package_unit: row.package_unit, package_cost: row.package_cost },
    }))
  }

  const cancelEdit = (pid: string) => setDrafts(prev => { const n = { ...prev }; delete n[pid]; return n })

  const saveName = async (row: IngredienteRow) => {
    const newName = editingNameValue.trim()
    if (!newName || newName === row.product_name) { setEditingNameId(null); return }
    setSavingName(true)
    try {
      await updateProduct(row.product_id, { name: newName })
      setRows(prev => prev.map(r => r.product_id === row.product_id ? { ...r, product_name: newName } : r))
      success(`Nombre actualizado: ${newName}`)
    } catch (e: any) {
      toastError(e?.message || 'Error al actualizar nombre')
    } finally {
      setSavingName(false)
      setEditingNameId(null)
    }
  }

  const setField = (pid: string, field: string, value: any) =>
    setDrafts(prev => ({ ...prev, [pid]: { ...prev[pid], [field]: value } }))

  const save = async (row: IngredienteRow) => {
    const draft = drafts[row.product_id]
    if (!draft) return
    if (draft.qty_per_package <= 0) { toastError('El contenido debe ser mayor que 0'); return }
    setSaving(prev => ({ ...prev, [row.product_id]: true }))
    try {
      await Promise.all(
        row.refs.filter(r => r.ingredient_id).map(ref =>
          updateIngredient(ref.recipe_id, ref.ingredient_id, {
            purchase_packaging: draft.purchase_packaging,
            qty_per_package: draft.qty_per_package,
            package_unit: normalizeUnitCode(draft.package_unit, units),
            package_cost: draft.package_cost,
          })
        )
      )
      setRows(prev => prev.map(r => r.product_id === row.product_id ? { ...r, ...draft, hasDivergence: false } : r))
      cancelEdit(row.product_id)
      success(`Actualizado en ${row.refs.length} receta${row.refs.length !== 1 ? 's' : ''}`)
    } catch (e: any) {
      toastError(e?.message || 'Error al guardar')
    } finally {
      setSaving(prev => { const n = { ...prev }; delete n[row.product_id]; return n })
    }
  }

  const confirmDelete = async () => {
    if (!deleteConfirm) return
    setDeleting(true)
    try {
      await Promise.all(
        deleteConfirm.refs.filter(r => r.ingredient_id).map(ref =>
          deleteIngredient(ref.recipe_id, ref.ingredient_id)
        )
      )
      setRows(prev => prev.filter(r => r.product_id !== deleteConfirm.product_id))
      setDeleteConfirm(null)
      success(`${deleteConfirm.product_name} eliminado de ${deleteConfirm.refs.length} receta${deleteConfirm.refs.length !== 1 ? 's' : ''}`)
    } catch (e: any) {
      toastError(e?.message || 'Error al eliminar')
    } finally {
      setDeleting(false)
    }
  }

  if (loading) return (
    <div className="p-8 flex flex-col items-center justify-center gap-3 text-gray-400">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <div className="text-sm">Cargando ingredientes…</div>
      {progress && <div className="text-xs">{progress.done} / {progress.total} recetas</div>}
    </div>
  )
  if (err) return <div className="p-6 text-red-600">{err}</div>

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => navigate(-1)} /></div>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ingredientes Maestros</h1>
          <p className="text-sm text-gray-500 mt-1">
            <span className="font-medium text-gray-700">{rows.length}</span> ingredientes ·{' '}
            <span className="font-medium text-gray-700">{totalRecipes}</span> recetas
          </p>
          <div className="mt-2 inline-flex items-center gap-1.5 text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Cambiar el precio aquí lo actualiza en todas las recetas automáticamente
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <input
              type="search"
              className="border rounded-lg pl-9 pr-3 py-2 w-56 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Buscar ingrediente…"
              value={q}
              onChange={e => setQ(e.target.value)}
            />
          </div>
          <button
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-sm"
            onClick={() => setNewIngOpen(true)}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" /></svg>
            Nuevo ingrediente
          </button>
          <button
            className="flex items-center gap-1.5 border border-gray-200 hover:bg-gray-50 text-gray-600 px-3 py-2 rounded-lg text-sm transition-colors"
            onClick={() => navigate('../recetas')}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Recetas
          </button>
        </div>
      </div>

      {/* Divergence banner */}
      {rows.some(r => r.hasDivergence) && (
        <div className="mb-4 flex items-start gap-2 bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 text-sm text-orange-700">
          <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          <span>Algunos ingredientes tienen precios distintos entre recetas. Edítalos y guarda para unificar los valores.</span>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="p-12 text-center text-gray-400 border-2 border-dashed rounded-xl">
          {rows.length === 0 ? 'No hay ingredientes en las recetas.' : 'Sin resultados para la búsqueda.'}
        </div>
      ) : (
        <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-52">Ingrediente</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Empaque</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Contenido</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Costo pack</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Costo / unidad</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Recetas que lo usan</th>
                <th className="px-4 py-3 w-28"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(row => {
                const draft = drafts[row.product_id]
                const isSaving = !!saving[row.product_id]
                const cur = draft ?? row
                const costPerUnit = cur.qty_per_package > 0 ? cur.package_cost / cur.qty_per_package : 0
                const isEditing = !!draft

                return (
                  <tr
                    key={row.product_id}
                    className={isEditing ? 'bg-blue-50 ring-1 ring-inset ring-blue-200' : 'hover:bg-gray-50 transition-colors'}
                  >
                    {/* Ingrediente */}
                    <td className="px-4 py-3 align-top">
                      {editingNameId === row.product_id ? (
                        <input
                          autoFocus
                          className="border border-blue-300 rounded-md px-2 py-1 text-sm font-semibold text-gray-900 w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
                          value={editingNameValue}
                          disabled={savingName}
                          onChange={e => setEditingNameValue(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter') saveName(row)
                            else if (e.key === 'Escape') setEditingNameId(null)
                          }}
                          onBlur={() => saveName(row)}
                        />
                      ) : (
                        <EditableCell
                          value={row.product_name}
                          onClick={() => { setEditingNameId(row.product_id); setEditingNameValue(row.product_name) }}
                          strong
                        />
                      )}
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        {row.inventory_product ? (
                          <span className="inline-flex items-center gap-0.5 text-xs text-emerald-600">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
                            inventario · {row.inventory_product.unit || row.unit}
                          </span>
                        ) : (
                          <span className="text-xs text-amber-500">⚠ sin vincular</span>
                        )}
                        {row.hasDivergence && !isEditing && (
                          <span
                            className="inline-flex items-center gap-0.5 text-xs text-orange-500 cursor-help"
                            title="Precios distintos entre recetas. Edita y guarda para unificar."
                          >
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
                            precios distintos
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Empaque */}
                    <td className="px-4 py-3 align-middle">
                      {isEditing ? (
                        <input
                          autoFocus
                          className="border border-blue-300 rounded-md px-2.5 py-1.5 w-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                          value={draft.purchase_packaging}
                          onChange={e => setField(row.product_id, 'purchase_packaging', e.target.value)}
                          placeholder="ej: Saco 50 kg"
                        />
                      ) : (
                        <EditableCell value={row.purchase_packaging || '—'} onClick={() => startEdit(row)} />
                      )}
                    </td>

                    {/* Contenido */}
                    <td className="px-4 py-3 align-middle">
                      {isEditing ? (
                        <div className="flex items-center gap-1 justify-end">
                          <input
                            type="number"
                            className="border border-blue-300 rounded-md px-2 py-1.5 w-20 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-400"
                            value={draft.qty_per_package}
                            min={0.0001}
                            step={0.01}
                            onChange={e => setField(row.product_id, 'qty_per_package', Number(e.target.value))}
                          />
                          <select
                            className="border border-blue-300 rounded-md px-1 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                            value={normalizeUnitCode(draft.package_unit, units)}
                            onChange={e => setField(row.product_id, 'package_unit', e.target.value)}
                          >
                            {units.map(u => <option key={u.code} value={u.code}>{u.label}</option>)}
                          </select>
                        </div>
                      ) : (
                        <EditableCell
                          value={`${row.qty_per_package} ${row.package_unit}`}
                          onClick={() => startEdit(row)}
                          align="right"
                        />
                      )}
                    </td>

                    {/* Costo pack */}
                    <td className="px-4 py-3 align-middle">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1">
                          <span className="text-gray-400 text-sm">{currency}</span>
                          <input
                            type="number"
                            className="border border-blue-300 rounded-md px-2 py-1.5 w-28 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-400"
                            value={draft.package_cost}
                            min={0}
                            step={0.01}
                            onChange={e => setField(row.product_id, 'package_cost', Number(e.target.value))}
                          />
                        </div>
                      ) : (
                        <EditableCell
                          value={fmt(row.package_cost)}
                          onClick={() => startEdit(row)}
                          align="right"
                          strong
                        />
                      )}
                    </td>

                    {/* Costo / unidad */}
                    <td className="px-4 py-3 align-middle text-right whitespace-nowrap">
                      <span className="text-gray-700 font-medium">{fmt(costPerUnit, 4)}</span>
                      <span className="text-xs text-gray-400 ml-1">/ {cur.package_unit || row.unit}</span>
                    </td>

                    {/* Recetas */}
                    <td className="px-4 py-3 align-middle">
                      <div className="flex flex-wrap gap-1">
                        {row.refs.map(ref => (
                          <button
                            key={ref.ingredient_id || ref.recipe_id}
                            onClick={() => navigate(`../recetas/${ref.recipe_id}`)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs transition-colors"
                            title={`${ref.qty} ${ref.unit}`}
                          >
                            {ref.recipe_name}
                            <span className="text-slate-400 text-[10px]">{ref.qty}{ref.unit}</span>
                          </button>
                        ))}
                      </div>
                    </td>

                    {/* Acciones */}
                    <td className="px-4 py-3 align-middle">
                      {isEditing ? (
                        <div className="flex items-center gap-1 justify-end">
                          <button
                            disabled={isSaving}
                            onClick={() => save(row)}
                            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
                            title={`Guardar en ${row.refs.length} receta${row.refs.length !== 1 ? 's' : ''}`}
                          >
                            {isSaving ? (
                              <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin inline-block" />
                            ) : (
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                            )}
                            {isSaving ? '' : `${row.refs.length} receta${row.refs.length !== 1 ? 's' : ''}`}
                          </button>
                          <button
                            disabled={isSaving}
                            onClick={() => cancelEdit(row.product_id)}
                            className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-100 text-gray-500 transition-colors"
                            title="Cancelar"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" /></svg>
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 justify-end">
                          <button
                            onClick={() => startEdit(row)}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-gray-200 hover:border-blue-300 hover:text-blue-600 text-gray-500 text-xs transition-colors"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                            Editar
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(row)}
                            className="p-1.5 rounded-lg border border-gray-200 hover:border-red-300 hover:text-red-600 text-gray-400 transition-colors"
                            title="Eliminar de todas las recetas"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* New ingredient modal */}
      {newIngOpen && (
        <NewIngredientModal
          products={allProducts}
          recipes={recipesList}
          units={units}
          currency={currency}
          onClose={() => setNewIngOpen(false)}
          onSuccess={() => { setNewIngOpen(false); setReload(r => r + 1) }}
        />
      )}

      {/* Delete confirmation modal */}
      {deleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => !deleting && setDeleteConfirm(null)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base">Eliminar ingrediente</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  Se eliminará <span className="font-semibold text-gray-800">{deleteConfirm.product_name}</span> de{' '}
                  <span className="font-semibold">{deleteConfirm.refs.length} receta{deleteConfirm.refs.length !== 1 ? 's' : ''}</span>:
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {deleteConfirm.refs.map(r => (
                    <span key={r.recipe_id} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{r.recipe_name}</span>
                  ))}
                </div>
                <p className="text-xs text-red-600 mt-2">Esta acción no se puede deshacer.</p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                disabled={deleting}
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                disabled={deleting}
                onClick={confirmDelete}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
              >
                {deleting ? 'Eliminando…' : 'Sí, eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Modal: agregar nuevo ingrediente a recetas ────────────────────────────────
function NewIngredientModal({
  products,
  recipes,
  units,
  currency,
  onClose,
  onSuccess,
}: {
  products: Product[]
  recipes: Array<{ id: string; name: string }>
  units: Array<{ code: string; label: string }>
  currency: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [form, setForm] = useState({
    product_id: '',
    qty: 1,
    unit: 'kg',
    purchase_packaging: '',
    qty_per_package: 1,
    package_unit: 'kg',
    package_cost: 0,
  })
  const [productSearch, setProductSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedRecipes, setSelectedRecipes] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const filteredProducts = useMemo(() => {
    const q = productSearch.trim().toLowerCase()
    if (!q) return products.slice(0, 30)
    return products.filter(p => p.name.toLowerCase().includes(q)).slice(0, 30)
  }, [products, productSearch])

  const canCreateNew = useMemo(() => {
    const q = productSearch.trim().toLowerCase()
    if (!q) return false
    return !products.some(p => p.name.toLowerCase() === q)
  }, [products, productSearch])

  const selectProduct = (p: Product) => {
    setForm(f => ({ ...f, product_id: p.id, unit: p.unit || f.unit, package_unit: p.unit || f.package_unit }))
    setProductSearch(p.name)
    setShowDropdown(false)
  }

  const createAndSelect = async () => {
    const name = productSearch.trim()
    if (!name) return
    setErr(null)
    try {
      const created = await createProduct({ name, price: 0, stock: 0, unit: form.unit || 'kg', is_raw_material: true } as any)
      setForm(f => ({ ...f, product_id: created.id }))
      setProductSearch(created.name)
      setShowDropdown(false)
    } catch (e: any) {
      setErr(e?.message || 'Error al crear el producto')
    }
  }

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const toggleRecipe = (id: string) =>
    setSelectedRecipes(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const handleSubmit = async () => {
    if (!form.product_id && !productSearch.trim()) { setErr('Selecciona o escribe un producto'); return }
    if (selectedRecipes.size === 0) { setErr('Selecciona al menos una receta'); return }
    if (form.qty <= 0) { setErr('La cantidad debe ser mayor a 0'); return }
    setErr(null)
    setSaving(true)
    try {
      let productId = form.product_id
      if (!productId && productSearch.trim()) {
        const created = await createProduct({ name: productSearch.trim(), price: 0, stock: 0, unit: form.unit || 'kg', is_raw_material: true } as any)
        productId = created.id
      }
      await Promise.all(
        [...selectedRecipes].map(recipeId =>
          addIngredient(recipeId, {
            product_id: productId,
            qty: form.qty,
            unit: form.unit,
            purchase_packaging: form.purchase_packaging || '-',
            qty_per_package: Math.max(form.qty_per_package, 0.0001),
            package_unit: form.package_unit,
            package_cost: form.package_cost,
          })
        )
      )
      onSuccess()
    } catch (e: any) {
      setErr(e?.message || 'Error al agregar el ingrediente')
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={() => !saving && onClose()}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Nuevo ingrediente</h2>
            <p className="text-xs text-gray-500 mt-0.5">Agrega un producto a una o varias recetas</p>
          </div>
          <button onClick={onClose} disabled={saving} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {err && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            {err}
          </div>
        )}

        {/* Producto */}
        <div className="mb-4" ref={dropdownRef}>
          <label className="block text-xs font-semibold text-gray-600 mb-1.5">Producto / Ingrediente *</label>
          <div className="relative">
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              placeholder="Buscar o escribir nuevo producto..."
              value={productSearch}
              onChange={e => {
                setProductSearch(e.target.value)
                setForm(f => ({ ...f, product_id: '' }))
                setShowDropdown(true)
              }}
              onFocus={() => setShowDropdown(true)}
            />
            {form.product_id && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-emerald-500 text-xs">✓</span>
            )}
          </div>
          {showDropdown && (
            <div className="absolute z-10 mt-1 w-full max-w-[calc(100%-3rem)] bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {canCreateNew && (
                <button
                  type="button"
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors border-b border-blue-100"
                  onClick={createAndSelect}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" /></svg>
                  Crear "<span className="font-semibold">{productSearch.trim()}</span>" como materia prima
                </button>
              )}
              {filteredProducts.map(p => (
                <button
                  key={p.id}
                  type="button"
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${form.product_id === p.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'}`}
                  onClick={() => selectProduct(p)}
                >
                  {p.name}{p.unit ? <span className="text-gray-400 ml-1">({p.unit})</span> : ''}
                </button>
              ))}
              {filteredProducts.length === 0 && !canCreateNew && (
                <div className="px-3 py-3 text-sm text-gray-400 text-center">Sin resultados</div>
              )}
            </div>
          )}
        </div>

        {/* Cantidad + unidad en receta */}
        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">Cantidad en receta *</label>
            <input
              type="number"
              min={0.001}
              step={0.001}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.qty}
              onChange={e => setForm(f => ({ ...f, qty: Number(e.target.value) }))}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">Unidad</label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              value={form.unit}
              onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
            >
              {units.map(u => <option key={u.code} value={u.code}>{u.label}</option>)}
            </select>
          </div>
        </div>

        {/* Info de compra */}
        <div className="mb-4 p-3.5 bg-gray-50 rounded-xl border border-gray-200">
          <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">Info de compra (opcional)</p>
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-600 mb-1">Presentación / Empaque</label>
            <input
              type="text"
              placeholder="ej: Saco 50 kg, Caja 12 uds"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              value={form.purchase_packaging}
              onChange={e => setForm(f => ({ ...f, purchase_packaging: e.target.value }))}
            />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Contenido</label>
              <input
                type="number"
                min={0.0001}
                step={0.01}
                className="w-full border rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                value={form.qty_per_package}
                onChange={e => setForm(f => ({ ...f, qty_per_package: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Unidad</label>
              <select
                className="w-full border rounded-lg px-1 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                value={form.package_unit}
                onChange={e => setForm(f => ({ ...f, package_unit: e.target.value }))}
              >
                {units.map(u => <option key={u.code} value={u.code}>{u.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Costo pack ({currency})</label>
              <input
                type="number"
                min={0}
                step={0.01}
                className="w-full border rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                value={form.package_cost}
                onChange={e => setForm(f => ({ ...f, package_cost: Number(e.target.value) }))}
              />
            </div>
          </div>
        </div>

        {/* Selección de recetas */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-gray-600">Agregar a recetas *</label>
            <button
              type="button"
              className="text-xs text-blue-600 hover:underline"
              onClick={() =>
                setSelectedRecipes(
                  selectedRecipes.size === recipes.length
                    ? new Set()
                    : new Set(recipes.map(r => r.id))
                )
              }
            >
              {selectedRecipes.size === recipes.length ? 'Deseleccionar todas' : 'Seleccionar todas'}
            </button>
          </div>
          <div className="border rounded-xl overflow-hidden max-h-44 overflow-y-auto">
            {recipes.length === 0 ? (
              <div className="p-4 text-sm text-gray-400 text-center">No hay recetas disponibles</div>
            ) : (
              recipes.map((r, i) => (
                <label
                  key={r.id}
                  className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer hover:bg-blue-50 transition-colors ${i < recipes.length - 1 ? 'border-b border-gray-100' : ''} ${selectedRecipes.has(r.id) ? 'bg-blue-50' : ''}`}
                >
                  <input
                    type="checkbox"
                    className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                    checked={selectedRecipes.has(r.id)}
                    onChange={() => toggleRecipe(r.id)}
                  />
                  <span className="text-sm text-gray-700">{r.name}</span>
                </label>
              ))
            )}
          </div>
          {selectedRecipes.size > 0 && (
            <p className="text-xs text-blue-600 mt-1.5 font-medium">
              {selectedRecipes.size} receta{selectedRecipes.size !== 1 ? 's' : ''} seleccionada{selectedRecipes.size !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 justify-end pt-1 border-t border-gray-100">
          <button
            disabled={saving}
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            disabled={saving || !form.product_id || selectedRecipes.size === 0}
            onClick={handleSubmit}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold transition-colors flex items-center gap-2"
          >
            {saving ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
                Agregando…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" /></svg>
                Agregar a {selectedRecipes.size || ''} receta{selectedRecipes.size !== 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// Small helper: cell that shows a pencil icon on hover to indicate it's editable
function EditableCell({ value, onClick, align = 'left', strong = false }: {
  value: string; onClick: () => void; align?: 'left' | 'right'; strong?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex items-center gap-1.5 w-full rounded-md px-1.5 py-1 -mx-1.5 hover:bg-white hover:shadow-sm hover:ring-1 hover:ring-gray-200 transition-all ${align === 'right' ? 'justify-end' : 'justify-start'}`}
      title="Clic para editar"
    >
      <span className={strong ? 'font-semibold text-gray-900' : 'text-gray-700'}>{value}</span>
      <svg className="w-3 h-3 text-gray-300 group-hover:text-blue-400 flex-shrink-0 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
      </svg>
    </button>
  )
}
