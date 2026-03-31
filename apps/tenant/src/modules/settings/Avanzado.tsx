import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import tenantApi from '../../shared/api/client'
import { useCompanySector } from '../../contexts/CompanyConfigContext'
import { clearCompanySettingsCache, getCompanySettings } from '../../services/companySettings'
import { listRecipes, type Recipe } from '../../services/api/recetas'
import { getErrorMessage, useToast } from '../../shared/toast'
import { useSettingsAccess } from './useSettingsAccess'
import { isBakeryOperativeSector } from './sectorRules'
import { NUMBERING_DEFAULTS, resetToDefaults } from '../../constants/defaults'
import { useDocTypes } from '../../hooks/useGlobalCatalogs'
import {
    getBakeryShortcutValidationError,
    normalizeBakeryShortcutLetter,
    sanitizeBulkPricingItem,
    type BulkPricingItem,
} from '../pos/bakeryShortcuts'

type InventoryForm = {
    track_lots?: boolean
    track_expiry?: boolean
    allow_negative_stock?: boolean
    reorder_point_default?: number | null
}

type PosForm = {
    receipt_width_mm?: number | null
    default_tax_rate?: number | null
    return_window_days?: number | null
    price_includes_tax?: boolean
    store_credit_enabled?: boolean
    store_credit_single_use?: boolean
    store_credit_expiry_months?: number | null
    bulk_pricing_items?: BulkPricingItem[]
}

type NumberingCounter = {
    doc_type: string
    year: number
    series: string
    current_no: number
    updated_at?: string | null
}

type DocSeries = {
    id: string
    register_id?: string | null
    doc_type: string
    name: string
    current_no: number
    reset_policy: 'yearly' | 'never'
    active: boolean
    created_at?: string | null
}

type AvanzadoSettingsProps = {
    variant?: 'admin' | 'operativo'
}

type BulkPricingProductOption = {
    id: string
    name: string
    recipe_name?: string
}

