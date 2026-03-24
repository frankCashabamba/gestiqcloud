import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BackButton } from '@ui'
import {
  createProveedor,
  getProveedor,
  updateProveedor,
  type ProveedorPayload,
  type ProveedorContacto,
  type ProveedorDireccion,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCountries, useTaxTypes } from '../../hooks/useGlobalCatalogs'

const emptyForm: ProveedorPayload = {
  name: '',
  nombre_comercial: null,
  nif: null,
  pais: 'ES',
  idioma: 'es',
  email: null,
  phone: null,
  tipo_impuesto: 'IVA',
  retencion_irpf: null,
  exento_impuestos: false,
  regimen_especial: null,
  condiciones_pago: null,
  plazo_pago_dias: 30,
  descuento_pronto_pago: null,
  divisa: null,
  metodo_pago: null,
  iban: null,
  iban_confirmacion: null,
  contactos: [],
  direcciones: [],
}

const emptyContacto: ProveedorContacto = {
  tipo: 'comercial',
  name: null,
  email: null,
  phone: null,
  notas: null,
}

const emptyDireccion: ProveedorDireccion = {
  tipo: 'facturacion',
  linea1: '',
  linea2: null,
  city: null,
  region: null,
  codigo_postal: null,
  pais: 'ES',
  notas: null,
}

