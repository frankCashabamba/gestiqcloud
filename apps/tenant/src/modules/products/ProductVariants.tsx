import React, { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../../services/api/client'
import { useToast, getErrorMessage } from '../../shared/toast'

interface Attribute {
  id: string
  name: string
  values: string[]
}

interface Variant {
  id: string
  product_id: string
  sku: string | null
  attributes: Record<string, string>
  price: number | null
  cost: number | null
  barcode: string | null
  is_active: boolean
}

interface ProductVariantsProps {
  productId: string
  basePrice?: number
  currencySymbol?: string
}

const BASE = '/api/v1/tenant/products/variants'

export default function ProductVariants({ productId, basePrice, currencySymbol = '' }: ProductVariantsProps) {
  const { t } = useTranslation('products')
  const { error: toastError } = useToast()
  const [variants, setVariants] = useState<Variant[]>([])
  const [attributes, setAttributes] = useState<Attribute[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [showAttrForm, setShowAttrForm] = useState(false)
  const [deleteVariantTarget, setDeleteVariantTarget] = useState<string | null>(null)
  const [form, setForm] = useState<{
    sku: string
    attributes: Record<string, string>
    price: string
    cost: string
    barcode: string
  }>({ sku: '', attributes: {}, price: '', cost: '', barcode: '' })
  const [attrForm, setAttrForm] = useState({ name: '', values: '' })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [varsRes, attrsRes] = await Promise.all([
        api.get(`${BASE}/${productId}`),
        // Scoped to this product so attributes from other tenants are never exposed
        api.get(`${BASE}/attributes?product_id=${encodeURIComponent(productId)}`),
      ])
      setVariants(varsRes.data)
      setAttributes(attrsRes.data)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [productId])

  useEffect(() => { load() }, [load])

  const handleCreateAttribute = async () => {
    if (!attrForm.name.trim()) return
    setSaving(true)
    try {
      await api.post(`${BASE}/attributes`, {
        product_id: productId,
        name: attrForm.name.trim(),
        values: attrForm.values.split(',').map((v) => v.trim()).filter(Boolean),
      })
      setAttrForm({ name: '', values: '' })
      setShowAttrForm(false)
      load()
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAttribute = async (id: string) => {
    try {
      await api.delete(`${BASE}/attributes/${id}`)
      load()
    } catch (e) {
      toastError(getErrorMessage(e))
    }
  }

  const handleCreateVariant = async () => {
    setSaving(true)
    try {
      await api.post(BASE, {
        product_id: productId,
        sku: form.sku || null,
        attributes: form.attributes,
        price: form.price ? parseFloat(form.price) : null,
        cost: form.cost ? parseFloat(form.cost) : null,
        barcode: form.barcode || null,
      })
      setForm({ sku: '', attributes: {}, price: '', cost: '', barcode: '' })
      setShowForm(false)
      load()
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const handleToggleVariant = async (v: Variant) => {
    try {
      await api.put(`${BASE}/${v.id}`, { is_active: !v.is_active })
      load()
    } catch (e) {
      toastError(getErrorMessage(e))
    }
  }

  const handleDeleteVariant = (id: string) => {
    setDeleteVariantTarget(id)
  }

  const doDeleteVariant = async () => {
    if (!deleteVariantTarget) return
    try {
      await api.delete(`${BASE}/${deleteVariantTarget}`)
      setDeleteVariantTarget(null)
      load()
    } catch (e) {
      toastError(getErrorMessage(e))
    }
  }

  if (loading) return <div className="p-4 text-sm text-slate-400">Cargando variantes...</div>

  return (
    <div className="space-y-4">
      {/* Atributos */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">Atributos disponibles</span>
          <button
            onClick={() => setShowAttrForm(!showAttrForm)}
            className="text-xs px-2 py-1 text-blue-600 border border-blue-300 rounded hover:bg-blue-50"
          >
            + Nuevo atributo
          </button>
        </div>
        {showAttrForm && (
          <div className="border rounded p-3 bg-slate-50 space-y-2 mb-3">
            <input
              type="text"
              placeholder="Nombre (ej: Talla)"
              className="w-full border rounded px-2 py-1.5 text-sm"
              value={attrForm.name}
              onChange={(e) => setAttrForm((f) => ({ ...f, name: e.target.value }))}
            />
            <input
              type="text"
              placeholder="Valores separados por coma (ej: S, M, L, XL)"
              className="w-full border rounded px-2 py-1.5 text-sm"
              value={attrForm.values}
              onChange={(e) => setAttrForm((f) => ({ ...f, values: e.target.value }))}
            />
            <div className="flex gap-2">
              <button
                onClick={handleCreateAttribute}
                disabled={saving}
                className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
              >
                Guardar
              </button>
              <button onClick={() => setShowAttrForm(false)} className="px-3 py-1.5 border rounded text-sm">
                Cancelar
              </button>
            </div>
          </div>
        )}
        {attributes.length === 0 ? (
          <p className="text-xs text-slate-400">Sin atributos. Crea uno para empezar.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {attributes.map((a) => (
              <div key={a.id} className="flex items-center gap-1.5 bg-white border rounded px-2 py-1 text-xs">
                <span className="font-medium">{a.name}:</span>
                <span className="text-slate-500">{a.values.join(', ')}</span>
                <button
                  onClick={() => handleDeleteAttribute(a.id)}
                  className="ml-1 text-slate-400 hover:text-red-500"
                  title="Eliminar atributo"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Variantes */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">
            Variantes ({variants.filter((v) => v.is_active).length} activas)
          </span>
          <button
            onClick={() => setShowForm(!showForm)}
            disabled={attributes.length === 0}
            className="text-xs px-2 py-1 text-blue-600 border border-blue-300 rounded hover:bg-blue-50 disabled:opacity-40"
            title={attributes.length === 0 ? 'Crea atributos primero' : undefined}
          >
            + Nueva variante
          </button>
        </div>

        {showForm && (
          <div className="border rounded p-3 bg-slate-50 space-y-2 mb-3">
            {/* Atributos de la variante */}
            {attributes.map((attr) => (
              <div key={attr.id} className="flex items-center gap-2">
                <label className="text-xs w-20 shrink-0">{attr.name}</label>
                <select
                  className="flex-1 border rounded px-2 py-1 text-sm"
                  value={form.attributes[attr.name] || ''}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      attributes: { ...f.attributes, [attr.name]: e.target.value },
                    }))
                  }
                >
                  <option value="">— Seleccionar —</option>
                  {attr.values.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
            ))}
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-slate-500">SKU</label>
                <input
                  type="text"
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={form.sku}
                  onChange={(e) => setForm((f) => ({ ...f, sku: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">Precio (vacío = base {basePrice ?? '—'})</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={form.price}
                  onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">Código de barras</label>
                <input
                  type="text"
                  className="w-full border rounded px-2 py-1 text-sm"
                  value={form.barcode}
                  onChange={(e) => setForm((f) => ({ ...f, barcode: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreateVariant}
                disabled={saving}
                className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
              >
                Guardar variante
              </button>
              <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-sm">
                Cancelar
              </button>
            </div>
          </div>
        )}

        {variants.length === 0 ? (
          <p className="text-xs text-slate-400">Sin variantes.</p>
        ) : (
          <div className="border rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="px-3 py-2 text-left text-slate-500 font-medium">Atributos</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-medium">SKU</th>
                  <th className="px-3 py-2 text-right text-slate-500 font-medium">Precio</th>
                  <th className="px-3 py-2 text-left text-slate-500 font-medium">Barcode</th>
                  <th className="px-3 py-2 text-center text-slate-500 font-medium">Estado</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {variants.map((v) => (
                  <tr key={v.id} className={!v.is_active ? 'opacity-40' : ''}>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(v.attributes).map(([k, val]) => (
                          <span key={k} className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded text-xs">
                            {k}: {val}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2 font-mono text-slate-600">{v.sku || '—'}</td>
                    <td className="px-3 py-2 text-right">
                      {v.price != null ? `${currencySymbol}${v.price.toFixed(2)}` : <span className="text-slate-400">base</span>}
                    </td>
                    <td className="px-3 py-2 text-slate-500">{v.barcode || '—'}</td>
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => handleToggleVariant(v)}
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          v.is_active
                            ? 'bg-green-100 text-green-700'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {v.is_active ? 'Activa' : 'Inactiva'}
                      </button>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => handleDeleteVariant(v.id)}
                        className="text-slate-400 hover:text-red-500"
                        title="Eliminar"
                      >
                        🗑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: confirmar eliminación de variante */}
      {deleteVariantTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">
              {t('deleteVariantConfirm', { defaultValue: '¿Eliminar esta variante?' })}
            </h3>
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setDeleteVariantTarget(null)}
                className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm"
              >
                {t('cancel', { defaultValue: 'Cancelar' })}
              </button>
              <button
                onClick={doDeleteVariant}
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm"
              >
                {t('delete', { defaultValue: 'Eliminar' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