export default function AvanzadoSettings({ variant = 'admin' }: AvanzadoSettingsProps) {
    const { t } = useTranslation(['settings', 'common'])
    const { success, error } = useToast()
    const { isCompanyAdmin } = useSettingsAccess()
    const sector = useCompanySector()
    const isAdminView = variant === 'admin'
    const showBakeryBulkPricing = !isAdminView && isBakeryOperativeSector(sector?.plantilla)
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [locale, setLocale] = useState('')
    const [timezone, setTimezone] = useState('')
    const [currency, setCurrency] = useState('')
    const [inventory, setInventory] = useState<InventoryForm>({})
    const [pos, setPos] = useState<PosForm>({})
    const [docMinInvoice, setDocMinInvoice] = useState<number | null>(null)
    const [docRequireBuyer, setDocRequireBuyer] = useState(false)
    const [invoiceJson, setInvoiceJson] = useState('{}')
    const [einvoiceJson, setEinvoiceJson] = useState('{}')
    const [purchasesJson, setPurchasesJson] = useState('{}')
    const [expensesJson, setExpensesJson] = useState('{}')
    const [financeJson, setFinanceJson] = useState('{}')
    const [hrJson, setHrJson] = useState('{}')
    const [salesJson, setSalesJson] = useState('{}')
    const [settingsBase, setSettingsBase] = useState<Record<string, any>>({})
    const [numberingCounters, setNumberingCounters] = useState<NumberingCounter[]>([])
    const [numberingLoading, setNumberingLoading] = useState(false)
    const [counterForm, setCounterForm] = useState(NUMBERING_DEFAULTS.COUNTER_FORM)
    const [docSeriesList, setDocSeriesList] = useState<DocSeries[]>([])
    const [docSeriesLoading, setDocSeriesLoading] = useState(false)
    const [seriesForm, setSeriesForm] = useState(NUMBERING_DEFAULTS.DOC_SERIES_FORM)
    const [products, setProducts] = useState<BulkPricingProductOption[]>([])
    const [productsLoading, setProductsLoading] = useState(false)
    const [bulkPricingForm, setBulkPricingForm] = useState<BulkPricingItem>({
        product_id: '',
        quantity: 6,
        unit_price: 1.0,
        shortcut_letter: '',
    })

    const [resetYearlyPending, setResetYearlyPending] = useState(false)

    const { items: docTypesCatalog } = useDocTypes()
    const shouldAutoSaveBulk = useRef(false)

    const loadSettings = async () => {
        try {
            setLoading(true)
            const data = await getCompanySettings()
            setLocale(data.locale || '')
            setTimezone(data.timezone || '')
            setCurrency(data.currency || '')

            setInventory({
                track_lots: data.inventory?.track_lots ?? false,
                track_expiry: data.inventory?.track_expiry ?? false,
                allow_negative_stock: data.inventory?.allow_negative_stock ?? false,
                reorder_point_default:
                    data.inventory?.reorder_point_default ?? null,
            })

            const toNumberOrNull = (value: unknown) => {
                const num = Number(value)
                return Number.isFinite(num) ? num : null
            }

            const posConfig = data.pos_config || {}
            const tax = (posConfig as any).tax || {}
            const receipt = (posConfig as any).receipt || {}
            const storeCredit = (posConfig as any).store_credit || {}
            const bulkPricingItems = ((posConfig as any).bulk_pricing_items || []).map(sanitizeBulkPricingItem)
            const taxDefault = toNumberOrNull(tax.default_rate)
            const taxDefaultPct =
                taxDefault === null ? null : taxDefault <= 1 ? taxDefault * 100 : taxDefault
            setPos({
                receipt_width_mm: toNumberOrNull(receipt.width_mm),
                default_tax_rate: taxDefaultPct,
                return_window_days: toNumberOrNull(posConfig.return_window_days),
                price_includes_tax: tax.price_includes_tax ?? false,
                store_credit_enabled: storeCredit.enabled ?? false,
                store_credit_single_use: storeCredit.single_use ?? false,
                store_credit_expiry_months: toNumberOrNull(storeCredit.expiry_months),
                bulk_pricing_items: bulkPricingItems,
            })

            const baseSettings = (data.settings || {}) as Record<string, any>
            setSettingsBase(baseSettings)
            const buyerPolicy = (baseSettings.documents || {}).buyer_policy || {}
            setDocMinInvoice(
                Number.isFinite(Number(buyerPolicy.consumerFinalMaxTotal))
                    ? Number(buyerPolicy.consumerFinalMaxTotal)
                    : null
            )
            const minValue = Number(buyerPolicy.consumerFinalMaxTotal || 0)
            setDocRequireBuyer(
                buyerPolicy.requireBuyerAboveAmount ?? (Number.isFinite(minValue) && minValue > 0)
            )
            setInvoiceJson(JSON.stringify(data.invoice_config || {}, null, 2))
            setEinvoiceJson(JSON.stringify(baseSettings.einvoicing || {}, null, 2))
            setPurchasesJson(JSON.stringify(baseSettings.purchases || {}, null, 2))
            setExpensesJson(JSON.stringify(baseSettings.expenses || {}, null, 2))
            setFinanceJson(JSON.stringify(baseSettings.finance || {}, null, 2))
            setHrJson(JSON.stringify(baseSettings.hr || {}, null, 2))
            setSalesJson(JSON.stringify(baseSettings.sales || {}, null, 2))
        } catch (err: any) {
            error(getErrorMessage(err))
        } finally {
            setLoading(false)
        }
    }

    const loadNumbering = async () => {
        try {
            setNumberingLoading(true)
            setDocSeriesLoading(true)
            const [countersRes, seriesRes] = await Promise.all([
                tenantApi.get<NumberingCounter[]>('/api/v1/tenant/pos/numbering/counters'),
                tenantApi.get<DocSeries[]>('/api/v1/tenant/pos/numbering/series'),
            ])
            setNumberingCounters(countersRes.data || [])
            setDocSeriesList(seriesRes.data || [])
        } catch (err: any) {
            error(getErrorMessage(err))
        } finally {
            setNumberingLoading(false)
            setDocSeriesLoading(false)
        }
    }

    const loadProducts = async () => {
        try {
            setProductsLoading(true)
            const recipes = await listRecipes({ activo: true, limit: 500 })
            const byProductId = new Map<string, BulkPricingProductOption>()
            ;(Array.isArray(recipes) ? recipes : []).forEach((recipe: Recipe) => {
                const productId = String(recipe.product_id || '').trim()
                if (!productId || byProductId.has(productId)) return
                byProductId.set(productId, {
                    id: productId,
                    name: String(recipe.product_name || recipe.name || productId),
                    recipe_name: recipe.name || undefined,
                })
            })
            setProducts(
                Array.from(byProductId.values()).sort((a, b) => a.name.localeCompare(b.name))
            )
        } catch (err: any) {
            error(getErrorMessage(err))
        } finally {
            setProductsLoading(false)
        }
    }

    useEffect(() => {
        void loadSettings()
        if (variant !== 'admin') {
            void loadNumbering()
            if (showBakeryBulkPricing) {
                void loadProducts()
            }
        }
    }, [showBakeryBulkPricing, variant])

    useEffect(() => {
        if (shouldAutoSaveBulk.current) {
            shouldAutoSaveBulk.current = false
            void save()
        }
    }, [pos.bulk_pricing_items])

    const parsedSettings = useMemo(() => {
        if (!isAdminView) {
            return {
                invoice: {},
                einvoice: {},
                purchases: {},
                expenses: {},
                finance: {},
                hr: {},
                sales: {},
            }
        }
        const parse = (value: string) => {
            try {
                return value.trim() ? JSON.parse(value) : {}
            } catch {
                return null
            }
        }
        return {
            invoice: parse(invoiceJson),
            einvoice: parse(einvoiceJson),
            purchases: parse(purchasesJson),
            expenses: parse(expensesJson),
            finance: parse(financeJson),
            hr: parse(hrJson),
            sales: parse(salesJson),
        }
    }, [invoiceJson, einvoiceJson, purchasesJson, expensesJson, financeJson, hrJson, salesJson, isAdminView])

    const save = async () => {
        if (isAdminView) {
            if (
                parsedSettings.invoice === null ||
                parsedSettings.einvoice === null ||
                parsedSettings.purchases === null ||
                parsedSettings.expenses === null ||
                parsedSettings.finance === null ||
                parsedSettings.hr === null ||
                parsedSettings.sales === null
            ) {
                error('Revisa los JSON: hay un formato invalido')
                return
            }
        }

        try {
            setSaving(true)
            const payload: any = {}
            if (!isAdminView) {
                payload.locale = locale || null
                payload.timezone = timezone || null
                payload.currency = currency || null
                payload.inventory = {
                    track_lots: !!inventory.track_lots,
                    track_expiry: !!inventory.track_expiry,
                    allow_negative_stock: !!inventory.allow_negative_stock,
                    reorder_point_default:
                        inventory.reorder_point_default === null ||
                            inventory.reorder_point_default === undefined
                            ? null
                            : Number(inventory.reorder_point_default),
                }
                payload.pos_config = {
                    // receipt.width_mm is managed from Ticket POS — preserve existing value
                    receipt: {
                        ...(pos.receipt_width_mm != null ? { width_mm: Number(pos.receipt_width_mm) } : {}),
                    },
                    tax: {
                        // default_rate is managed from Configuración Fiscal — preserve existing value
                        ...(pos.default_tax_rate != null
                            ? { default_rate: pos.default_tax_rate > 1 ? pos.default_tax_rate / 100 : pos.default_tax_rate }
                            : {}),
                        price_includes_tax: !!pos.price_includes_tax,
                    },
                    return_window_days:
                        pos.return_window_days === null || pos.return_window_days === undefined
                            ? null
                            : Number(pos.return_window_days),
                    bulk_pricing_items: (pos.bulk_pricing_items || []).map((item: any) => ({
                        product_id: item.product_id,
                        product_name: item.product_name,
                        quantity: Number(item.quantity) || 1,
                        unit_price: Number(item.unit_price) || 0,
                        shortcut_letter: normalizeBakeryShortcutLetter(item.shortcut_letter) || null,
                    })),
                    store_credit: {
                        enabled: !!pos.store_credit_enabled,
                        single_use: !!pos.store_credit_single_use,
                        expiry_months:
                            pos.store_credit_expiry_months === null ||
                                pos.store_credit_expiry_months === undefined
                                ? null
                                : Number(pos.store_credit_expiry_months),
                    },
                }
                payload.settings = {
                    ...settingsBase,
                    documents: {
                        ...(settingsBase.documents || {}),
                        buyer_policy: {
                            ...(settingsBase.documents || {}).buyer_policy,
                            requireBuyerAboveAmount:
                                (docMinInvoice !== null && docMinInvoice !== undefined && Number(docMinInvoice) > 0)
                                    ? true
                                    : !!docRequireBuyer,
                            consumerFinalMaxTotal:
                                docMinInvoice === null || docMinInvoice === undefined
                                    ? null
                                    : Number(docMinInvoice),
                        },
                    },
                }
            } else {
                payload.invoice_config = parsedSettings.invoice
                payload.settings = {
                    ...settingsBase,
                    einvoicing: parsedSettings.einvoice,
                    purchases: parsedSettings.purchases,
                    expenses: parsedSettings.expenses,
                    finance: parsedSettings.finance,
                    hr: parsedSettings.hr,
                    sales: parsedSettings.sales,
                }
            }

            await tenantApi.put('/api/v1/company/settings', payload)
            clearCompanySettingsCache()
            await loadSettings()
            success('Configuracion guardada')
        } catch (err: any) {
            error(getErrorMessage(err))
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="p-4" style={{ maxWidth: 980 }}>
            <h2 className="font-semibold text-lg mb-2">
                {isAdminView ? 'Configuracion avanzada' : 'Operativo'}
            </h2>
            <p className="text-sm text-slate-600 mb-6">
                {isAdminView
                    ? 'Ajustes avanzados y configuracion tecnica del tenant.'
                    : 'Ajustes operativos clave para POS e inventario.'}
            </p>
            {!isCompanyAdmin && isAdminView && (
                <div className="mb-4 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
                    Solo administradores de empresa pueden editar esta seccion.
                </div>
            )}

            {loading && <div className="text-sm text-slate-500 mb-4">Loading...</div>}

            {!isAdminView && (
                <>
                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">Regional</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-sm mb-1">{t('settings:regional.locale')}</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    value={locale}
                                    onChange={(e) => setLocale(e.target.value)}
                                    placeholder="es-EC"
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">{t('settings:regional.timezone')}</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    value={timezone}
                                    onChange={(e) => setTimezone(e.target.value)}
                                    placeholder="America/Guayaquil"
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">{t('settings:regional.currency')}</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    value={currency}
                                    onChange={(e) => setCurrency(e.target.value)}
                                    placeholder="USD"
                                />
                            </div>
                        </div>
                    </section>
                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">{t('settings:advanced.inventory')}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={!!inventory.track_lots}
                                    onChange={(e) =>
                                        setInventory((prev) => ({ ...prev, track_lots: e.target.checked }))
                                    }
                                />
                                Rastrear lotes
                            </label>
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={!!inventory.track_expiry}
                                    onChange={(e) =>
                                        setInventory((prev) => ({ ...prev, track_expiry: e.target.checked }))
                                    }
                                />
                                Rastrear caducidad
                            </label>
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={!!inventory.allow_negative_stock}
                                    onChange={(e) =>
                                        setInventory((prev) => ({ ...prev, allow_negative_stock: e.target.checked }))
                                    }
                                />
                                Permitir stock negativo
                            </label>
                            <div>
                                <label className="block text-sm mb-1">Minimo de stock</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    value={inventory.reorder_point_default ?? ''}
                                    onChange={(e) =>
                                        setInventory((prev) => ({
                                            ...prev,
                                            reorder_point_default: e.target.value === '' ? null : Number(e.target.value),
                                        }))
                                    }
                                    min={0}
                                />
                            </div>
                        </div>
                    </section>
                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">POS</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-sm mb-1">Ventana devolucion (dias)</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    value={pos.return_window_days ?? ''}
                                    onChange={(e) =>
                                        setPos((prev) => ({
                                            ...prev,
                                            return_window_days: e.target.value === '' ? null : Number(e.target.value),
                                        }))
                                    }
                                    min={0}
                                />
                            </div>
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={!!pos.price_includes_tax}
                                    onChange={(e) =>
                                        setPos((prev) => ({ ...prev, price_includes_tax: e.target.checked }))
                                    }
                                />
                                Precios incluyen impuestos
                            </label>
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={!!pos.store_credit_enabled}
                                    onChange={(e) =>
                                        setPos((prev) => ({ ...prev, store_credit_enabled: e.target.checked }))
                                    }
                                />
                                Store credit habilitado
                            </label>
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={!!pos.store_credit_single_use}
                                    onChange={(e) =>
                                        setPos((prev) => ({ ...prev, store_credit_single_use: e.target.checked }))
                                    }
                                />
                                Store credit un solo uso
                            </label>
                            <div>
                                <label className="block text-sm mb-1">Expiracion store credit (meses)</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    value={pos.store_credit_expiry_months ?? ''}
                                    onChange={(e) =>
                                        setPos((prev) => ({
                                            ...prev,
                                            store_credit_expiry_months:
                                                e.target.value === '' ? null : Number(e.target.value),
                                        }))
                                    }
                                    min={0}
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">{t('settings:advanced.minForInvoice')}</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    value={docMinInvoice ?? ''}
                                    onChange={(e) =>
                                        setDocMinInvoice(e.target.value === '' ? null : Number(e.target.value))
                                    }
                                    min={0}
                                    step="0.01"
                                />
                            </div>
                            <label className="text-sm flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={docRequireBuyer}
                                    onChange={(e) => setDocRequireBuyer(e.target.checked)}
                                />
                                Requerir datos del comprador sobre ese monto
                            </label>
                        </div>
                    </section>

                    {showBakeryBulkPricing && (
                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">Venta por Cantidad (Panadería)</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Configura el precio fijo para una cantidad específica de cada producto (ej: 6 tapapados por $1)
                        </p>
                        <p className="text-xs text-gray-500 mb-4">
                            Cada producto puede tener una letra. En el POS esa letra vende 1 conjunto al instante;
                            si necesitas mas, pulsa la misma letra varias veces. Solo se permiten 10 letras distintas.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4 p-3 bg-gray-50 rounded">
                            <div>
                                <label className="block text-sm mb-1 font-medium">{t('settings:advanced.selectProduct')}</label>
                                <select
                                    className="border px-2 py-1 w-full rounded"
                                    value={bulkPricingForm.product_id}
                                    onChange={(e) =>
                                        setBulkPricingForm((prev) => {
                                            const product = products.find((p) => p.id === e.target.value)
                                            return {
                                                ...prev,
                                                product_id: e.target.value,
                                                product_name: product?.name || '',
                                            }
                                        })
                                    }
                                    disabled={productsLoading}
                                >
                                    <option value="">-- Seleccionar --</option>
                                    {products.map((product) => (
                                        <option key={product.id} value={product.id}>
                                            {product.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm mb-1 font-medium">Cantidad (unidades)</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    placeholder="6"
                                    value={bulkPricingForm.quantity}
                                    onChange={(e) =>
                                        setBulkPricingForm((prev) => ({
                                            ...prev,
                                            quantity: Number(e.target.value) || 0,
                                        }))
                                    }
                                    min={1}
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1 font-medium">Precio (por conjunto)</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    placeholder="1.00"
                                    value={bulkPricingForm.unit_price}
                                    onChange={(e) =>
                                        setBulkPricingForm((prev) => ({
                                            ...prev,
                                            unit_price: Number(e.target.value) || 0,
                                        }))
                                    }
                                    min={0}
                                    step="0.01"
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1 font-medium">Tecla</label>
                                <input
                                    className="border px-2 py-1 w-full rounded uppercase"
                                    type="text"
                                    placeholder="T"
                                    value={bulkPricingForm.shortcut_letter || ''}
                                    onChange={(e) =>
                                        setBulkPricingForm((prev) => ({
                                            ...prev,
                                            shortcut_letter: normalizeBakeryShortcutLetter(e.target.value),
                                        }))
                                    }
                                    maxLength={1}
                                />
                            </div>
                            <div className="flex items-end">
                                <button
                                    className="bg-green-600 text-white px-3 py-1.5 rounded w-full disabled:opacity-60"
                                    onClick={() => {
                                        if (!bulkPricingForm.product_id) {
                                            error(t('settings:advanced.mustSelectProduct'))
                                            return
                                        }
                                        if (bulkPricingForm.quantity <= 0) {
                                            error('La cantidad debe ser mayor a 0')
                                            return
                                        }

                                        const isDuplicate = pos.bulk_pricing_items?.some(
                                            (item) => item.product_id === bulkPricingForm.product_id
                                        )
                                        if (isDuplicate) {
                                            error('Este producto ya está en la lista. Edítalo o elimínalo primero.')
                                            return
                                        }

                                        const shortcutError = getBakeryShortcutValidationError(
                                            pos.bulk_pricing_items || [],
                                            bulkPricingForm.shortcut_letter,
                                            bulkPricingForm.product_id
                                        )
                                        if (shortcutError) {
                                            error(shortcutError)
                                            return
                                        }

                                        shouldAutoSaveBulk.current = true
                                        setPos((prev) => ({
                                            ...prev,
                                            bulk_pricing_items: [
                                                ...(prev.bulk_pricing_items || []),
                                                sanitizeBulkPricingItem(bulkPricingForm),
                                            ],
                                        }))

                                        setBulkPricingForm({
                                            product_id: '',
                                            quantity: 6,
                                            unit_price: 1.0,
                                            shortcut_letter: '',
                                        })
                                    }}
                                    disabled={productsLoading || !bulkPricingForm.product_id}
                                >
                                    Agregar
                                </button>
                            </div>
                        </div>

                        {/* Tabla de productos con bulk pricing */}
                        <div className="border rounded overflow-hidden">
                            <table className="w-full text-sm">
                                <thead className="bg-slate-50">
                                    <tr>
                                        <th className="text-left px-3 py-2">{t('settings:advanced.product')}</th>
                                        <th className="text-right px-3 py-2">{t('settings:advanced.quantity')}</th>
                                        <th className="text-right px-3 py-2">{t('settings:advanced.price')}</th>
                                        <th className="text-right px-3 py-2">Tecla</th>
                                        <th className="text-right px-3 py-2">Precio/Unidad</th>
                                        <th className="text-right px-3 py-2">Acción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(pos.bulk_pricing_items || []).length > 0 ? (
                                        (pos.bulk_pricing_items || []).map((item, idx) => {
                                            const pricePerUnit = item.unit_price / item.quantity
                                            return (
                                                <tr key={item.product_id} className="border-t">
                                                    <td className="px-3 py-2">
                                                        {item.product_name ||
                                                            products.find((p) => p.id === item.product_id)?.name ||
                                                            item.product_id}
                                                    </td>
                                                    <td className="px-3 py-2 text-right">{item.quantity}</td>
                                                    <td className="px-3 py-2 text-right">${item.unit_price.toFixed(2)}</td>
                                                    <td className="px-3 py-2 text-right">
                                                        {item.shortcut_letter ? (
                                                            <span className="inline-flex items-center rounded bg-slate-100 px-2 py-1 font-mono text-xs font-semibold">
                                                                {item.shortcut_letter}
                                                            </span>
                                                        ) : (
                                                            <span className="text-slate-400">-</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-right">${pricePerUnit.toFixed(4)}</td>
                                                    <td className="px-3 py-2 text-right">
                                                        <button
                                                            className="btn btn-sm ghost"
                                                            onClick={() => {
                                                                shouldAutoSaveBulk.current = true
                                                                setPos((prev) => ({
                                                                    ...prev,
                                                                    bulk_pricing_items: (
                                                                        prev.bulk_pricing_items || []
                                                                    ).filter((_, i) => i !== idx),
                                                                }))
                                                            }}
                                                        >
                                                            Eliminar
                                                        </button>
                                                    </td>
                                                </tr>
                                            )
                                        })
                                    ) : (
                                        <tr>
                                            <td
                                                className="px-3 py-4 text-center text-slate-500 text-sm"
                                                colSpan={6}
                                            >
                                                No hay productos configurados. Agrega uno arriba.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>
                    )}

                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">Numeracion</h3>
                        <div className="grid grid-cols-1 gap-6">
                            <div>
                                <div className="text-sm font-semibold mb-2">Contadores</div>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
                                    <div>
                                        <label className="block text-sm mb-1">Tipo</label>
                                        <select
                                            className="border px-2 py-1 w-full rounded"
                                            value={counterForm.doc_type}
                                            onChange={(e) => setCounterForm((prev) => ({ ...prev, doc_type: e.target.value }))}
                                        >
                                            {docTypesCatalog.length > 0
                                              ? docTypesCatalog.map(dt => (
                                                  <option key={dt.code} value={dt.code}>{dt.name}</option>
                                                ))
                                              : <>
                                                  <option value="pos_receipt">pos_receipt</option>
                                                  <option value="invoice">invoice</option>
                                                  <option value="sales_order">sales_order</option>
                                                  <option value="delivery">delivery</option>
                                                  <option value="purchase_order">purchase_order</option>
                                                </>
                                            }
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Anio</label>
                                        <input
                                            className="border px-2 py-1 w-full rounded"
                                            type="number"
                                            value={counterForm.year}
                                            onChange={(e) =>
                                                setCounterForm((prev) => ({ ...prev, year: Number(e.target.value) || 0 }))
                                            }
                                            min={2000}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Serie</label>
                                        <input
                                            className="border px-2 py-1 w-full rounded"
                                            value={counterForm.series}
                                            onChange={(e) => setCounterForm((prev) => ({ ...prev, series: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Numero actual</label>
                                        <input
                                            className="border px-2 py-1 w-full rounded"
                                            type="number"
                                            value={counterForm.current_no}
                                            onChange={(e) =>
                                                setCounterForm((prev) => ({ ...prev, current_no: Number(e.target.value) || 0 }))
                                            }
                                            min={0}
                                        />
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 mb-3">
                                    <button
                                        className="bg-blue-600 text-white px-3 py-1.5 rounded disabled:opacity-60"
                                        onClick={async () => {
                                            try {
                                                await tenantApi.put('/api/v1/tenant/pos/numbering/counters', {
                                                    doc_type: counterForm.doc_type,
                                                    year: counterForm.year,
                                                    series: counterForm.series,
                                                    current_no: counterForm.current_no,
                                                })
                                                success('Contador guardado')
                                                await loadNumbering()
                                            } catch (err: any) {
                                                error(getErrorMessage(err))
                                            }
                                        }}
                                        disabled={numberingLoading}
                                    >
                                        Save counter
                                    </button>
                                    <button
                                        className="btn ghost"
                                        onClick={() =>
                                            setCounterForm(resetToDefaults('COUNTER'))
                                        }
                                    >
                                        Limpiar
                                    </button>
                                </div>
                                <div className="border rounded overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="text-left px-3 py-2">Tipo</th>
                                                <th className="text-left px-3 py-2">Anio</th>
                                                <th className="text-left px-3 py-2">Serie</th>
                                                <th className="text-right px-3 py-2">Numero</th>
                                                <th className="text-left px-3 py-2">Actualizado</th>
                                                <th className="text-right px-3 py-2">Accion</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {numberingCounters.map((row) => (
                                                <tr key={`${row.doc_type}-${row.year}-${row.series}`} className="border-t">
                                                    <td className="px-3 py-2">{row.doc_type}</td>
                                                    <td className="px-3 py-2">{row.year}</td>
                                                    <td className="px-3 py-2">{row.series}</td>
                                                    <td className="px-3 py-2 text-right">{row.current_no}</td>
                                                    <td className="px-3 py-2">
                                                        {row.updated_at ? new Date(row.updated_at).toLocaleString() : '-'}
                                                    </td>
                                                    <td className="px-3 py-2 text-right">
                                                        <button
                                                            className="btn ghost"
                                                            onClick={() =>
                                                                setCounterForm({
                                                                    doc_type: row.doc_type,
                                                                    year: row.year,
                                                                    series: row.series,
                                                                    current_no: row.current_no,
                                                                })
                                                            }
                                                        >
                                                            Editar
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {numberingCounters.length === 0 && (
                                                <tr>
                                                    <td className="px-3 py-3 text-center text-slate-500" colSpan={6}>
                                                        {numberingLoading ? 'Loading...' : 'No counters'}
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div>
                                <div className="text-sm font-semibold mb-2">Series por caja</div>
                                <div className="grid grid-cols-1 md:grid-cols-6 gap-3 mb-3">
                                    <div>
                                        <label className="block text-sm mb-1">Register ID</label>
                                        <input
                                            className="border px-2 py-1 w-full rounded"
                                            placeholder="(opcional)"
                                            value={seriesForm.register_id}
                                            onChange={(e) => setSeriesForm((prev) => ({ ...prev, register_id: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Tipo</label>
                                        <select
                                            className="border px-2 py-1 w-full rounded"
                                            value={seriesForm.doc_type}
                                            onChange={(e) => setSeriesForm((prev) => ({ ...prev, doc_type: e.target.value }))}
                                        >
                                            {docTypesCatalog.length > 0
                                              ? docTypesCatalog.map(dt => (
                                                  <option key={dt.code} value={dt.code}>{dt.name}</option>
                                                ))
                                              : <>
                                                  <option value="R">R</option>
                                                  <option value="F">F</option>
                                                  <option value="C">C</option>
                                                </>
                                            }
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">{t('settings:advanced.name')}</label>
                                        <input
                                            className="border px-2 py-1 w-full rounded"
                                            value={seriesForm.name}
                                            onChange={(e) => setSeriesForm((prev) => ({ ...prev, name: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Numero actual</label>
                                        <input
                                            className="border px-2 py-1 w-full rounded"
                                            type="number"
                                            value={seriesForm.current_no}
                                            onChange={(e) =>
                                                setSeriesForm((prev) => ({ ...prev, current_no: Number(e.target.value) || 0 }))
                                            }
                                            min={0}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Reset</label>
                                        <select
                                            className="border px-2 py-1 w-full rounded"
                                            value={seriesForm.reset_policy}
                                            onChange={(e) =>
                                                setSeriesForm((prev) => ({ ...prev, reset_policy: e.target.value as 'yearly' | 'never' }))
                                            }
                                        >
                                            <option value="yearly">yearly</option>
                                            <option value="never">never</option>
                                        </select>
                                    </div>
                                    <div className="flex items-end">
                                        <label className="text-sm flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={seriesForm.active}
                                                onChange={(e) => setSeriesForm((prev) => ({ ...prev, active: e.target.checked }))}
                                            />
                                            Active
                                        </label>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 mb-3">
                                    <button
                                        className="bg-blue-600 text-white px-3 py-1.5 rounded disabled:opacity-60"
                                        onClick={async () => {
                                            try {
                                                await tenantApi.put('/api/v1/tenant/pos/numbering/series', {
                                                    id: seriesForm.id || undefined,
                                                    register_id: seriesForm.register_id || undefined,
                                                    doc_type: seriesForm.doc_type,
                                                    name: seriesForm.name,
                                                    current_no: seriesForm.current_no,
                                                    reset_policy: seriesForm.reset_policy,
                                                    active: seriesForm.active,
                                                })
                                                success('Serie guardada')
                                                setSeriesForm(resetToDefaults('DOC_SERIES'))
                                                await loadNumbering()
                                            } catch (err: any) {
                                                error(getErrorMessage(err))
                                            }
                                        }}
                                        disabled={docSeriesLoading}
                                    >
                                        Save series
                                    </button>
                                    <button
                                        className="btn ghost"
                                        onClick={() =>
                                            setSeriesForm(resetToDefaults('DOC_SERIES'))
                                        }
                                    >
                                        Limpiar
                                    </button>
                                    <button
                                        className="btn"
                                        onClick={() => setResetYearlyPending(true)}
                                        disabled={docSeriesLoading}
                                    >
                                        Reset anual
                                    </button>
                                </div>
                                <div className="border rounded overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="text-left px-3 py-2">{t('settings:advanced.name')}</th>
                                                <th className="text-left px-3 py-2">Tipo</th>
                                                <th className="text-left px-3 py-2">Register</th>
                                                <th className="text-right px-3 py-2">Numero</th>
                                                <th className="text-left px-3 py-2">Reset</th>
                                                <th className="text-left px-3 py-2">Activa</th>
                                                <th className="text-right px-3 py-2">Accion</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {docSeriesList.map((row) => (
                                                <tr key={row.id} className="border-t">
                                                    <td className="px-3 py-2">{row.name}</td>
                                                    <td className="px-3 py-2">{row.doc_type}</td>
                                                    <td className="px-3 py-2">{row.register_id || '-'}</td>
                                                    <td className="px-3 py-2 text-right">{row.current_no}</td>
                                                    <td className="px-3 py-2">{row.reset_policy}</td>
                                                    <td className="px-3 py-2">{row.active ? 'Yes' : 'No'}</td>
                                                    <td className="px-3 py-2 text-right">
                                                        <button
                                                            className="btn ghost"
                                                            onClick={() =>
                                                                setSeriesForm({
                                                                    id: row.id,
                                                                    register_id: row.register_id || '',
                                                                    doc_type: row.doc_type,
                                                                    name: row.name,
                                                                    current_no: row.current_no,
                                                                    reset_policy: row.reset_policy,
                                                                    active: row.active,
                                                                })
                                                            }
                                                        >
                                                            Editar
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                            {docSeriesList.length === 0 && (
                                                <tr>
                                                    <td className="px-3 py-3 text-center text-slate-500" colSpan={7}>
                                                        {docSeriesLoading ? 'Loading...' : 'No series'}
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </section>

                </>
            )}

            {isAdminView && (
                <>
                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">Facturacion (invoice_config)</h3>
                        <textarea
                            className="border px-2 py-2 w-full rounded font-mono text-sm"
                            rows={6}
                            value={invoiceJson}
                            onChange={(e) => setInvoiceJson(e.target.value)}
                        />
                    </section>

                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">E-Factura (settings.einvoicing)</h3>
                        <textarea
                            className="border px-2 py-2 w-full rounded font-mono text-sm"
                            rows={6}
                            value={einvoiceJson}
                            onChange={(e) => setEinvoiceJson(e.target.value)}
                        />
                    </section>

                    <section className="border rounded-lg p-4 mb-6">
                        <h3 className="font-semibold mb-3">Otros modulos</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm mb-1">Purchases</label>
                                <textarea
                                    className="border px-2 py-2 w-full rounded font-mono text-sm"
                                    rows={6}
                                    value={purchasesJson}
                                    onChange={(e) => setPurchasesJson(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">Expenses</label>
                                <textarea
                                    className="border px-2 py-2 w-full rounded font-mono text-sm"
                                    rows={6}
                                    value={expensesJson}
                                    onChange={(e) => setExpensesJson(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">Finance</label>
                                <textarea
                                    className="border px-2 py-2 w-full rounded font-mono text-sm"
                                    rows={6}
                                    value={financeJson}
                                    onChange={(e) => setFinanceJson(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">HR</label>
                                <textarea
                                    className="border px-2 py-2 w-full rounded font-mono text-sm"
                                    rows={6}
                                    value={hrJson}
                                    onChange={(e) => setHrJson(e.target.value)}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm mb-1">Sales</label>
                                <textarea
                                    className="border px-2 py-2 w-full rounded font-mono text-sm"
                                    rows={6}
                                    value={salesJson}
                                    onChange={(e) => setSalesJson(e.target.value)}
                                />
                            </div>
                        </div>
                    </section>
                </>
            )}

            <button
                className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-60"
                onClick={save}
                disabled={saving}
            >
                Save configuration
            </button>

            {resetYearlyPending && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
                        <h3 className="font-semibold text-lg mb-2">Reset anual</h3>
                        <p className="text-sm text-slate-600 mb-4">Resetear series yearly a 0. Esta acción no se puede deshacer.</p>
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setResetYearlyPending(false)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancelar</button>
                            <button
                                onClick={async () => {
                                    setResetYearlyPending(false)
                                    try {
                                        await tenantApi.post('/api/v1/tenant/pos/numbering/series/reset_yearly')
                                        success('Series reseteadas')
                                        await loadNumbering()
                                    } catch (err: any) {
                                        error(getErrorMessage(err))
                                    }
                                }}
                                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm"
                            >
                                Reset anual
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
