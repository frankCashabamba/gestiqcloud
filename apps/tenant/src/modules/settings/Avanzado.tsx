import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import tenantApi from '../../shared/api/client'
import { clearCompanySettingsCache, getCompanySettings } from '../../services/companySettings'
import { getErrorMessage, useToast } from '../../shared/toast'
import { useAuth } from '../../auth/AuthContext'
import { NUMBERING_DEFAULTS, resetToDefaults } from '../../constants/defaults'

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

export default function AvanzadoSettings({ variant = 'admin' }: AvanzadoSettingsProps) {
    const { t } = useTranslation()
    const { success, error } = useToast()
    const { profile } = useAuth()
    const isCompanyAdmin = Boolean(
        (profile as any)?.is_company_admin ||
        (profile as any)?.is_company_admi ||
        profile?.es_admin_empresa
    )
    const isAdminView = variant === 'admin'
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

    useEffect(() => {
        void loadSettings()
        if (variant !== 'admin') {
            void loadNumbering()
        }
    }, [variant])

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
                const taxDefaultRate =
                    pos.default_tax_rate === null || pos.default_tax_rate === undefined
                        ? null
                        : Number(pos.default_tax_rate)
                const taxDefaultRateDecimal =
                    taxDefaultRate === null || !Number.isFinite(taxDefaultRate)
                        ? null
                        : taxDefaultRate > 1
                            ? taxDefaultRate / 100
                            : taxDefaultRate
                payload.pos_config = {
                    receipt: {
                        width_mm:
                            pos.receipt_width_mm === null || pos.receipt_width_mm === undefined
                                ? null
                                : Number(pos.receipt_width_mm),
                    },
                    tax: {
                        default_rate: taxDefaultRateDecimal,
                        price_includes_tax: !!pos.price_includes_tax,
                    },
                    return_window_days:
                        pos.return_window_days === null || pos.return_window_days === undefined
                            ? null
                            : Number(pos.return_window_days),
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
                                <label className="block text-sm mb-1">{t('settings.regional.locale')}</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    value={locale}
                                    onChange={(e) => setLocale(e.target.value)}
                                    placeholder="es-EC"
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">{t('settings.regional.timezone')}</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    value={timezone}
                                    onChange={(e) => setTimezone(e.target.value)}
                                    placeholder="America/Guayaquil"
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">{t('settings.regional.currency')}</label>
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
                        <h3 className="font-semibold mb-3">Inventario</h3>
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
                                <label className="block text-sm mb-1">Ancho ticket (mm)</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    value={pos.receipt_width_mm ?? ''}
                                    onChange={(e) =>
                                        setPos((prev) => ({
                                            ...prev,
                                            receipt_width_mm: e.target.value === '' ? null : Number(e.target.value),
                                        }))
                                    }
                                    min={0}
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1">IVA default (%)</label>
                                <input
                                    className="border px-2 py-1 w-full rounded"
                                    type="number"
                                    value={pos.default_tax_rate ?? ''}
                                    onChange={(e) =>
                                        setPos((prev) => ({
                                            ...prev,
                                            default_tax_rate: e.target.value === '' ? null : Number(e.target.value),
                                        }))
                                    }
                                    min={0}
                                    step="0.01"
                                />
                            </div>
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
                                <label className="block text-sm mb-1">Minimo para exigir factura</label>
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
                                            <option value="pos_receipt">pos_receipt</option>
                                            <option value="invoice">invoice</option>
                                            <option value="sales_order">sales_order</option>
                                            <option value="delivery">delivery</option>
                                            <option value="purchase_order">purchase_order</option>
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
                                            <option value="R">R</option>
                                            <option value="F">F</option>
                                            <option value="C">C</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm mb-1">Nombre</label>
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
                                        onClick={async () => {
                                            if (!confirm('Resetear series yearly a 0?')) return
                                            try {
                                                await tenantApi.post('/api/v1/tenant/pos/numbering/series/reset_yearly')
                                                success('Series reseteadas')
                                                await loadNumbering()
                                            } catch (err: any) {
                                                error(getErrorMessage(err))
                                            }
                                        }}
                                        disabled={docSeriesLoading}
                                    >
                                        Reset anual
                                    </button>
                                </div>
                                <div className="border rounded overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="text-left px-3 py-2">Nombre</th>
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
        </div>
    )
}
