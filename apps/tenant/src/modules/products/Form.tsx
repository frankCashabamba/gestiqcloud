// apps/tenant/src/modules/productos/Form.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createProducto, getProducto, updateProducto, listCategorias, type Producto, type Categoria } from './productsApi'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'
import { useCurrency } from '../../hooks/useCurrency'
import { getCompanySettings, getDefaultReorderPoint } from '../../services/companySettings'

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
  const nav = useNavigate()
  const { symbol: currencySymbol } = useCurrency()
  const [form, setForm] = useState<Partial<Producto>>({
    sku: '',
    name: '',
    price: 0,
    iva_tasa: 0,
    active: true,
    stock: 0,
    unit: 'unit',
  })
  const { success, error } = useToast()
  const [fields, setFields] = useState<FieldCfg[] | null>(null)
  const [loadingCfg, setLoadingCfg] = useState(false)
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [minStockGlobal, setMinStockGlobal] = useState(0)

  // Cargar categorías disponibles
  useEffect(() => {
    ;(async () => {
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
    ;(async () => {
      try {
        setLoadingCfg(true)
        const q = new URLSearchParams({ module: 'products', ...(empresa ? { empresa } : {}) }).toString()
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

  useEffect(() => {
    let cancelled = false
    ;(async () => {
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

  const fieldList = useMemo(() => {
    const base: FieldCfg[] = [
      { field: 'sku', visible: true, required: false, ord: 10, label: 'Code', type: 'text', help: 'Dejar vacío para generar automáticamente' },
      { field: 'name', visible: true, required: true, ord: 20, label: 'Nombre', type: 'text' },
      { field: 'categoria', visible: true, required: false, ord: 22, label: 'Categoría', type: 'select' },
      { field: 'descripcion', visible: true, required: false, ord: 25, label: 'Description', type: 'textarea' },
      { field: 'price', visible: true, required: true, ord: 30, label: `Precio de venta (${currencySymbol})`, type: 'number' },
      { field: 'stock', visible: true, required: false, ord: 35, label: 'Stock inicial', type: 'number' },
      { field: 'iva_tasa', visible: true, required: false, ord: 40, label: 'IVA (%)', type: 'number' },
      { field: 'activo', visible: true, required: false, ord: 50, label: 'Activo', type: 'boolean' },
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

    return Array.from(map.values()).sort((a, b) => (a.ord || 999) - (b.ord || 999))
  }, [fields, currencySymbol])

  const BARCODE_META_FIELDS = ['codigo_barras', 'barcode', 'ean', 'upc'] as const
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
        throw new Error('El precio no puede ser negativo')
      }

      const metadata = { ...(((form.product_metadata ?? {}) as Record<string, unknown>) ?? {}) }
      const wholesaleMeta = (metadata.wholesale || {}) as Record<string, unknown>
      const wholesaleEnabled = wholesaleMeta.enabled !== false
      if (wholesaleEnabled && minStockGlobal > 0 && (Number(form.stock ?? 0) || 0) < minStockGlobal) {
        throw new Error(`No se permite activar mayorista si el stock inicial es menor al minimo de stock (${minStockGlobal}).`)
      }

      // Auto-cálculo de margen si existe precio_compra (guardar en metadata)
      if (form.precio_compra && form.price) {
        const margen = ((form.price - form.precio_compra) / form.precio_compra) * 100
        metadata.margen = parseFloat(margen.toFixed(2))
        setForm((prev) => ({ ...prev, product_metadata: metadata }))
      }

      const payload = prepareProductPayload(metadata) as Partial<Producto>

      if (id) await updateProducto(id, payload)
      else await createProducto(payload)

      success('Producto guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const generateSKU = () => {
    const categoria = (form as any).categoria || ''
    const prefix = categoria ? categoria.substring(0, 3).toUpperCase() : 'PRO'
    const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0')
    const sku = `${prefix}-${random}`
    setForm({ ...form, sku })
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
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder={f.help || 'Código del producto'}
          />
          <button
            type="button"
            onClick={generateSKU}
            className="px-4 py-2 bg-gray-100 border border-gray-300 rounded hover:bg-gray-200 transition-colors whitespace-nowrap"
            title="Generar código automático"
          >
            ⚡ Auto
          </button>
        </div>
      )
    }

    // Campo Categoría con select que carga desde BD
    if (f.field === 'categoria') {
      return (
        <select
          value={value}
          onChange={(e) => setForm({ ...form, categoria: e.target.value })}
          className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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

    switch (fieldType) {
      case 'number':
        return (
          <input
            type="number"
            step="0.01"
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: parseFloat(e.target.value) || 0 })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
              onChange={(e) => setForm({ ...form, [f.field]: e.target.checked })}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-600">{f.help || 'Sí/No'}</span>
          </label>
        )

      case 'textarea':
        return (
          <textarea
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={3}
            required={!!f.required}
            placeholder={f.help || ''}
          />
        )

      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
            onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
            className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{id ? 'Editar producto' : 'Nuevo producto'}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {id ? 'Modifica los datos del producto' : 'Completa el formulario para registrar un nuevo producto'}
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-6 bg-white shadow-sm rounded-lg p-6">
        {loadingCfg && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Loading field configuration...
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {fieldList.map((f) => (
            <div key={f.field} className={f.type === 'textarea' ? 'md:col-span-2' : ''}>
              <label className="block mb-2 font-medium text-gray-700 text-sm">
                {f.label || f.field.replace(/_/g, ' ')}
                {f.required && <span className="text-red-600 ml-1">*</span>}
              </label>
              {renderField(f)}
              {f.help && <p className="text-xs text-gray-500 mt-1">{f.help}</p>}
            </div>
          ))}
        </div>

        <div className="border-t pt-4">
          <h2 className="text-lg font-semibold text-gray-900">Precio mayorista</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configura condiciones por producto: cliente mayorista o minimos por cantidad.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            <div>
              <label className="block mb-2 font-medium text-gray-700 text-sm">Habilitar mayorista</label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={wholesaleEnabled}
                  onChange={(e) => updateWholesale({ enabled: e.target.checked })}
                  disabled={stockBelowGlobalMin && !wholesaleEnabled}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-600">Aplicar reglas de mayorista</span>
              </label>
              {minStockGlobal > 0 && (
                <p className="text-xs text-gray-500 mt-2">
                  Minimo global de stock: {minStockGlobal}
                </p>
              )}
              {stockBelowGlobalMin && (
                <p className="text-xs text-amber-600 mt-2">
                  El stock inicial ({stockValue}) esta por debajo del minimo de stock ({minStockGlobal}). No se permite activar mayorista.
                </p>
              )}
            </div>
            <div>
              <label className="block mb-2 font-medium text-gray-700 text-sm">Precio mayorista</label>
              <input
                type="number"
                step="0.01"
                value={wholesalePrice}
                onChange={(e) => updateWholesale({ price: Number(e.target.value) || 0 })}
                className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={`Ej: ${currencySymbol}8.50`}
              />
            </div>
            <div>
              <label className="block mb-2 font-medium text-gray-700 text-sm">Minimo (unidades)</label>
              <input
                type="number"
                step="1"
                min="0"
                value={wholesaleMinUnits}
                onChange={(e) => updateWholesale({ min_qty_units: Number(e.target.value) || 0 })}
                className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Ej: 12"
              />
            </div>
            <div>
              <label className="block mb-2 font-medium text-gray-700 text-sm">Aplicacion del precio</label>
              <select
                value={wholesaleApplyMode}
                onChange={(e) => updateWholesale({ apply_mode: e.target.value })}
                className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Todo el pedido</option>
                <option value="excess">Solo excedente</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block mb-2 font-medium text-gray-700 text-sm">Presentaciones (opcional)</label>
              <input
                type="text"
                value={packsInput}
                onChange={(e) => updatePacks(parseKeyValueNumberMap(e.target.value))}
                className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Formato: caja=12, bulto=24"
              />
              <p className="text-xs text-gray-500 mt-1">
                Define equivalencias por presentacion para futuros calculos.
              </p>
            </div>
            <div className="md:col-span-2">
              <label className="block mb-2 font-medium text-gray-700 text-sm">Minimo por presentacion</label>
              <input
                type="text"
                value={wholesaleMinByPackInput}
                onChange={(e) => updateWholesaleMinByPack(parseKeyValueNumberMap(e.target.value))}
                className="border px-3 py-2 w-full rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Formato: caja=1, bulto=1"
              />
              <p className="text-xs text-gray-500 mt-1">
                Si la venta se maneja por presentacion, aplica estos minimos.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-4 flex gap-3 border-t">
          <button
            type="submit"
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
          >
            {id ? 'Save changes' : 'Create product'}
          </button>
          <button
            type="button"
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium text-gray-700"
            onClick={() => nav('..')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
