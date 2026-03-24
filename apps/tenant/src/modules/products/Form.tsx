// apps/tenant/src/modules/products/Form.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import { createProducto, getProducto, updateProducto, listCategorias, type Producto, type Categoria } from './productsApi'
import { listRecipes, type Recipe } from '../../services/api/recetas'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'
import { useCurrency } from '../../hooks/useCurrency'
import { getCompanySettings, getDefaultReorderPoint } from '../../services/companySettings'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'
import ProductVariants from './ProductVariants'

const BARCODE_META_FIELDS = ['codigo_barras', 'barcode', 'ean', 'upc'] as const

type FieldCfg = {
    field: string
    visible?: boolean
    required?: boolean
    ord?: number | null
    label?: string | null
    help?: string | null
    type?: string | null
    options?: string[] | null
}

export default function ProductoForm() {
    const { id, empresa } = useParams()
    const { t } = useTranslation(['products', 'common'])
    const nav = useNavigate()
    const { symbol: currencySymbol } = useCurrency()
    const can = usePermission()
    const requiredPerm = id ? 'products:update' : 'products:create'
    const [form, setForm] = useState<Partial<Producto>>({
        sku: '',
        name: '',
        price: 0,
        tax_rate: 0,
        active: true,
        stock: 0,
        unit: 'unit',
        is_raw_material: false,
    })
    const { success, error } = useToast()
    const [fields, setFields] = useState<FieldCfg[] | null>(null)
    const [loadingCfg, setLoadingCfg] = useState(false)
    const [categorias, setCategorias] = useState<Categoria[]>([])
    const [minStockGlobal, setMinStockGlobal] = useState(0)
    const [productRecipe, setProductRecipe] = useState<Recipe | null>(null)
    const [syncingPrice, setSyncingPrice] = useState(false)

    // Cargar categorías disponibles
    useEffect(() => {
        ; (async () => {
            try {
                const data = await listCategorias()
                setCategorias(data)
            } catch (e) {
                console.error('Error cargando categorías:', e)
            }
        })()
    }, [])

    useEffect(() => {
        if (!id) return
        getProducto(id).then((x) => setForm({ ...x }))
    }, [id])

    useEffect(() => {
        let cancelled = false
            ; (async () => {
                try {
                    setLoadingCfg(true)
                    const data = await apiFetch<{ items?: FieldCfg[] }>('/api/v1/company/settings/fields?module=products')
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
    }, [])

    useEffect(() => {
        let cancelled = false
            ; (async () => {
                try {
                    const settings = await getCompanySettings()
                    if (!cancelled) {
                        setMinStockGlobal(Number(getDefaultReorderPoint(settings) || 0))
                    }
                } catch {
                    if (!cancelled) setMinStockGlobal(0)
                }
            })()
        return () => {
            cancelled = true
        }
    }, [])

    const isBakerySector = useMemo(
        () => (fields || []).some((cfg) => ['peso_unitario', 'caducidad_dias', 'ingredientes', 'receta_id'].includes(cfg.field)),
        [fields]
    )

    useEffect(() => {
        if (!id || !isBakerySector) return
        listRecipes({ product_id: id, limit: 1 })
            .then((rs) => setProductRecipe(Array.isArray(rs) ? (rs[0] ?? null) : null))
            .catch(() => {})
    }, [id, isBakerySector])

    const fieldList = useMemo(() => {
        const base: FieldCfg[] = [
            { field: 'sku', visible: true, required: false, ord: 10, label: t('products:form.sku'), type: 'text', help: t('products:form.skuHelp') },
            { field: 'name', visible: true, required: true, ord: 20, label: t('products:form.name'), type: 'text' },
            { field: 'category', visible: true, required: false, ord: 22, label: t('products:form.category'), type: 'select' },
            { field: 'description', visible: true, required: false, ord: 25, label: t('products:form.description'), type: 'textarea' },
            { field: 'price', visible: true, required: true, ord: 30, label: `${t('products:form.price')} (${currencySymbol})`, type: 'number' },
            { field: 'stock', visible: true, required: false, ord: 35, label: t('products:form.stock'), type: 'number' },
            { field: 'is_raw_material', visible: isBakerySector, required: false, ord: 37, label: t('products:form.rawMaterial', 'Materia prima'), type: 'boolean', help: t('products:form.rawMaterialHelp', 'Marca este producto si se usa como ingrediente o insumo de producción.') },
            { field: 'tax_rate', visible: true, required: false, ord: 40, label: t('products:form.tax'), type: 'number' },
            { field: 'active', visible: true, required: false, ord: 50, label: t('products:form.active'), type: 'boolean' },
            { field: 'import_aliases', visible: false, required: false, ord: 90, label: t('products:form.importAliases', 'Alias de importación'), type: 'import_aliases', help: t('products:form.importAliasesHelp', 'Nombres alternativos en facturas de proveedor con factor de conversión.') },
        ]

        const map = new Map(base.map((cfg) => [cfg.field, cfg]))
            ; (fields || []).forEach((cfg) => {
                if (cfg.visible === false) {
                    map.delete(cfg.field)
                    return
                }
                const prev = map.get(cfg.field) || {}
                const merged = { ...prev, ...cfg }
                // Price field always shows currency symbol
                if (cfg.field === 'price' && merged.label && !merged.label.includes(currencySymbol)) {
                    merged.label = `${merged.label} (${currencySymbol})`
                }
                map.set(cfg.field, merged)
            })

        return Array.from(map.values()).sort((a, b) => (a.ord || 999) - (b.ord || 999))
    }, [fields, currencySymbol, isBakerySector, t])

    const suggestedPrice = Number((form as any).suggested_price ?? 0) || 0
    const useSuggestedPrice = Boolean((form as any).use_suggested_price)

    const parseKeyValueNumberMap = (raw: string) => {
        const result: Record<string, number> = {}
        raw
            .split(',')
            .map((part) => part.trim())
            .filter(Boolean)
            .forEach((part) => {
                const [key, value] = part.split('=').map((chunk) => chunk.trim())
                const num = Number(value)
                if (key && Number.isFinite(num) && num > 0) {
                    result[key] = num
                }
            })
        return result
    }

    const formatKeyValueNumberMap = (map?: Record<string, unknown> | null) => {
        if (!map) return ''
        return Object.entries(map)
            .map(([key, value]) => `${key}=${value}`)
            .join(', ')
    }

    if (!can(requiredPerm)) {
        return <PermissionDenied permission={requiredPerm} />
    }

    const updateMetadata = (updater: (meta: Record<string, unknown>) => Record<string, unknown>) => {
        setForm((prev) => {
            const current = { ...(((prev.product_metadata ?? {}) as Record<string, unknown>) ?? {}) }
            const next = updater(current)
            return { ...prev, product_metadata: next }
        })
    }

    const updateWholesale = (patch: Record<string, unknown>) => {
        updateMetadata((meta) => {
            const wholesale = { ...(((meta.wholesale ?? {}) as Record<string, unknown>) ?? {}), ...patch }
            meta.wholesale = wholesale
            return meta
        })
    }

    const updatePacks = (packs: Record<string, number>) => {
        updateMetadata((meta) => {
            if (Object.keys(packs).length) {
                meta.packs = packs
            } else {
                delete meta.packs
            }
            return meta
        })
    }

    const updateWholesaleMinByPack = (packs: Record<string, number>) => {
        updateMetadata((meta) => {
            const wholesale = { ...(((meta.wholesale ?? {}) as Record<string, unknown>) ?? {}) }
            if (Object.keys(packs).length) {
                wholesale.min_qty_by_pack = packs
            } else {
                delete wholesale.min_qty_by_pack
            }
            meta.wholesale = wholesale
            return meta
        })
    }

    const prepareProductPayload = (metadataOverride?: Record<string, unknown>) => {
        const payload: Record<string, unknown> = { ...(form as Record<string, unknown>) }
        const metadata =
            metadataOverride !== undefined && metadataOverride !== null
                ? { ...metadataOverride }
                : { ...(((payload.product_metadata || {}) as Record<string, unknown>) ?? {}) }

        BARCODE_META_FIELDS.forEach((field) => {
            if (Object.prototype.hasOwnProperty.call(payload, field)) {
                const value = payload[field]
                if (value !== undefined && value !== null) {
                    const normalized = typeof value === 'string' ? value.trim() : value
                    if (normalized !== '') {
                        metadata[field] = normalized
                    } else {
                        delete metadata[field as keyof typeof metadata]
                    }
                }
                delete payload[field]
            }
        })

        if (Object.keys(metadata).length > 0) {
            payload.product_metadata = metadata
        } else {
            delete payload.product_metadata
        }

        return payload
    }

    const syncRecipePrice = async () => {
        if (!productRecipe) return
        setSyncingPrice(true)
        try {
            const res = await apiFetch<{ suggested_price: number }>(
                `/api/v1/tenant/manufacturing/recipes/${productRecipe.id}/sync-product-price`,
                { method: 'POST' }
            )
            if (res?.suggested_price != null) {
                setForm((prev) => ({ ...prev, suggested_price: res.suggested_price }))
                success(t('products:form.priceSynced', 'Precio sincronizado desde receta'))
            }
        } catch (e) {
            error(getErrorMessage(e))
        } finally {
            setSyncingPrice(false)
        }
    }

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            // Validación de campos required
            for (const f of fieldList) {
                if (f.required && f.visible !== false) {
                    const val = (form as any)[f.field]
                    if (val === undefined || val === null || String(val).trim() === '') {
                        throw new Error(`El campo "${f.label || f.field}" es obligatorio`)
                    }
                }
            }

            // Validación de precio
            if (form.price !== undefined && form.price < 0) {
                throw new Error(t('products:form.priceNegativeError'))
            }

            const normalizedUnit = String(form.unit || '').trim().toLowerCase()
            const genericUnits = new Set(['', 'unit', 'units'])
            if (isBakerySector && Boolean(form.is_raw_material) && genericUnits.has(normalizedUnit)) {
                throw new Error('Las materias primas de panaderia deben usar una unidad explicita como kg, g, L, ml o uds.')
            }

            const metadata = { ...(((form.product_metadata ?? {}) as Record<string, unknown>) ?? {}) }
            const wholesaleMeta = (metadata.wholesale || {}) as Record<string, unknown>
            const wholesaleEnabled = wholesaleMeta.enabled !== false
            if (wholesaleEnabled && minStockGlobal > 0 && (Number(form.stock ?? 0) || 0) < minStockGlobal) {
                throw new Error(`No se permite activar mayorista si el stock inicial es menor al minimo de stock (${minStockGlobal}).`)
            }

            // Auto-calculate margin if cost_price is set
            if (form.cost_price && form.price) {
                const margen = ((form.price - form.cost_price) / form.cost_price) * 100
                metadata.margen = parseFloat(margen.toFixed(2))
                setForm((prev) => ({ ...prev, product_metadata: metadata }))
            }

            const payload = prepareProductPayload(metadata) as Partial<Producto>

            if (id) await updateProducto(id, payload)
            else await createProducto(payload)

            success(t('products:form.saved'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const generateSKU = () => {
        setForm((prev) => {
            const prefix = prev.category ? prev.category.substring(0, 3).toUpperCase() : 'PRO'
            const random = crypto.randomUUID().replace(/-/g, '').slice(0, 6).toUpperCase()
            return { ...prev, sku: `${prefix}-${random}` }
        })
    }

    const renderField = (f: FieldCfg) => {
        const label = f.label || f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' ')
        const value = (form as any)[f.field] ?? ''
        const fieldType = f.type || 'text'

        // Campo SKU con botón de auto-generación
        if (f.field === 'sku') {
            return (
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={value}
                        onChange={(e) => { const v = e.target.value; setForm((prev) => ({ ...prev, [f.field]: v })) }}
                        className="gc-input"
                        placeholder={f.help || t('products:form.codePlaceholder')}
                    />
                    <button
                        type="button"
                        onClick={generateSKU}
                        className="px-4 py-2 bg-gray-100 border border-slate-200 rounded hover:bg-gray-200 transition-colors whitespace-nowrap"
                        title="Generar código automático"
                    >
                        ⚡ Auto
                    </button>
                </div>
            )
        }

        // Campo Categoría con select que carga desde BD
        if (f.field === 'category') {
            return (
                <select
                    value={value}
                    onChange={(e) => { const v = e.target.value; setForm((prev) => ({ ...prev, category: v })) }}
                    className="gc-input"
                >
                    <option value="">Sin categoría</option>
                    {categorias.map((cat) => (
                        <option key={cat.id} value={cat.name}>
                            {cat.name}
                        </option>
                    ))}
                </select>
            )
        }

        if (f.field === 'import_aliases') {
            const aliases: Array<{ name: string; factor: number; unit?: string }> = form.import_aliases || []
            return (
                <div className="md:col-span-2">
                    {aliases.map((alias, idx) => (
                        <div key={idx} className="flex gap-2 mb-2 items-end">
                            <div className="flex-1">
                                {idx === 0 && <label className="block text-xs text-slate-600 mb-1">{t('products:form.aliasName', 'Nombre en factura')}</label>}
                                <input type="text" value={alias.name}
                                    onChange={(e) => { const a = [...aliases]; a[idx] = { ...a[idx], name: e.target.value }; setForm((p) => ({ ...p, import_aliases: a })) }}
                                    className="gc-input"
                                    placeholder="Ej: HARINA TRADICION PREMIUM 50 KG" />
                            </div>
                            <div className="w-24">
                                {idx === 0 && <label className="block text-xs text-slate-600 mb-1">{t('products:form.aliasFactor', 'Factor')}</label>}
                                <input type="number" min="0.001" step="any" value={alias.factor}
                                    onChange={(e) => { const a = [...aliases]; a[idx] = { ...a[idx], factor: Number(e.target.value) || 1 }; setForm((p) => ({ ...p, import_aliases: a })) }}
                                    className="gc-input" />
                            </div>
                            <div className="w-20">
                                {idx === 0 && <label className="block text-xs text-slate-600 mb-1">{t('products:form.aliasUnit', 'Unidad')}</label>}
                                <input type="text" value={alias.unit || ''}
                                    onChange={(e) => { const a = [...aliases]; a[idx] = { ...a[idx], unit: e.target.value }; setForm((p) => ({ ...p, import_aliases: a })) }}
                                    className="gc-input" placeholder="kg" />
                            </div>
                            <button type="button"
                                onClick={() => { const a = aliases.filter((_, i) => i !== idx); setForm((p) => ({ ...p, import_aliases: a.length ? a : null })) }}
                                className="px-2 py-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded" title={t('common:delete', 'Eliminar')}>✕</button>
                        </div>
                    ))}
                    <button type="button"
                        onClick={() => setForm((p) => ({ ...p, import_aliases: [...(p.import_aliases || []), { name: '', factor: 1, unit: '' }] }))}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                        + {t('products:form.addAlias', 'Agregar alias')}
                    </button>
                </div>
            )
        }

        switch (fieldType) {
            case 'number':
                return (
                    <input
                        type="number"
                        step="0.01"
                        value={value}
                        onChange={(e) => { const v = parseFloat(e.target.value) || 0; setForm((prev) => ({ ...prev, [f.field]: v })) }}
                        className="gc-input"
                        required={!!f.required}
                        placeholder={f.help || ''}
                    />
                )

            case 'boolean':
                return (
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={!!value}
                            onChange={(e) => { const v = e.target.checked; setForm((prev) => ({ ...prev, [f.field]: v })) }}
                            className="w-4 h-4 rounded border-slate-200 text-blue-600 focus:ring-[var(--gc-primary)]"
                        />
                        <span className="text-sm text-slate-600">{f.help || 'Sí/No'}</span>
                    </label>
                )

            case 'textarea':
                return (
                    <textarea
                        value={value}
                        onChange={(e) => { const v = e.target.value; setForm((prev) => ({ ...prev, [f.field]: v })) }}
                        className="gc-input"
                        rows={3}
                        required={!!f.required}
                        placeholder={f.help || ''}
                    />
                )

            case 'select':
                return (
                    <select
                        value={value}
                        onChange={(e) => { const v = e.target.value; setForm((prev) => ({ ...prev, [f.field]: v })) }}
                        className="gc-input"
                        required={!!f.required}
                    >
                        <option value="">Seleccionar...</option>
                        {(f.options || []).map((opt) => (
                            <option key={opt} value={opt}>
                                {opt}
                            </option>
                        ))}
                    </select>
                )

            default: // text
                return (
                    <input
                        type="text"
                        value={value}
                        onChange={(e) => { const v = e.target.value; setForm((prev) => ({ ...prev, [f.field]: v })) }}
                        className="gc-input"
                        required={!!f.required}
                        placeholder={f.help || ''}
                    />
                )
        }
    }

    const metadata = ((form.product_metadata ?? {}) as Record<string, unknown>) ?? {}
    const wholesale = ((metadata.wholesale ?? {}) as Record<string, unknown>) ?? {}
    const wholesaleEnabled = wholesale.enabled !== false
    const wholesalePrice = Number(wholesale.price ?? 0) || 0
    const wholesaleMinUnits = Number(wholesale.min_qty_units ?? 0) || 0
    const wholesaleApplyMode = (wholesale.apply_mode as string) === 'excess' ? 'excess' : 'all'
    const packsInput = formatKeyValueNumberMap(metadata.packs as Record<string, unknown>)
    const wholesaleMinByPackInput = formatKeyValueNumberMap(wholesale.min_qty_by_pack as Record<string, unknown>)
    const stockValue = Number(form.stock ?? 0) || 0
    const stockBelowGlobalMin = minStockGlobal > 0 && stockValue < minStockGlobal

    return (
        <div className="gc-container py-6 max-w-4xl">
            <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>

            {/* Header */}
            <div className="mb-6">
                <h1 className="gc-page-header__title">{id ? t('products:form.editProduct') : t('products:form.newProduct')}</h1>
                <p className="gc-page-header__subtitle mt-1">
                    {id ? t('products:form.editDescription') : t('products:form.newDescription')}
                </p>
            </div>

            <form onSubmit={onSubmit} className="space-y-5">

                {/* ── Datos del producto ── */}
                <fieldset className="gc-card">
                    <legend className="gc-section-title px-2">
                        {t('products:form.productData', 'Datos del producto')}
                    </legend>
                    {loadingCfg && (
                        <div className="flex items-center gap-2 text-sm mt-3" style={{ color: 'var(--gc-muted)' }}>
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            {t('products:form.loadingFields', 'Cargando configuración...')}
                        </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                        {fieldList.map((f) => (
                            <div key={f.field} className={f.type === 'textarea' || f.type === 'import_aliases' ? 'md:col-span-2' : ''}>
                                <label className="gc-label">
                                    {f.label || f.field.replace(/_/g, ' ')}
                                    {f.required && <span className="text-red-500 ml-1">*</span>}
                                </label>
                                {renderField(f)}
                                {f.help && f.type !== 'boolean' && f.type !== 'import_aliases' && (
                                    <p className="gc-field-hint">{f.help}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </fieldset>

                {/* ── Precio desde receta ── */}
                {productRecipe && (
                    <fieldset className="gc-card">
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                            <legend className="gc-section-title px-2">
                                {t('products:form.suggestedPriceTitle')}
                                <span className="gc-field-hint ml-2" style={{ fontWeight: 400 }}>
                                    {productRecipe.name}
                                </span>
                            </legend>
                            <button
                                type="button"
                                onClick={syncRecipePrice}
                                disabled={syncingPrice}
                                className="gc-btn gc-btn--soft gc-btn--sm"
                                style={{ marginTop: '0.1rem' }}
                            >
                                {syncingPrice ? (
                                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
                                ) : (
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                                )}
                                {t('products:form.syncPrice', 'Recalcular')}
                            </button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                            <div>
                                <label className="gc-label">{t('products:form.suggestedPrice')}</label>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={suggestedPrice}
                                        disabled
                                        className="gc-input"
                                        style={{ flex: 1 }}
                                        placeholder={suggestedPrice === 0 ? t('products:form.notCalculated', 'Sin calcular') : ''}
                                    />
                                    <span className="gc-field-hint">{currencySymbol}</span>
                                </div>
                                {suggestedPrice === 0 && (
                                    <p className="gc-field-hint" style={{ color: 'var(--gc-warning, #b45309)' }}>
                                        {t('products:form.syncHint', 'Pulsa "Recalcular" para obtener el precio desde los costes actuales.')}
                                    </p>
                                )}
                            </div>
                            {suggestedPrice > 0 && (
                                <div>
                                    <label className="gc-label">{t('products:form.useSuggestedPriceLabel')}</label>
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={useSuggestedPrice}
                                            onChange={(e) => {
                                                const checked = e.target.checked
                                                setForm((prev) => ({
                                                    ...prev,
                                                    use_suggested_price: checked,
                                                    ...(checked ? { price: suggestedPrice } : {}),
                                                }))
                                            }}
                                            className="w-4 h-4 rounded"
                                            style={{ accentColor: 'var(--gc-primary)' }}
                                        />
                                        <span className="gc-field-hint" style={{ fontSize: '0.875rem' }}>{t('products:form.useSuggestedPriceCheckbox')}</span>
                                    </label>
                                    <p className="gc-field-hint">{t('products:form.useSuggestedPriceHelp')}</p>
                                </div>
                            )}
                        </div>
                    </fieldset>
                )}

                {/* ── Precio mayorista ── */}
                <fieldset className="gc-card">
                    <legend className="gc-section-title px-2">{t('products:form.wholesaleTitle')}</legend>
                    <p className="gc-field-hint mt-1 mb-3">{t('products:form.wholesaleHint')}</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="gc-label">{t('products:form.wholesaleEnable')}</label>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={wholesaleEnabled}
                                    onChange={(e) => updateWholesale({ enabled: e.target.checked })}
                                    disabled={stockBelowGlobalMin && !wholesaleEnabled}
                                    className="w-4 h-4 rounded"
                                    style={{ accentColor: 'var(--gc-primary)' }}
                                />
                                <span style={{ fontSize: '0.875rem', color: 'var(--gc-foreground)' }}>{t('products:form.wholesaleApply')}</span>
                            </label>
                            {minStockGlobal > 0 && (
                                <p className="gc-field-hint">{t('products:form.stockGlobal', { value: minStockGlobal })}</p>
                            )}
                            {stockBelowGlobalMin && (
                                <p className="gc-field-hint" style={{ color: 'var(--gc-warning, #b45309)' }}>
                                    {t('products:form.stockBelowMin', { stock: stockValue, min: minStockGlobal })}
                                </p>
                            )}
                        </div>
                        <div>
                            <label className="gc-label">{t('products:form.wholesalePrice')}</label>
                            <input
                                type="number"
                                step="0.01"
                                value={wholesalePrice}
                                onChange={(e) => updateWholesale({ price: Number(e.target.value) || 0 })}
                                className="gc-input"
                                placeholder={t('products:form.wholesalePricePlaceholder', { currency: currencySymbol })}
                            />
                        </div>
                        <div>
                            <label className="gc-label">{t('products:form.wholesaleMinUnits')}</label>
                            <input
                                type="number"
                                step="1"
                                min="0"
                                value={wholesaleMinUnits}
                                onChange={(e) => updateWholesale({ min_qty_units: Number(e.target.value) || 0 })}
                                className="gc-input"
                                placeholder={t('products:form.wholesaleMinUnitsPlaceholder')}
                            />
                        </div>
                        <div>
                            <label className="gc-label">{t('products:form.wholesaleApplyMode')}</label>
                            <select
                                value={wholesaleApplyMode}
                                onChange={(e) => updateWholesale({ apply_mode: e.target.value })}
                                className="gc-input"
                            >
                                <option value="all">{t('products:form.wholesaleModeAll')}</option>
                                <option value="excess">{t('products:form.wholesaleModeExcess')}</option>
                            </select>
                        </div>
                        <div className="md:col-span-2">
                            <label className="gc-label">{t('products:form.packs')}</label>
                            <input
                                type="text"
                                value={packsInput}
                                onChange={(e) => updatePacks(parseKeyValueNumberMap(e.target.value))}
                                className="gc-input"
                                placeholder={t('products:form.packsPlaceholder')}
                            />
                            <p className="gc-field-hint">{t('products:form.packsHelp')}</p>
                        </div>
                        <div className="md:col-span-2">
                            <label className="gc-label">{t('products:form.minByPack')}</label>
                            <input
                                type="text"
                                value={wholesaleMinByPackInput}
                                onChange={(e) => updateWholesaleMinByPack(parseKeyValueNumberMap(e.target.value))}
                                className="gc-input"
                                placeholder={t('products:form.minByPackPlaceholder')}
                            />
                            <p className="gc-field-hint">{t('products:form.minByPackHelp')}</p>
                        </div>
                    </div>
                </fieldset>

                {/* ── Botones ── */}
                <div className="flex gap-3">
                    <ProtectedButton
                        permission={requiredPerm}
                        type="submit"
                        className="gc-btn gc-btn--primary"
                    >
                        {t('products:form.save')}
                    </ProtectedButton>
                    <button
                        type="button"
                        className="gc-btn gc-btn--ghost"
                        onClick={() => nav('..')}
                    >
                        {t('products:form.cancel')}
                    </button>
                </div>
            </form>

            {/* ── Variantes (solo sectores no-panadería) ── */}
            {id && !isBakerySector && (
                <fieldset className="gc-card mt-5">
                    <legend className="gc-section-title px-2">
                        {t('products:form.variantsTitle', 'Variantes de producto')}
                    </legend>
                    <p className="gc-field-hint mt-1 mb-4">
                        {t('products:form.variantsHint', 'Gestiona variantes por talla, color u otros atributos.')}
                    </p>
                    <ProductVariants productId={id} basePrice={form.price} currencySymbol={currencySymbol} />
                </fieldset>
            )}
        </div>
    )
}
