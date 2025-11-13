// apps/tenant/src/modules/productos/Form.tsx
import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createProducto, getProducto, updateProducto, type Producto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'
import { useCurrency } from '../../hooks/useCurrency'

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

type Categoria = {
  id: string
  name: string
  description?: string | null
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

  // Cargar categorías disponibles
  useEffect(() => {
    ;(async () => {
      try {
        const data = await apiFetch<Categoria[]>('/api/v1/tenant/products/product-categories')
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
        const q = new URLSearchParams({ module: 'productos', ...(empresa ? { empresa } : {}) }).toString()
        const data = await apiFetch<{ items?: FieldCfg[] }>(`/api/v1/tenant/settings/fields?${q}`)
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
      { field: 'sku', visible: true, required: false, ord: 10, label: 'Código', type: 'text', help: 'Dejar vacío para generar automáticamente' },
      { field: 'name', visible: true, required: true, ord: 20, label: 'Nombre', type: 'text' },
      { field: 'categoria', visible: true, required: false, ord: 22, label: 'Categoría', type: 'select' },
      { field: 'descripcion', visible: true, required: false, ord: 25, label: 'Descripción', type: 'textarea' },
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

      // Auto-cálculo de margen si existe precio_compra (guardar en metadata)
      if (form.precio_compra && form.price) {
        const margen = ((form.price - form.precio_compra) / form.precio_compra) * 100
        const metadata = form.product_metadata || {}
        metadata.margen = parseFloat(margen.toFixed(2))
        setForm((prev) => ({ ...prev, product_metadata: metadata }))
      }

      if (id) await updateProducto(id, form)
      else await createProducto(form)

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
            Cargando configuración de campos...
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

        <div className="pt-4 flex gap-3 border-t">
          <button
            type="submit"
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
          >
            {id ? 'Guardar cambios' : 'Crear producto'}
          </button>
          <button
            type="button"
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium text-gray-700"
            onClick={() => nav('..')}
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
