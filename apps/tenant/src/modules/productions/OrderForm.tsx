import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { createProductionOrder, getProductionOrder, updateProductionOrder, type ProductionOrder } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'
import { getRecipe as getRecipeDetail, getCostBreakdown, listRecipes, type Recipe as ApiRecipe } from '../../services/api/recetas'
import { listProducts } from '../../services/api/products'
import { listWarehouses, type Warehouse } from '../inventory/services'
import { useTranslation } from 'react-i18next'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'

type FieldCfg = {
    field: string
    visible?: boolean
    required?: boolean
    ord?: number | null
    label?: string | null
    help?: string | null
}

export default function OrderForm() {
    return (
        <ProductionAvailabilityGuard>
            <OrderFormContent />
        </ProductionAvailabilityGuard>
    )
}

function OrderFormContent() {
    const { id, empresa } = useParams()
    const [search] = useSearchParams()
    const nav = useNavigate()
    const { t } = useTranslation(['productions', 'common'])

    const [form, setForm] = useState<Partial<Omit<ProductionOrder, 'id'>>>({
        qty_planned: 1,
        status: 'draft',
    })
    const { success, error } = useToast()
    const [fields, setFields] = useState<FieldCfg[] | null>(null)
    const [loadingCfg, setLoadingCfg] = useState(false)
    const [prefillLocked, setPrefillLocked] = useState(false)
    const [useRecipeDefaultQty, setUseRecipeDefaultQty] = useState(true)
    const [recipeSummary, setRecipeSummary] = useState<{
        name: string
        productName: string
        yieldQty: number
        totalCost: number
        unitCost: number
        suggestedPrice: number
    } | null>(null)
    const [selectedWarehouse, setSelectedWarehouse] = useState<Warehouse | null>(null)
    const [availableRecipes, setAvailableRecipes] = useState<ApiRecipe[]>([])
    const [loadingRecipes, setLoadingRecipes] = useState(false)
    const autoCreateDoneRef = useRef(false)

    useEffect(() => {
        if (!id) return
        getProductionOrder(id).then((x) => setForm({ ...x }))
    }, [id])

    useEffect(() => {
        if (id) return
        const recipeId = search.get('recipeId')
        const productId = search.get('productId')
        const qtyParam = Number(search.get('qty') || 0)
        if (recipeId || productId) {
            setForm((prev) => ({
                ...prev,
                ...(recipeId ? { recipe_id: recipeId } : {}),
                ...(productId ? { product_id: productId } : {}),
                ...(qtyParam > 0 ? { qty_planned: qtyParam } : {}),
            }))
            setPrefillLocked(true)
        }
    }, [id, search])

    useEffect(() => {
        if (id) return
        let cancelled = false
        ;(async () => {
            try {
                setLoadingRecipes(true)
                const recipes = await listRecipes({ limit: 500 })
                if (!cancelled) setAvailableRecipes(Array.isArray(recipes) ? recipes : [])
            } catch {
                if (!cancelled) setAvailableRecipes([])
            } finally {
                if (!cancelled) setLoadingRecipes(false)
            }
        })()
        return () => {
            cancelled = true
        }
    }, [id])

    useEffect(() => {
        if (id) return
        const recipeId = search.get('recipeId')
        if (!recipeId) return

        let cancelled = false
        ;(async () => {
            try {
                const [recipe, breakdown, products] = await Promise.all([
                    getRecipeDetail(recipeId),
                    getCostBreakdown(recipeId),
                    listProducts({ limit: 500 }),
                ])
                if (cancelled) return

                const yieldQty = Number(recipe.yield_qty || breakdown.rendimiento || 1)
                const qtyFromQuery = Number(search.get('qty') || 0)
                const plannedQty = qtyFromQuery > 0 ? qtyFromQuery : (yieldQty > 0 ? yieldQty : 1)
                const unitCost = Number(breakdown.costo_por_unidad || 0)
                const totalCost = Number(breakdown.costo_total || 0)
                const matchedProduct = Array.isArray(products)
                    ? products.find((p) => p.id === recipe.product_id)
                    : undefined
                const suggestedPrice = Number(matchedProduct?.price ?? unitCost * 2.5)

                setRecipeSummary({
                    name: String(recipe.name || ''),
                    productName: String(matchedProduct?.name || recipe.product_name || ''),
                    yieldQty,
                    totalCost,
                    unitCost,
                    suggestedPrice,
                })

                setUseRecipeDefaultQty(plannedQty === yieldQty)
                setForm((prev) => ({
                    ...prev,
                    recipe_id: recipe.id,
                    product_id: recipe.product_id,
                    qty_planned: plannedQty,
                }))
            } catch {
                // keep form usable even if prefill lookup fails
            }
        })()

        return () => {
            cancelled = true
        }
    }, [id, search])

    useEffect(() => {
        if (id) return
        let cancelled = false
        ;(async () => {
            try {
                const warehouses = await listWarehouses()
                if (cancelled || !Array.isArray(warehouses) || warehouses.length === 0) return
                const preferred = warehouses.find((w) => w.is_active) || warehouses[0]
                setSelectedWarehouse(preferred)
                setForm((prev) => ({
                    ...prev,
                    warehouse_id: prev.warehouse_id || String(preferred.id),
                }))
            } catch {
                // Keep create flow working even if warehouse lookup fails.
            }
        })()
        return () => {
            cancelled = true
        }
    }, [id])

    useEffect(() => {
        if (id) return
        if (form.scheduled_date) return
        setForm((prev) => ({ ...prev, scheduled_date: new Date().toISOString().slice(0, 10) }))
    }, [id, form.scheduled_date])

    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                setLoadingCfg(true)
                const q = new URLSearchParams({ module: 'production', ...(empresa ? { empresa } : {}) }).toString()
                const data = await apiFetch<{ items?: FieldCfg[] }>(`/api/v1/company/settings/fields?${q}`)
                if (!cancelled) setFields((data?.items || []).filter((it) => it.visible !== false))
            } catch {
                if (!cancelled) setFields(null)
            } finally {
                if (!cancelled) setLoadingCfg(false)
            }
        })()
        return () => {
            cancelled = true
        }
    }, [empresa])

    const fieldList = useMemo(() => {
        const base: FieldCfg[] = [
            { field: 'numero', visible: true, required: false, ord: 10, label: t('productions:orderForm.number') },
            { field: 'recipe_id', visible: true, required: false, ord: 20, label: t('productions:orderForm.recipeId') },
            { field: 'product_id', visible: true, required: true, ord: 30, label: t('productions:orderForm.productId') },
            { field: 'warehouse_id', visible: true, required: false, ord: 40, label: t('productions:orderForm.warehouseId') },
            { field: 'qty_planned', visible: true, required: true, ord: 50, label: t('productions:orderForm.plannedQty') },
            { field: 'scheduled_date', visible: true, required: false, ord: 60, label: t('productions:orderForm.scheduledDate') },
            { field: 'batch_number', visible: true, required: false, ord: 70, label: t('productions:orderForm.batchNumber') },
            { field: 'notes', visible: true, required: false, ord: 80, label: t('productions:orderForm.notes') },
        ]

        const map = new Map(base.map((cfg) => [cfg.field, cfg]))
        ;(fields || []).forEach((cfg) => {
            if (cfg.visible === false) {
                map.delete(cfg.field)
                return
            }
            const prev = map.get(cfg.field) || {}
            map.set(cfg.field, { ...prev, ...cfg })
        })

        let list = Array.from(map.values())
        if (!id) {
            // Auto-managed on create: backend generates number and batch;
            // warehouse is optional; scheduled date defaults to now.
            const autoCreateFields = new Set(['numero', 'warehouse_id', 'batch_number'])
            list = list.filter((cfg) => !autoCreateFields.has(cfg.field))
        }
        return list.sort((a, b) => (a.ord || 999) - (b.ord || 999))
    }, [fields, t])

    useEffect(() => {
        if (id) return
        const shouldAutoCreate = search.get('autoCreate') === '1'
        if (!shouldAutoCreate) return
        if (autoCreateDoneRef.current) return
        if (!form.recipe_id || !form.product_id) return
        if (!Number(form.qty_planned || 0) || Number(form.qty_planned || 0) <= 0) return

        autoCreateDoneRef.current = true
        ;(async () => {
            try {
                const payload: any = { ...form }
                if (!payload.scheduled_date) payload.scheduled_date = new Date().toISOString()
                delete payload.numero
                delete payload.batch_number
                await createProductionOrder(payload)
                success(t('productions:orderForm.saved'))
                nav('..')
            } catch (e: any) {
                autoCreateDoneRef.current = false
                error(getErrorMessage(e))
            }
        })()
    }, [id, search, form, nav, success, error, t])

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            for (const f of fieldList || []) {
                if (f.required && f.visible !== false) {
                    const val = (form as any)[f.field]
                    if (val === undefined || val === null || String(val).trim() === '') {
                        throw new Error(`Field "${f.label || f.field}" is required`)
                    }
                }
            }
            if (!Number(form.qty_planned || 0) || Number(form.qty_planned || 0) <= 0) {
                throw new Error(t('productions:orderForm.qtyError'))
            }
            const payload: any = { ...form }
            if (!id) {
                if (!payload.scheduled_date) payload.scheduled_date = new Date().toISOString()
                delete payload.numero
                delete payload.batch_number
            }
            if (id) await updateProductionOrder(id, payload)
            else await createProductionOrder(payload)
            success(t('productions:orderForm.saved'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const getInputType = (field: string): string => {
        if (field.includes('date')) return 'date'
        if (field.includes('qty') || field.includes('cantidad')) return 'number'
        if (field === 'notes' || field === 'notas') return 'textarea'
        return 'text'
    }

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? t('productions:orderForm.editTitle') : t('productions:orderForm.newTitle')}</h3>
            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 620 }}>
                {!id && recipeSummary && (
                    <div className="rounded border border-gray-200 bg-gray-50 p-3 text-sm space-y-2">
                        <div className="font-semibold">{recipeSummary.name || '-'}</div>
                        <div className="text-gray-600">{recipeSummary.productName || '-'}</div>
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <div className="text-gray-500">{t('productions:orderForm.totalCost')}</div>
                                <div>${recipeSummary.totalCost.toFixed(2)}</div>
                            </div>
                            <div>
                                <div className="text-gray-500">{t('productions:orderForm.yield')}</div>
                                <div>{recipeSummary.yieldQty}</div>
                            </div>
                            <div>
                                <div className="text-gray-500">{t('productions:orderForm.costPerUnit')}</div>
                                <div>${recipeSummary.unitCost.toFixed(4)}</div>
                            </div>
                            <div>
                                <div className="text-gray-500">{t('productions:orderForm.suggestedPrice')}</div>
                                <div>${recipeSummary.suggestedPrice.toFixed(2)}</div>
                            </div>
                        </div>
                        {selectedWarehouse && (
                            <div className="text-gray-700">
                                {t('productions:orderForm.warehouse')}: {selectedWarehouse.code || selectedWarehouse.name || selectedWarehouse.id}
                            </div>
                        )}
                        <label className="flex items-center gap-2 pt-1">
                            <input
                                type="checkbox"
                                checked={useRecipeDefaultQty}
                                onChange={(e) => {
                                    const checked = e.target.checked
                                    setUseRecipeDefaultQty(checked)
                                    if (checked) {
                                        setForm((prev) => ({ ...prev, qty_planned: recipeSummary.yieldQty }))
                                    }
                                }}
                            />
                            <span>{t('productions:orderForm.useRecipeDefaultQty')}</span>
                        </label>
                    </div>
                )}

                {!id && (
                    <div className="rounded border border-gray-200 bg-white p-3 text-sm space-y-2">
                        <div className="font-medium">{t('productions:orderForm.quickProduction')}</div>
                        <label className="block text-gray-600">{t('productions:orderForm.recipe')}</label>
                        <select
                            className="border rounded px-2 py-2 w-full"
                            value={String(form.recipe_id || '')}
                            onChange={async (e) => {
                                const rid = e.target.value
                                if (!rid) return
                                try {
                                    const [recipe, breakdown, products] = await Promise.all([
                                        getRecipeDetail(rid),
                                        getCostBreakdown(rid),
                                        listProducts({ limit: 500 }),
                                    ])
                                    const qtyFromQuery = Number(search.get('qty') || 0)
                                    const yieldQty = Number(recipe.yield_qty || breakdown.rendimiento || 1)
                                    const plannedQty = qtyFromQuery > 0 ? qtyFromQuery : (yieldQty > 0 ? yieldQty : 1)
                                    const unitCost = Number(breakdown.costo_por_unidad || 0)
                                    const totalCost = Number(breakdown.costo_total || 0)
                                    const matchedProduct = Array.isArray(products)
                                        ? products.find((p) => p.id === recipe.product_id)
                                        : undefined
                                    const suggestedPrice = Number(matchedProduct?.price ?? unitCost * 2.5)

                                    setRecipeSummary({
                                        name: String(recipe.name || ''),
                                        productName: String(matchedProduct?.name || recipe.product_name || ''),
                                        yieldQty,
                                        totalCost,
                                        unitCost,
                                        suggestedPrice,
                                    })
                                    setUseRecipeDefaultQty(plannedQty === yieldQty)
                                    setForm((prev) => ({
                                        ...prev,
                                        recipe_id: recipe.id,
                                        product_id: recipe.product_id,
                                        qty_planned: plannedQty,
                                    }))
                                    setPrefillLocked(true)
                                } catch (err: any) {
                                    error(getErrorMessage(err))
                                }
                            }}
                        >
                            <option value="">{loadingRecipes ? t('productions:orderForm.loading') : t('productions:orderForm.selectRecipe')}</option>
                            {availableRecipes.map((r) => (
                                <option key={r.id} value={r.id}>
                                    {r.name}
                                </option>
                            ))}
                        </select>
                        <div className="text-xs text-gray-500">
                            {t('productions:orderForm.yieldHint')}
                        </div>
                    </div>
                )}

                {loadingCfg && <div className="text-sm text-gray-500">Loading fields...</div>}

                {fieldList.map((f) => {
                    const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
                    const type = getInputType(f.field)
                    const value = (form as any)[f.field] ?? ''
                    const isLockedByRecipe = !id && prefillLocked && (f.field === 'recipe_id' || f.field === 'product_id')
                    const qtyLocked = !id && !!recipeSummary && f.field === 'qty_planned' && useRecipeDefaultQty
                    const dateLocked = !id && f.field === 'scheduled_date'
                    const readOnly = isLockedByRecipe || qtyLocked || dateLocked

                    return (
                        <div key={f.field}>
                            <label className="block mb-1">{label}</label>
                            {type === 'textarea' ? (
                                <textarea
                                    value={value}
                                    onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
                                    className="border px-2 py-1 w-full rounded"
                                    required={!!f.required}
                                    placeholder={f.help || ''}
                                    rows={3}
                                    readOnly={readOnly}
                                />
                            ) : (
                                <input
                                    type={type}
                                    value={value}
                                    onChange={(e) => {
                                        if (readOnly) return
                                        setForm({
                                            ...form,
                                            [f.field]: type === 'number' ? Number(e.target.value) : e.target.value,
                                        })
                                    }}
                                    className="border px-2 py-1 w-full rounded"
                                    required={!!f.required}
                                    placeholder={f.help || ''}
                                    step={type === 'number' ? '0.01' : undefined}
                                    readOnly={readOnly}
                                />
                            )}
                            {isLockedByRecipe && (
                                <div className="mt-1 text-xs text-gray-500">
                                    {t('productions:orderForm.autoFilled')}
                                </div>
                            )}
                            {qtyLocked && (
                                <div className="mt-1 text-xs text-gray-500">
                                    {t('productions:orderForm.uncheckToEdit')}
                                </div>
                            )}
                        </div>
                    )
                })}

                <div className="pt-2">
                    <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">{t('productions:orderForm.save')}</button>
                    <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>{t('productions:orderForm.cancel')}</button>
                </div>
            </form>
        </div>
    )
}
