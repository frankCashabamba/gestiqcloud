import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createFactura, getFactura, updateFactura, clearInvoicesCache, type InvoiceLine } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'

interface FormT {
  numero?: string
  fecha: string
  cliente_id?: number
  cliente_nombre?: string
  descripcion?: string
  lineas: InvoiceLine[]
  subtotal: number
  iva_porcentaje: number
  iva: number
  total: number
  estado?: string
  notas?: string
}

export default function FacturaForm() {
  const { t } = useTranslation()
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const { config } = useCompanyConfig()
  const currency = config?.settings?.currency || '€'
  const today = new Date().toISOString().slice(0, 10)
  const isNew = !id
  
  const [form, setForm] = useState<FormT>({
    numero: '',
    fecha: today,
    cliente_id: undefined,
    cliente_nombre: '',
    descripcion: '',
    lineas: [{ cantidad: 1, precio_unitario: 0, total: 0, description: '' }],
    subtotal: 0,
    iva_porcentaje: 21,
    iva: 0,
    total: 0,
    estado: 'draft',
    notas: '',
  })
  const [loading, setLoading] = useState(false)
  const isLocked = form.estado !== 'draft' && form.estado !== 'borrador'

  useEffect(() => {
    if (id) {
      setLoading(true)
      getFactura(id)
        .then((x: any) => {
          console.log('Invoice loaded from API:', x)
          console.log('Lines from API:', x?.lineas)
          setForm({
            numero: x?.numero || '',
            fecha: x?.fecha || today,
            cliente_id: x?.cliente_id,
            cliente_nombre: x?.cliente_nombre || '',
            descripcion: x?.descripcion || '',
            lineas: x?.lineas || [{ cantidad: 1, precio_unitario: 0, total: 0, description: '' }],
            subtotal: Number(x?.subtotal || 0),
            iva_porcentaje: x?.iva_porcentaje || 21,
            iva: Number(x?.iva || 0),
            total: Number(x?.total || 0),
            estado: x?.estado || 'draft',
            notas: x?.notas || '',
          })
        })
        .catch((err) => {
          console.error('Error loading invoice:', err)
        })
        .finally(() => setLoading(false))
    }
  }, [id, today])

  const updateLineTotal = (index: number, linea: InvoiceLine) => {
    linea.total = linea.cantidad * linea.precio_unitario
    const newLineas = [...form.lineas]
    newLineas[index] = linea
    const newSubtotal = newLineas.reduce((sum, l) => sum + l.total, 0)
    const newIva = newSubtotal * (form.iva_porcentaje / 100)
    const newTotal = newSubtotal + newIva
    
    setForm({
      ...form,
      lineas: newLineas,
      subtotal: newSubtotal,
      iva: newIva,
      total: newTotal,
    })
  }

  const addLine = () => {
    setForm({
      ...form,
      lineas: [...form.lineas, { cantidad: 1, precio_unitario: 0, total: 0, description: '' }],
    })
  }

  const removeLine = (index: number) => {
    const newLineas = form.lineas.filter((_, i) => i !== index)
    const newSubtotal = newLineas.reduce((sum, l) => sum + l.total, 0)
    const newIva = newSubtotal * (form.iva_porcentaje / 100)
    const newTotal = newSubtotal + newIva
    
    setForm({
      ...form,
      lineas: newLineas,
      subtotal: newSubtotal,
      iva: newIva,
      total: newTotal,
    })
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    if (isLocked) return
    try {
      if (!form.fecha) throw new Error(t('billing.errors.dateRequired'))
      if (form.lineas.length === 0) throw new Error(t('billing.sectorInvoice.errors.atLeastOneLine'))
      if (form.lineas.some(l => !l.description || l.cantidad <= 0)) throw new Error(t('billing.errors.validationError'))
      if (form.total < 0) throw new Error(t('billing.errors.totalNonNegative'))
      
      const payload = {
        numero: form.numero || undefined,
        fecha: form.fecha,
        cliente_id: form.cliente_id,
        cliente_nombre: form.cliente_nombre,
        descripcion: form.descripcion,
        lineas: form.lineas,
        subtotal: form.subtotal,
        iva_porcentaje: form.iva_porcentaje,
        iva: form.iva,
        total: form.total,
        estado: form.estado,
        notas: form.notas,
      }
      
      if (id) await updateFactura(id, payload as any)
      else await createFactura(payload as any)
      
      // Limpiar cache para que la lista se actualice
      clearInvoicesCache()
      
      success(t('billing.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-4">{id ? t('billing.editTitle') : t('billing.newTitle')}</h3>
      
      {isLocked && (
        <div className="mb-4 rounded border border-amber-300 bg-amber-50 text-amber-800 px-3 py-2 text-sm">
          {t('billing.status.issued')} · {t('common.readonly') || 'Solo lectura'}
        </div>
      )}
      
      {loading ? (
        <div className="text-gray-500">{t('common.loading')}</div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-6">
          {/* Header Section */}
          <div className="border-b pb-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">{t('common.date')}</label>
              <input
                type="date"
                value={form.fecha}
                onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                className="border px-2 py-1 w-full rounded text-sm"
                disabled={isLocked}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">{t('billing.invoiceNumber')}</label>
              <input
                type="text"
                value={form.numero}
                onChange={(e) => setForm({ ...form, numero: e.target.value })}
                placeholder={isNew ? '' : t('billing.numberPlaceholder')}
                className="border px-2 py-1 w-full rounded text-sm"
                disabled={isLocked || isNew}
              />
              {isNew && (
                <p className="text-xs text-gray-500 mt-1">
                  {t('billing.numberAutoPlaceholder') || 'Se asignara automaticamente al guardar'}
                </p>
              )}
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">{t('common.status')}</label>
              <select
                value={form.estado}
                onChange={(e) => setForm({ ...form, estado: e.target.value })}
                className="border px-2 py-1 w-full rounded text-sm"
                disabled={isLocked}
              >
                <option value="draft">{t('billing.status.draft')}</option>
                <option value="issued">{t('billing.status.issued')}</option>
                <option value="voided">{t('billing.status.voided')}</option>
              </select>
            </div>
          </div>

          {/* Customer Section */}
          <div className="border-b pb-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">{t('common.category')} ID</label>
              <input
                type="number"
                value={form.cliente_id || ''}
                onChange={(e) => setForm({ ...form, cliente_id: e.target.value ? Number(e.target.value) : undefined })}
                className="border px-2 py-1 w-full rounded text-sm"
                disabled={isLocked}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">{t('common.category')} {t('common.name')}</label>
              <input
                type="text"
                value={form.cliente_nombre}
                onChange={(e) => setForm({ ...form, cliente_nombre: e.target.value })}
                placeholder="Nombre del cliente"
                className="border px-2 py-1 w-full rounded text-sm"
                disabled={isLocked}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">{t('common.description')}</label>
              <textarea
                value={form.descripcion}
                onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
                rows={2}
                className="border px-2 py-1 w-full rounded text-sm"
                disabled={isLocked}
              />
            </div>
          </div>

          {/* Line Items Section */}
          <div className="border-b pb-4">
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-medium text-sm">{t('billing.sectorInvoice.lines')}</h4>
              <button
                type="button"
                onClick={addLine}
                className={`px-3 py-1 rounded text-sm ${isLocked ? 'bg-gray-300 text-gray-600 cursor-not-allowed' : 'bg-green-600 text-white'}`}
                disabled={isLocked}
              >
                {isLocked ? (t('common.readonly') || 'Solo lectura') : t('billing.sectorInvoice.addLine')}
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm border">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border p-2 text-left">{t('billing.sectorInvoice.fields.description')}</th>
                    <th className="border p-2 text-center w-20">{t('billing.sectorInvoice.fields.quantity')}</th>
                    <th className="border p-2 text-right w-24">{t('billing.sectorInvoice.fields.unitPrice')}</th>
                    <th className="border p-2 text-right w-24">{t('common.total')}</th>
                    <th className="border p-2 text-center w-12">{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {form.lineas.map((linea, idx) => (
                    <tr key={idx}>
                      <td className="border p-2">
                        <input
                          type="text"
                          value={linea.description}
                      onChange={(e) =>
                        updateLineTotal(idx, { ...linea, description: e.target.value })
                      }
                      className="border px-2 py-1 w-full rounded text-sm"
                      disabled={isLocked}
                      required
                    />
                  </td>
                      <td className="border p-2">
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={linea.cantidad}
                      onChange={(e) =>
                        updateLineTotal(idx, { ...linea, cantidad: Number(e.target.value) })
                      }
                      className="border px-2 py-1 w-full rounded text-sm text-center"
                      disabled={isLocked}
                      required
                    />
                  </td>
                      <td className="border p-2">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={linea.precio_unitario}
                      onChange={(e) =>
                        updateLineTotal(idx, { ...linea, precio_unitario: Number(e.target.value) })
                      }
                      className="border px-2 py-1 w-full rounded text-sm text-right"
                      disabled={isLocked}
                      required
                    />
                  </td>
                      <td className="border p-2 text-right">
                        {currency}{linea.total.toFixed(2)}
                      </td>
                      <td className="border p-2 text-center">
                        <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      className="text-red-600 hover:text-red-800 text-sm"
                      disabled={isLocked}
                    >
                      {t('billing.sectorInvoice.remove')}
                    </button>
                  </td>
                </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals Section */}
          <div className="border-b pb-4 flex justify-end">
            <div className="w-64 space-y-2">
              <div className="flex justify-between text-sm">
                <span>{t('billing.sectorInvoice.subtotal')}</span>
                <span>{currency}{form.subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <label className="flex items-center gap-2">
                  <span>{t('billing.sectorInvoice.vat')} (%)</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={form.iva_porcentaje}
                    onChange={(e) => {
                      const pct = Number(e.target.value)
                      const newIva = form.subtotal * (pct / 100)
                      setForm({
                        ...form,
                        iva_porcentaje: pct,
                        iva: newIva,
                        total: form.subtotal + newIva,
                      })
                    }}
                    className="border px-2 py-1 w-16 rounded text-sm text-right"
                    disabled={isLocked}
                  />
                </label>
                <span>{currency}{form.iva.toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-semibold border-t pt-2">
                <span>{t('common.total')}</span>
                <span>{currency}{form.total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Notes Section */}
          <div>
            <label className="block text-sm font-medium mb-1">{t('common.notes')}</label>
            <textarea
              value={form.notas}
              onChange={(e) => setForm({ ...form, notas: e.target.value })}
              rows={3}
              placeholder={t('billing.notesPlaceholder')}
              className="border px-2 py-1 w-full rounded text-sm"
              disabled={isLocked}
            />
          </div>

          {/* Form Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              className={`px-4 py-2 rounded ${isLocked ? 'bg-gray-300 text-gray-600 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'}`}
              disabled={isLocked}
            >
              {isLocked ? t('common.readonly') || 'Solo lectura' : t('common.save')}
            </button>
            <button
              type="button"
              onClick={() => nav('..')}
              className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
            >
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