export default function ProveedorForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['suppliers', 'common'])
  const [form, setForm] = useState<ProveedorPayload>(emptyForm)
  const [editMode, setEditMode] = useState(false)
  const [busy, setBusy] = useState(false)
  const { success, error: toastError } = useToast()
  const { items: countries } = useCountries()
  const { items: taxTypes } = useTaxTypes()

  useEffect(() => {
    if (!id) return
    setBusy(true)
    let cancelled = false
    ;(async () => {
      try {
        const proveedor = await getProveedor(id)
        if (cancelled) return
        setForm({
          name: proveedor.name,
          nombre_comercial: proveedor.nombre_comercial,
          nif: proveedor.nif,
          pais: proveedor.pais,
          idioma: proveedor.idioma,
          email: proveedor.email,
          phone: proveedor.phone,
          tipo_impuesto: proveedor.tipo_impuesto,
          retencion_irpf: proveedor.retencion_irpf,
          exento_impuestos: proveedor.exento_impuestos,
          regimen_especial: proveedor.regimen_especial,
          condiciones_pago: proveedor.condiciones_pago,
          plazo_pago_dias: proveedor.plazo_pago_dias,
          descuento_pronto_pago: proveedor.descuento_pronto_pago,
          divisa: proveedor.divisa,
          metodo_pago: proveedor.metodo_pago,
          iban: proveedor.iban,
          iban_confirmacion: proveedor.iban,
          contactos: proveedor.contactos || [],
          direcciones: proveedor.direcciones || [],
        })
        setEditMode(true)
      } catch (e: any) {
        if (!cancelled) {
          toastError(getErrorMessage(e))
        }
      } finally {
        if (!cancelled) {
          setBusy(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  const onSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    try {
      if (!form.name?.trim()) {
        throw new Error(t('suppliers:form.errors.nameRequired'))
      }
      if (form.iban && form.iban !== form.iban_confirmacion) {
        throw new Error(t('suppliers:form.errors.ibanMismatch'))
      }

      const payload = { ...form }
      delete payload.iban_confirmacion

      if (editMode && id) {
        await updateProveedor(id, payload)
        success(t('suppliers:messages.updated'))
      } else {
        await createProveedor(payload)
        success(t('suppliers:messages.created'))
      }
      nav('..')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const addContacto = () => {
    setForm({ ...form, contactos: [...form.contactos, { ...emptyContacto }] })
  }

  const removeContacto = (index: number) => {
    setForm({ ...form, contactos: form.contactos.filter((_, i) => i !== index) })
  }

  const updateContacto = (index: number, field: keyof ProveedorContacto, value: any) => {
    const updated = [...form.contactos]
    updated[index] = { ...updated[index], [field]: value }
    setForm({ ...form, contactos: updated })
  }

  const addDireccion = () => {
    setForm({ ...form, direcciones: [...form.direcciones, { ...emptyDireccion }] })
  }

  const removeDireccion = (index: number) => {
    setForm({ ...form, direcciones: form.direcciones.filter((_, i) => i !== index) })
  }

  const updateDireccion = (index: number, field: keyof ProveedorDireccion, value: any) => {
    const updated = [...form.direcciones]
    updated[index] = { ...updated[index], [field]: value }
    setForm({ ...form, direcciones: updated })
  }

  return (
    <div className="gc-container py-6 max-w-5xl">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <h3 className="gc-page-header__title mb-4">
        {editMode ? t('suppliers:form.titleEdit') : t('suppliers:form.title')}
      </h3>
      <form onSubmit={onSubmit} className="space-y-6">
        {/* Datos Generales */}
        <div className="gc-card">
          <h4 className="gc-section-title mb-4">{t('suppliers:detail.generalInfo')}</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">
                {t('suppliers:form.name')} <span className="text-rose-500">*</span>
              </span>
              <input
                className="gc-input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Trade Name</span>
              <input
                className="gc-input"
                value={form.nombre_comercial || ''}
                onChange={(e) => setForm({ ...form, nombre_comercial: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">NIF / Tax ID</span>
              <input
                className="gc-input"
                value={form.nif || ''}
                onChange={(e) => setForm({ ...form, nif: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Country</span>
              <select
                className="gc-input"
                value={form.pais || 'ES'}
                onChange={(e) => setForm({ ...form, pais: e.target.value || null })}
              >
                {countries.map(c => (
                  <option key={c.code} value={c.code}>{c.name}</option>
                ))}
                {countries.length === 0 && <option value={form.pais || 'ES'}>{form.pais || 'ES'}</option>}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Email</span>
              <input
                type="email"
                className="gc-input"
                value={form.email || ''}
                onChange={(e) => setForm({ ...form, email: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Phone</span>
              <input
                className="gc-input"
                value={form.phone || ''}
                onChange={(e) => setForm({ ...form, phone: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Web</span>
              <input
                type="url"
                className="gc-input"
                placeholder="https://"
                value={form.web || ''}
                onChange={(e) => setForm({ ...form, web: e.target.value || null })}
              />
            </label>
          </div>
        </div>

        {/* Configuración Fiscal */}
        <div className="gc-card">
          <h4 className="gc-section-title mb-4">{t('suppliers:detail.taxPayment')}</h4>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Tax Type</span>
              <select
                className="gc-input"
                value={form.tipo_impuesto || 'IVA'}
                onChange={(e) => setForm({ ...form, tipo_impuesto: e.target.value || null })}
              >
                {taxTypes.map(t => (
                  <option key={t.code} value={t.code}>{t.name}</option>
                ))}
                {taxTypes.length === 0 && <option value={form.tipo_impuesto || 'IVA'}>{form.tipo_impuesto || 'IVA'}</option>}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">IRPF Withholding (%)</span>
              <input
                type="number"
                step="0.01"
                className="gc-input"
                value={form.retencion_irpf || ''}
                onChange={(e) => setForm({ ...form, retencion_irpf: e.target.value ? parseFloat(e.target.value) : null })}
              />
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-600 pt-6">
              <input
                type="checkbox"
                checked={form.exento_impuestos || false}
                onChange={(e) => setForm({ ...form, exento_impuestos: e.target.checked })}
              />
              Tax exempt
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Payment Term (days)</span>
              <input
                type="number"
                className="gc-input"
                value={form.plazo_pago_dias || ''}
                onChange={(e) => setForm({ ...form, plazo_pago_dias: e.target.value ? parseInt(e.target.value) : null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Currency</span>
              <select
                className="gc-input"
                value={form.divisa || ''}
                onChange={(e) => setForm({ ...form, divisa: e.target.value || null })}
              >
                <option value="">(sin moneda)</option>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Payment Method</span>
              <select
                className="gc-input"
                value={form.metodo_pago || ''}
                onChange={(e) => setForm({ ...form, metodo_pago: e.target.value || null })}
              >
                <option value="">Select...</option>
                <option value="transferencia">Bank Transfer</option>
                <option value="efectivo">Cash</option>
                <option value="tarjeta">Card</option>
                <option value="pagare">Promissory Note</option>
              </select>
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 mt-4">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">IBAN</span>
              <input
                className="gc-input font-mono"
                value={form.iban || ''}
                onChange={(e) => setForm({ ...form, iban: e.target.value || null })}
                placeholder="ES00 0000 0000 0000 0000 0000"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Confirm IBAN</span>
              <input
                className="gc-input font-mono"
                value={form.iban_confirmacion || ''}
                onChange={(e) => setForm({ ...form, iban_confirmacion: e.target.value || null })}
                placeholder="ES00 0000 0000 0000 0000 0000"
              />
            </label>
          </div>
        </div>

        {/* Contactos */}
        <div className="gc-card">
          <div className="flex items-center justify-between mb-4">
            <h4 className="gc-section-title">Contacts</h4>
            <button
              type="button"
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
              onClick={addContacto}
            >
              + Add Contact
            </button>
          </div>
          {form.contactos.length === 0 && (
            <p className="text-sm text-slate-500">No contacts added.</p>
          )}
          <div className="space-y-4">
            {form.contactos.map((contacto, index) => (
              <div key={index} className="border border-slate-200 rounded-xl p-4 relative">
                <button
                  type="button"
                  className="absolute top-2 right-2 text-rose-600 hover:text-rose-500 text-sm"
                  onClick={() => removeContacto(index)}
                >
                  ✕
                </button>
                <div className="grid gap-3 sm:grid-cols-3">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Type</span>
                    <select
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.tipo}
                      onChange={(e) => updateContacto(index, 'tipo', e.target.value)}
                    >
                      <option value="facturacion">Billing</option>
                      <option value="entrega">Delivery</option>
                      <option value="administracion">Administration</option>
                      <option value="comercial">Commercial</option>
                      <option value="soporte">Support</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Name</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.name || ''}
                      onChange={(e) => updateContacto(index, 'name', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Email</span>
                    <input
                      type="email"
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.email || ''}
                      onChange={(e) => updateContacto(index, 'email', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Phone</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.phone || ''}
                      onChange={(e) => updateContacto(index, 'phone', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm sm:col-span-2">
                    <span className="font-medium text-slate-600">Notes</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.notas || ''}
                      onChange={(e) => updateContacto(index, 'notas', e.target.value || null)}
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Direcciones */}
        <div className="gc-card">
          <div className="flex items-center justify-between mb-4">
            <h4 className="gc-section-title">Addresses</h4>
            <button
              type="button"
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
              onClick={addDireccion}
            >
              + Add Address
            </button>
          </div>
          {form.direcciones.length === 0 && (
            <p className="text-sm text-slate-500">No addresses added.</p>
          )}
          <div className="space-y-4">
            {form.direcciones.map((direccion, index) => (
              <div key={index} className="border border-slate-200 rounded-xl p-4 relative">
                <button
                  type="button"
                  className="absolute top-2 right-2 text-rose-600 hover:text-rose-500 text-sm"
                  onClick={() => removeDireccion(index)}
                >
                  ✕
                </button>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Type</span>
                    <select
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.tipo}
                      onChange={(e) => updateDireccion(index, 'tipo', e.target.value)}
                    >
                      <option value="facturacion">Billing</option>
                      <option value="entrega">Delivery</option>
                      <option value="administracion">Administration</option>
                      <option value="otros">Other</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">
                      Address Line 1 <span className="text-rose-500">*</span>
                    </span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.linea1}
                      onChange={(e) => updateDireccion(index, 'linea1', e.target.value)}
                      required
                    />
                  </label>
                  <label className="space-y-1 text-sm sm:col-span-2">
                    <span className="font-medium text-slate-600">Address Line 2</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.linea2 || ''}
                      onChange={(e) => updateDireccion(index, 'linea2', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">City</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.city || ''}
                      onChange={(e) => updateDireccion(index, 'city', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Province / Region</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.region || ''}
                      onChange={(e) => updateDireccion(index, 'region', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Postal Code</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.codigo_postal || ''}
                      onChange={(e) => updateDireccion(index, 'codigo_postal', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Country</span>
                    <select
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.pais || 'ES'}
                      onChange={(e) => updateDireccion(index, 'pais', e.target.value || null)}
                    >
                      {countries.map(c => (
                        <option key={c.code} value={c.code}>{c.name}</option>
                      ))}
                      {countries.length === 0 && <option value={direccion.pais || 'ES'}>{direccion.pais || 'ES'}</option>}
                    </select>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Botones */}
        <div className="flex items-center gap-3">
          <button type="submit" className="gc-button gc-button--primary" disabled={busy}>
            {editMode ? t('suppliers:form.saveChanges') : t('suppliers:form.create')}
          </button>
          <button type="button" className="gc-button gc-button--ghost" onClick={() => nav('..')}>
            {t('common:cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
