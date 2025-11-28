import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createProveedor,
  getProveedor,
  updateProveedor,
  type ProveedorPayload,
  type ProveedorContacto,
  type ProveedorDireccion,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

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
  divisa: 'EUR',
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
  const [form, setForm] = useState<ProveedorPayload>(emptyForm)
  const [editMode, setEditMode] = useState(false)
  const [busy, setBusy] = useState(false)
  const { success, error: toastError } = useToast()

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
        throw new Error('Name is required')
      }
      if (form.iban && form.iban !== form.iban_confirmacion) {
        throw new Error('Los IBAN no coinciden')
      }

      const payload = { ...form }
      delete payload.iban_confirmacion

      if (editMode && id) {
        await updateProveedor(id, payload)
        success('Proveedor actualizado')
      } else {
        await createProveedor(payload)
        success('Proveedor creado')
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
    <div className="p-4 max-w-5xl">
      <h3 className="text-xl font-semibold text-slate-900 mb-4">
        {editMode ? 'Editar proveedor' : 'Nuevo proveedor'}
      </h3>
      <form onSubmit={onSubmit} className="space-y-6">
        {/* Datos Generales */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h4 className="text-base font-semibold text-slate-700 mb-4">Datos Generales</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">
                Nombre / Razón Social <span className="text-rose-500">*</span>
              </span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Nombre Comercial</span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.nombre_comercial || ''}
                onChange={(e) => setForm({ ...form, nombre_comercial: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">NIF / Tax ID</span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.nif || ''}
                onChange={(e) => setForm({ ...form, nif: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">País</span>
              <select
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.pais || 'ES'}
                onChange={(e) => setForm({ ...form, pais: e.target.value || null })}
              >
                <option value="ES">España</option>
                <option value="EC">Ecuador</option>
                <option value="FR">Francia</option>
                <option value="DE">Alemania</option>
                <option value="IT">Italia</option>
                <option value="PT">Portugal</option>
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Email</span>
              <input
                type="email"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.email || ''}
                onChange={(e) => setForm({ ...form, email: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Teléfono</span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.phone || ''}
                onChange={(e) => setForm({ ...form, phone: e.target.value || null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Web</span>
              <input
                type="url"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                placeholder="https://"
                value={form.web || ''}
                onChange={(e) => setForm({ ...form, web: e.target.value || null })}
              />
            </label>
          </div>
        </div>

        {/* Configuración Fiscal */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h4 className="text-base font-semibold text-slate-700 mb-4">Configuración Fiscal y Pagos</h4>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Tipo Impuesto</span>
              <select
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.tipo_impuesto || 'IVA'}
                onChange={(e) => setForm({ ...form, tipo_impuesto: e.target.value || null })}
              >
                <option value="IVA">IVA</option>
                <option value="IGIC">IGIC</option>
                <option value="IPSI">IPSI</option>
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Retención IRPF (%)</span>
              <input
                type="number"
                step="0.01"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
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
              Exento de impuestos
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Plazo Pago (días)</span>
              <input
                type="number"
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.plazo_pago_dias || ''}
                onChange={(e) => setForm({ ...form, plazo_pago_dias: e.target.value ? parseInt(e.target.value) : null })}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Divisa</span>
              <select
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.divisa || 'EUR'}
                onChange={(e) => setForm({ ...form, divisa: e.target.value || null })}
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Método de Pago</span>
              <select
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.metodo_pago || ''}
                onChange={(e) => setForm({ ...form, metodo_pago: e.target.value || null })}
              >
                <option value="">Seleccionar...</option>
                <option value="transferencia">Transferencia</option>
                <option value="efectivo">Efectivo</option>
                <option value="tarjeta">Tarjeta</option>
                <option value="pagare">Pagaré</option>
              </select>
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 mt-4">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">IBAN</span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-mono"
                value={form.iban || ''}
                onChange={(e) => setForm({ ...form, iban: e.target.value || null })}
                placeholder="ES00 0000 0000 0000 0000 0000"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Confirmar IBAN</span>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-mono"
                value={form.iban_confirmacion || ''}
                onChange={(e) => setForm({ ...form, iban_confirmacion: e.target.value || null })}
                placeholder="ES00 0000 0000 0000 0000 0000"
              />
            </label>
          </div>
        </div>

        {/* Contactos */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-semibold text-slate-700">Contactos</h4>
            <button
              type="button"
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
              onClick={addContacto}
            >
              + Añadir Contacto
            </button>
          </div>
          {form.contactos.length === 0 && (
            <p className="text-sm text-slate-500">No hay contactos agregados.</p>
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
                    <span className="font-medium text-slate-600">Tipo</span>
                    <select
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.tipo}
                      onChange={(e) => updateContacto(index, 'tipo', e.target.value)}
                    >
                      <option value="facturacion">Facturación</option>
                      <option value="entrega">Entrega</option>
                      <option value="administracion">Administración</option>
                      <option value="comercial">Comercial</option>
                      <option value="soporte">Soporte</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Nombre</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.name || ''}
                      onChange={(e) => updateContacto(index, 'nombre', e.target.value || null)}
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
                    <span className="font-medium text-slate-600">Teléfono</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={contacto.phone || ''}
                      onChange={(e) => updateContacto(index, 'telefono', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm sm:col-span-2">
                    <span className="font-medium text-slate-600">Notas</span>
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
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-semibold text-slate-700">Direcciones</h4>
            <button
              type="button"
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
              onClick={addDireccion}
            >
              + Añadir Dirección
            </button>
          </div>
          {form.direcciones.length === 0 && (
            <p className="text-sm text-slate-500">No hay direcciones agregadas.</p>
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
                    <span className="font-medium text-slate-600">Tipo</span>
                    <select
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.tipo}
                      onChange={(e) => updateDireccion(index, 'tipo', e.target.value)}
                    >
                      <option value="facturacion">Facturación</option>
                      <option value="entrega">Entrega</option>
                      <option value="administracion">Administración</option>
                      <option value="otros">Otros</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">
                      Dirección Línea 1 <span className="text-rose-500">*</span>
                    </span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.linea1}
                      onChange={(e) => updateDireccion(index, 'linea1', e.target.value)}
                      required
                    />
                  </label>
                  <label className="space-y-1 text-sm sm:col-span-2">
                    <span className="font-medium text-slate-600">Dirección Línea 2</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.linea2 || ''}
                      onChange={(e) => updateDireccion(index, 'linea2', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Ciudad</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.city || ''}
                      onChange={(e) => updateDireccion(index, 'ciudad', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Provincia / Región</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.region || ''}
                      onChange={(e) => updateDireccion(index, 'region', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Código Postal</span>
                    <input
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.codigo_postal || ''}
                      onChange={(e) => updateDireccion(index, 'codigo_postal', e.target.value || null)}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">País</span>
                    <select
                      className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                      value={direccion.pais || 'ES'}
                      onChange={(e) => updateDireccion(index, 'pais', e.target.value || null)}
                    >
                      <option value="ES">España</option>
                      <option value="EC">Ecuador</option>
                      <option value="FR">Francia</option>
                      <option value="DE">Alemania</option>
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
            {editMode ? 'Guardar cambios' : 'Crear proveedor'}
          </button>
          <button type="button" className="gc-button gc-button--ghost" onClick={() => nav('..')}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
