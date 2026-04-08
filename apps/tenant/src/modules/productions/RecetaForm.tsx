/**
 * RecetaForm - Formulario de creación/edición de recetas
 */

import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  createRecipe, updateRecipe, type Recipe, type RecipeIngredient
} from '../../services/api/recetas'
import { createProduct, listProducts, type Product } from '../../services/api/products'
import { normalizeUnitCode } from '../../services/unitService'
import { useUnits } from '../../hooks/useUnits'

interface RecetaFormProps {
  open: boolean
  recipe?: Recipe | null
  onClose: () => void
}

const getRecipeRequestErrorMessage = (err: any): string => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item: any) => {
        const loc = Array.isArray(item?.loc)
          ? item.loc.filter((part: string) => part !== 'body').join('.')
          : 'payload'
        return `${loc || 'payload'}: ${item?.msg || 'valor invalido'}`
      })
      .join('; ')
  }
  return err?.message || 'Error saving recipe'
}

export default function RecetaForm({ recipe, onClose }: RecetaFormProps) {
  const { t } = useTranslation(['productions', 'common'])
  const { units } = useUnits()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [productsLoaded, setProductsLoaded] = useState(false)

  // Datos de receta
  const [name, setName] = useState('')
  const [productId, setProductId] = useState<string | null>(null)
  const [productInputValue, setProductInputValue] = useState('')
  const [yieldQty, setYieldQty] = useState<number>(1)
  const [prepTimeMinutes, setPrepTimeMinutes] = useState<number | null>(null)
  const [instructions, setInstructions] = useState('')

  // Tiempos y producción
  const [bakingTimeMinutes, setBakingTimeMinutes] = useState<number | null>(null)
  const [ovenTempCelsius, setOvenTempCelsius] = useState<number | null>(null)
  const [restTimeMinutes, setRestTimeMinutes] = useState<number | null>(null)
  const [touchMinutesStandard, setTouchMinutesStandard] = useState<number | null>(null)
  const [wastePct, setWastePct] = useState<number | null>(null)
  const [traysPerBatch, setTraysPerBatch] = useState<number | null>(null)
  const [unitsPerTray, setUnitsPerTray] = useState<number | null>(null)

  // Ingredientes
  const [ingredientes, setIngredientes] = useState<RecipeIngredient[]>([])

  useEffect(() => {
    loadProducts()
  }, [])

  useEffect(() => {
    if (recipe) {
      setName(recipe.name)
      setProductId(recipe.product_id)
      setProductInputValue(recipe.product_name || recipe.name || '')
      setYieldQty(recipe.yield_qty)
      setPrepTimeMinutes(recipe.prep_time_minutes || null)
      setInstructions(recipe.instructions || '')
      setBakingTimeMinutes((recipe as any).baking_time_minutes ?? null)
      setOvenTempCelsius((recipe as any).oven_temp_celsius ?? null)
      setRestTimeMinutes((recipe as any).rest_time_minutes ?? null)
      setTouchMinutesStandard((recipe as any).touch_minutes_standard ?? null)
      setWastePct((recipe as any).waste_pct ?? null)
      setTraysPerBatch((recipe as any).trays_per_batch ?? null)
      setUnitsPerTray((recipe as any).units_per_tray ?? null)

      if (recipe.ingredients) {
        setIngredientes(recipe.ingredients.map(ing => ({
          product_id: ing.product_id,
          qty: ing.qty,
          unit: normalizeUnitCode(ing.unit, units),
          purchase_packaging: ing.purchase_packaging ?? '',
          qty_per_package: ing.qty_per_package ?? 1,
          package_unit: normalizeUnitCode(ing.package_unit, units),
          package_cost: ing.package_cost ?? 0,
          notes: ing.notes,
          line_order: ing.line_order || 0
        })))
      }
    }
  }, [recipe])

  useEffect(() => {
    if (!recipe) {
      const pid = searchParams.get('productId')
      if (pid) setProductId(pid)
    }
  }, [recipe, searchParams])

  useEffect(() => {
    if (!productId) return
    const selectedProduct = products.find((p) => p.id === productId)
    if (selectedProduct) {
      setProductInputValue(selectedProduct.name)
    }
  }, [productId, products])

  const loadProducts = async () => {
    try {
      const data = await listProducts({ limit: 500 })
      setProducts(data)
    } catch (err: any) {
      console.error('Error cargando productos:', err)
    } finally {
      setProductsLoaded(true)
    }
  }

  const handleAddIngredient = () => {
    setIngredientes(prev => [
      ...prev,
      {
        product_id: '',
        qty: 0,
        unit: 'kg',
        purchase_packaging: '',
        qty_per_package: 1,
        package_unit: 'kg',
        package_cost: 0,
        line_order: prev.length
      }
    ])
  }

  const handleRemoveIngredient = (index: number) => {
    setIngredientes(prev => prev.filter((_, i) => i !== index))
  }

  const handleIngredientChange = (index: number, field: string, value: any) => {
    setIngredientes(prev => {
      const updated = [...prev]
      const normalizedValue =
        field === 'unit' || field === 'package_unit'
          ? normalizeUnitCode(value, units)
          : value
      ;(updated[index] as any)[field] = normalizedValue

      if (field === 'product_id' && value) {
        const producto = products.find(p => p.id === value)
        if (producto) {
          updated[index].unit = normalizeUnitCode(producto.unit, units)
          updated[index].package_unit = normalizeUnitCode(producto.unit, units)

          const defaultPresentaciones: Record<string, { qty: number; desc: string }> = {
            'kg': { qty: 50, desc: 'Saco 50 kg' },
            'lb': { qty: 50, desc: 'Saco 50 lb' },
            'g': { qty: 1000, desc: 'Bolsa 1 kg' },
            'oz': { qty: 16, desc: 'Libra (16 oz)' },
            'L': { qty: 20, desc: 'Bidón 20 L' },
            'uds': { qty: 24, desc: t('productions:recipeForm.box24Units') }
          }

          const unit = normalizeUnitCode(producto.unit, units)
          const defaultPres = defaultPresentaciones[unit] || { qty: 1, desc: t('productions:recipeForm.unit') }

          updated[index].qty_per_package = defaultPres.qty
          updated[index].purchase_packaging = defaultPres.desc
          updated[index].package_cost = producto.cost_price
            ? Number(producto.cost_price) * defaultPres.qty
            : 0
        }
      }

      return updated
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const trimmedProductName = productInputValue.trim()

    if (!productId && !trimmedProductName) {
      setError('Debes seleccionar o crear un producto final')
      return
    }

    if (yieldQty <= 0) {
      setError('El rendimiento debe ser mayor a 0')
      return
    }

    try {
      setLoading(true)
      setError(null)
      let resolvedProductId = productId

      if (!resolvedProductId && trimmedProductName) {
        const existingProduct = products.find(
          (p) => p.name.trim().toLowerCase() === trimmedProductName.toLowerCase()
        )
        if (existingProduct) {
          resolvedProductId = existingProduct.id
        } else {
          const createdProduct = await createProduct({
            name: trimmedProductName,
            price: 0,
            stock: 0,
            unit: 'uds',
            tax_rate: 0,
            active: true,
          })
          resolvedProductId = createdProduct.id
          setProducts(prev =>
            [...prev, createdProduct].sort((a, b) => a.name.localeCompare(b.name))
          )
        }
      }

      if (!resolvedProductId) {
        setError('Debes seleccionar o crear un producto final')
        return
      }

      setProductId(resolvedProductId)

      if (traysPerBatch != null && traysPerBatch < 1) {
        setError('Bandejas por lote debe ser 1 o mayor')
        return
      }

      if (unitsPerTray != null && unitsPerTray < 1) {
        setError('Unidades por bandeja debe ser 1 o mayor')
        return
      }

      const normalizedIngredients = ingredientes
        .filter((ing) => ing.product_id && Number(ing.qty || 0) > 0)
        .map((ing, index) => ({
          product_id: ing.product_id,
          qty: Number(ing.qty || 0),
          unit: normalizeUnitCode(ing.unit, units),
          purchase_packaging: String(ing.purchase_packaging || '-'),
          qty_per_package: Math.max(Number(ing.qty_per_package || 1), 0.0001),
          package_unit: normalizeUnitCode(ing.package_unit || ing.unit, units),
          package_cost: Number(ing.package_cost || 0),
          notes: ing.notes || undefined,
          line_order: index,
        }))

      const seenProducts = new Set<string>()
      for (const ingredient of normalizedIngredients) {
        if (seenProducts.has(ingredient.product_id)) {
          const productName = products.find((p) => p.id === ingredient.product_id)?.name
          setError(
            productName
              ? `El ingrediente ${productName} ya existe en la receta.`
              : 'El ingrediente ya existe en la receta.'
          )
          return
        }
        seenProducts.add(ingredient.product_id)
      }

      const data = {
        name: name.trim(),
        product_id: resolvedProductId,
        yield_qty: yieldQty,
        prep_time_minutes: prepTimeMinutes ?? undefined,
        baking_time_minutes: bakingTimeMinutes ?? undefined,
        oven_temp_celsius: ovenTempCelsius ?? undefined,
        rest_time_minutes: restTimeMinutes ?? undefined,
        touch_minutes_standard: touchMinutesStandard ?? undefined,
        oven_minutes_standard: undefined,
        process_minutes: Math.max((prepTimeMinutes || 0) - (touchMinutesStandard || 0), 0) || undefined,
        waste_pct: wastePct ?? undefined,
        trays_per_batch: traysPerBatch && traysPerBatch >= 1 ? traysPerBatch : undefined,
        units_per_tray: unitsPerTray && unitsPerTray >= 1 ? unitsPerTray : undefined,
        instructions: instructions.trim() || undefined,
        ingredients: normalizedIngredients,
      }

      if (recipe) {
        await updateRecipe(recipe.id, data)
      } else {
        await createRecipe(data)
      }

      onClose()
    } catch (err: any) {
      setError(getRecipeRequestErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (!productsLoaded) {
    return (
      <div className="gc-container py-6 max-w-4xl">
        <p className="gc-page-header__subtitle">Cargando productos...</p>
      </div>
    )
  }

  const passiveMinutes = Math.max((prepTimeMinutes || 0) - (touchMinutesStandard || 0), 0)

  return (
    <div className="gc-container py-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="gc-page-header__title">
          {recipe ? t('productions:recipeForm.editRecipe') : t('productions:recipeForm.newRecipe')}
        </h1>
        <p className="gc-page-header__subtitle mt-1">
          Define producto, rendimiento e ingredientes con una estructura más clara.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg border text-sm" style={{ background: 'color-mix(in srgb, var(--gc-destructive) 8%, transparent)', borderColor: 'color-mix(in srgb, var(--gc-destructive) 30%, transparent)', color: 'var(--gc-destructive)' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Base de la receta */}
        <fieldset className="gc-card">
          <legend className="gc-section-title px-2">{t('productions:recipeForm.baseRecipe', 'Base de la receta')}</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            <div className="md:col-span-2">
              <label className="gc-label">{t('productions:recipeForm.recipeName')} *</label>
              <input
                type="text"
                className="gc-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <div>
              <label className="gc-label">{t('productions:recipeForm.finalProduct')} *</label>
              <input
                type="text"
                list="receta-products-list"
                className="gc-input"
                value={productInputValue}
                onChange={(e) => {
                  setProductInputValue(e.target.value)
                  const matched = products.find(
                    (p) => p.name.trim().toLowerCase() === e.target.value.trim().toLowerCase()
                  )
                  setProductId(matched?.id || null)
                }}
                placeholder="Selecciona o escribe un producto nuevo"
                required
                disabled={loading}
              />
              <datalist id="receta-products-list">
                {products.map((p) => (
                  <option key={p.id} value={p.name} />
                ))}
              </datalist>
              <p className="gc-field-hint">Si no existe, escríbelo y se creará al guardar.</p>
            </div>

            <div>
              <label className="gc-label">Rendimiento (uds) *</label>
              <input
                type="number"
                className="gc-input"
                value={yieldQty}
                onChange={(e) => setYieldQty(Number(e.target.value))}
                min={1}
                required
                disabled={loading}
              />
            </div>

            <div className="md:col-span-2">
              <label className="gc-label">Instrucciones</label>
              <textarea
                className="gc-input"
                rows={3}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>
        </fieldset>

        {/* Tiempos y Producción */}
        <fieldset className="gc-card">
          <legend className="gc-section-title px-2">{t('productions:recipeForm.timesProduction', 'Tiempos y Producción')}</legend>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
            <div>
              <label className="gc-label">Preparación (min)</label>
              <input
                type="number"
                className="gc-input"
                value={prepTimeMinutes ?? ''}
                onChange={(e) => setPrepTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                min={0}
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">Horneado (min)</label>
              <input
                type="number"
                className="gc-input"
                value={bakingTimeMinutes ?? ''}
                onChange={(e) => setBakingTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                min={0}
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">Temperatura horno °C</label>
              <input
                type="number"
                className="gc-input"
                value={ovenTempCelsius ?? ''}
                onChange={(e) => setOvenTempCelsius(e.target.value ? Number(e.target.value) : null)}
                min={0}
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">Reposo/Fermentación (min)</label>
              <input
                type="number"
                className="gc-input"
                value={restTimeMinutes ?? ''}
                onChange={(e) => setRestTimeMinutes(e.target.value ? Number(e.target.value) : null)}
                min={0}
                disabled={loading}
              />
            </div>
          </div>

          <div className="my-4 p-3 rounded-lg text-sm" style={{ background: 'color-mix(in srgb, var(--gc-primary) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--gc-primary) 20%, transparent)', color: 'var(--gc-foreground)' }}>
            🟢 Touch = trabajo activo (cuesta MO) | ⚫ Proceso = pasivo (fermentación/reposo)
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="gc-label">Trabajo activo min (TOUCH)</label>
              <input
                type="number"
                className="gc-input"
                value={touchMinutesStandard ?? ''}
                onChange={(e) => setTouchMinutesStandard(e.target.value ? Number(e.target.value) : null)}
                min={0}
                disabled={loading}
              />
              <p className="gc-field-hint">Pesar, amasar, bolear, cargar/descargar</p>
            </div>
            <div>
              <label className="gc-label">Proceso pasivo (min)</label>
              <input
                type="number"
                className="gc-input"
                value={passiveMinutes || ''}
                readOnly
                style={{ background: 'color-mix(in srgb, var(--gc-muted) 40%, transparent)' }}
              />
              <p className="gc-field-hint">{t('productions:recipeForm.autoHelperText', 'Calculado automáticamente')}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <div>
              <label className="gc-label">Merma %</label>
              <input
                type="number"
                className="gc-input"
                value={wastePct ?? ''}
                onChange={(e) => setWastePct(e.target.value ? Number(e.target.value) : null)}
                min={0}
                max={100}
                step={0.1}
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">Bandejas por lote</label>
              <input
                type="number"
                className="gc-input"
                value={traysPerBatch ?? ''}
                onChange={(e) => setTraysPerBatch(e.target.value ? Number(e.target.value) : null)}
                min={1}
                step={1}
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('productions:recipeForm.unitsPerTray', 'Uds por bandeja')}</label>
              <input
                type="number"
                className="gc-input"
                value={unitsPerTray ?? ''}
                onChange={(e) => setUnitsPerTray(e.target.value ? Number(e.target.value) : null)}
                min={1}
                step={1}
                disabled={loading}
              />
            </div>
          </div>
        </fieldset>

        {/* Ingredientes */}
        <fieldset className="gc-card">
          <div className="flex items-center justify-between">
            <legend className="gc-section-title px-2">Ingredientes</legend>
            <button
              type="button"
              className="gc-btn gc-btn--soft"
              onClick={handleAddIngredient}
              disabled={loading}
            >
              + Agregar
            </button>
          </div>

          <div className="space-y-3 mt-3">
            {ingredientes.length === 0 && (
              <p className="text-sm py-2" style={{ color: 'var(--gc-muted-foreground)' }}>
                Sin ingredientes. Haz clic en "+ Agregar" para comenzar.
              </p>
            )}
            {ingredientes.map((ing, index) => (
              <div
                key={index}
                className="p-3 rounded-lg space-y-2"
                style={{
                  background: 'color-mix(in srgb, var(--gc-muted) 30%, transparent)',
                  border: '1px solid var(--gc-border)',
                }}
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 items-end">
                <div>
                  <label className="gc-label">Producto</label>
                  <select
                    className="gc-input"
                    value={ing.product_id}
                    onChange={(e) => handleIngredientChange(index, 'product_id', e.target.value)}
                    disabled={loading}
                  >
                    <option value="">— Seleccionar —</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="gc-label">Cantidad</label>
                  <input
                    type="number"
                    className="gc-input"
                    value={ing.qty}
                    onChange={(e) => handleIngredientChange(index, 'qty', Number(e.target.value))}
                    min={0}
                    step="any"
                    disabled={loading}
                  />
                </div>

                <div>
                  <label className="gc-label">{t('productions:recipeForm.unit', 'Unidad')}</label>
                  <select
                    className="gc-input"
                    value={normalizeUnitCode(ing.unit, units)}
                    onChange={(e) => handleIngredientChange(index, 'unit', e.target.value)}
                    disabled={loading}
                  >
                    {units.map((u) => (
                      <option key={u.code} value={u.code}>{u.label}</option>
                    ))}
                  </select>
                </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => handleRemoveIngredient(index)}
                    className="gc-btn gc-btn--ghost"
                    style={{ color: 'var(--gc-destructive)', padding: '0.375rem' }}
                    title="Eliminar ingrediente"
                    disabled={loading}
                  >
                    🗑
                  </button>
                </div>
              </div>
            ))}
          </div>
        </fieldset>

        <div className="flex gap-3">
          <button type="submit" className="gc-btn gc-btn--primary" disabled={loading}>
            {loading ? t('common:saving', 'Guardando...') : t('common:save', 'Guardar')}
          </button>
          <button
            type="button"
            className="gc-btn gc-btn--ghost"
            onClick={onClose}
            disabled={loading}
          >
            {t('common:cancel', 'Cancelar')}
          </button>
        </div>
      </form>
    </div>
  )
}
