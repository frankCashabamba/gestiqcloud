import React, { useEffect, useMemo, useState } from 'react'
import tenantApi from '../../shared/api/client'
import { getTenantSettings } from '../../services/tenantSettings'
import { getErrorMessage, useToast } from '../../shared/toast'

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

export default function AvanzadoSettings() {
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [locale, setLocale] = useState('')
  const [timezone, setTimezone] = useState('')
  const [currency, setCurrency] = useState('')
  const [inventory, setInventory] = useState<InventoryForm>({})
  const [pos, setPos] = useState<PosForm>({})
  const [invoiceJson, setInvoiceJson] = useState('{}')
  const [einvoiceJson, setEinvoiceJson] = useState('{}')
  const [purchasesJson, setPurchasesJson] = useState('{}')
  const [expensesJson, setExpensesJson] = useState('{}')
  const [financeJson, setFinanceJson] = useState('{}')
  const [hrJson, setHrJson] = useState('{}')
  const [salesJson, setSalesJson] = useState('{}')
  const [settingsBase, setSettingsBase] = useState<Record<string, any>>({})

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        const data = await getTenantSettings()
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
        setPos({
          receipt_width_mm: toNumberOrNull(receipt.width_mm),
          default_tax_rate: toNumberOrNull(tax.default_rate),
          return_window_days: toNumberOrNull(posConfig.return_window_days),
          price_includes_tax: tax.price_includes_tax ?? false,
          store_credit_enabled: storeCredit.enabled ?? false,
          store_credit_single_use: storeCredit.single_use ?? false,
          store_credit_expiry_months: toNumberOrNull(storeCredit.expiry_months),
        })

        const baseSettings = (data.settings || {}) as Record<string, any>
        setSettingsBase(baseSettings)
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
    })()
  }, [])

  const parsedSettings = useMemo(() => {
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
  }, [invoiceJson, einvoiceJson, purchasesJson, expensesJson, financeJson, hrJson, salesJson])

  const save = async () => {
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

    try {
      setSaving(true)
      const payload = {
        locale: locale || null,
        timezone: timezone || null,
        currency: currency || null,
        inventory: {
          track_lots: !!inventory.track_lots,
          track_expiry: !!inventory.track_expiry,
          allow_negative_stock: !!inventory.allow_negative_stock,
          reorder_point_default:
            inventory.reorder_point_default === null ||
            inventory.reorder_point_default === undefined
              ? null
              : Number(inventory.reorder_point_default),
        },
        pos_config: {
          receipt: {
            width_mm:
              pos.receipt_width_mm === null || pos.receipt_width_mm === undefined
                ? null
                : Number(pos.receipt_width_mm),
          },
          tax: {
            default_rate:
              pos.default_tax_rate === null || pos.default_tax_rate === undefined
                ? null
                : Number(pos.default_tax_rate),
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
        },
        invoice_config: parsedSettings.invoice,
        settings: {
          ...settingsBase,
          einvoicing: parsedSettings.einvoice,
          purchases: parsedSettings.purchases,
          expenses: parsedSettings.expenses,
          finance: parsedSettings.finance,
          hr: parsedSettings.hr,
          sales: parsedSettings.sales,
        },
      }

      await tenantApi.put('/api/v1/company/settings', payload)
      success('Configuracion guardada')
    } catch (err: any) {
      error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-4" style={{ maxWidth: 980 }}>
      <h2 className="font-semibold text-lg mb-2">Configuracion avanzada</h2>
      <p className="text-sm text-slate-600 mb-6">
        Ajustes operativos del tenant. Sin hardcode: cada empresa define sus valores.
      </p>

      {loading && <div className="text-sm text-slate-500 mb-4">Cargando...</div>}

      <section className="border rounded-lg p-4 mb-6">
        <h3 className="font-semibold mb-3">Regional</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">Locale</label>
            <input
              className="border px-2 py-1 w-full rounded"
              value={locale}
              onChange={(e) => setLocale(e.target.value)}
              placeholder="es-EC"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Timezone</label>
            <input
              className="border px-2 py-1 w-full rounded"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              placeholder="America/Guayaquil"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Moneda</label>
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
              onChange={(e) => setInventory((prev) => ({ ...prev, track_lots: e.target.checked }))}
            />
            Rastrear lotes
          </label>
          <label className="text-sm flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!inventory.track_expiry}
              onChange={(e) => setInventory((prev) => ({ ...prev, track_expiry: e.target.checked }))}
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
            <label className="block text-sm mb-1">Punto de reorden</label>
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
            <label className="block text-sm mb-1">IVA default (ej: 0.15)</label>
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
                  store_credit_expiry_months: e.target.value === '' ? null : Number(e.target.value),
                }))
              }
              min={0}
            />
          </div>
        </div>
      </section>

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

      <button
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-60"
        onClick={save}
        disabled={saving}
      >
        Guardar configuracion
      </button>
    </div>
  )
}
