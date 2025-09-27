import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createProveedor,
  getProveedor,
  updateProveedor,
  type Proveedor,
  type ProveedorContacto,
  type ProveedorDireccion,
  type ProveedorPayload,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

const contactoTipos: ProveedorContacto['tipo'][] = ['facturacion', 'entrega', 'administracion', 'comercial', 'soporte']
const direccionTipos: ProveedorDireccion['tipo'][] = ['facturacion', 'entrega', 'administracion', 'otros']

const emptyContact: ProveedorContacto = { tipo: 'facturacion', nombre: '', email: '', telefono: '' }
const emptyAddress: ProveedorDireccion = { tipo: 'facturacion', linea1: '', linea2: '', ciudad: '', region: '', codigo_postal: '', pais: '' }

function toPayload(form: FormState): ProveedorPayload {
  const parseNumber = (value: string | null | undefined) => {
    if (value === undefined || value === null || value === '') return undefined
    const num = Number(value)
    return Number.isFinite(num) ? num : undefined
  }

  return {
    nombre: form.nombre,
    nombre_comercial: form.nombre_comercial || undefined,
    nif: form.nif || undefined,
    pais: form.pais || undefined,
    idioma: form.idioma || undefined,
    email: form.email || undefined,
    telefono: form.telefono || undefined,
    tipo_impuesto: form.tipo_impuesto || undefined,
    retencion_irpf: parseNumber(form.retencion_irpf),
    exento_impuestos: form.exento_impuestos,
    regimen_especial: form.regimen_especial || undefined,
    condiciones_pago: form.condiciones_pago || undefined,
    plazo_pago_dias: parseNumber(form.plazo_pago_dias),
    descuento_pronto_pago: parseNumber(form.descuento_pronto_pago),
    divisa: form.divisa || undefined,
    metodo_pago: form.metodo_pago || undefined,
    iban: form.iban || undefined,
    iban_confirmacion: form.iban_confirmacion || undefined,
    contactos: form.contactos.map(({ id, ...rest }) => ({ ...rest, id })),
    direcciones: form.direcciones.map(({ id, ...rest }) => ({ ...rest, id })),
  }
}

type FormState = {
  nombre: string
  nombre_comercial?: string | null
  nif?: string | null
  pais?: string | null
  idioma?: string | null
  email?: string | null
  telefono?: string | null
  tipo_impuesto?: string | null
  retencion_irpf?: string | null
  exento_impuestos: boolean
  regimen_especial?: string | null
  condiciones_pago?: string | null
  plazo_pago_dias?: string | null
  descuento_pronto_pago?: string | null
  divisa?: string | null
  metodo_pago?: string | null
  iban?: string | null
  iban_confirmacion?: string | null
  contactos: ProveedorContacto[]
  direcciones: ProveedorDireccion[]
}

const emptyForm: FormState = {
  nombre: '',
  nombre_comercial: '',
  nif: '',
  pais: '',
  idioma: '',
  email: '',
  telefono: '',
  tipo_impuesto: '',
  retencion_irpf: '',
  exento_impuestos: false,
  regimen_especial: '',
  condiciones_pago: '',
  plazo_pago_dias: '',
  descuento_pronto_pago: '',
  divisa: '',
  metodo_pago: '',
  iban: '',
  iban_confirmacion: '',
  contactos: [],
  direcciones: [],
}

export default function ProveedorForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormState>(emptyForm)
  const [loading, setLoading] = useState(false)
  const { success, error } = useToast()

  useEffect(() => {
    if (!id) {
      setForm((prev) => ({ ...prev, contactos: [], direcciones: [] }))
      return
    }
    setLoading(true)
    getProveedor(id)
      .then((proveedor) => {
        setForm({
          nombre: proveedor.nombre,
          nombre_comercial: proveedor.nombre_comercial || '',
          nif: proveedor.nif || '',
          pais: proveedor.pais || '',
          idioma: proveedor.idioma || '',
          email: proveedor.email || '',
          telefono: proveedor.telefono || '',
          tipo_impuesto: proveedor.tipo_impuesto || '',
          retencion_irpf: proveedor.retencion_irpf != null ? String(proveedor.retencion_irpf) : '',
          exento_impuestos: Boolean(proveedor.exento_impuestos),
          regimen_especial: proveedor.regimen_especial || '',
          condiciones_pago: proveedor.condiciones_pago || '',
          plazo_pago_dias: proveedor.plazo_pago_dias != null ? String(proveedor.plazo_pago_dias) : '',
          descuento_pronto_pago: proveedor.descuento_pronto_pago != null ? String(proveedor.descuento_pronto_pago) : '',
          divisa: proveedor.divisa || '',
          metodo_pago: proveedor.metodo_pago || '',
          iban: proveedor.iban || '',
          iban_confirmacion: proveedor.iban || '',
          contactos: proveedor.contactos.length ? proveedor.contactos : [],
          direcciones: proveedor.direcciones.length ? proveedor.direcciones : [],
        })
      })
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id, error])

  const heading = id ? 'Editar proveedor' : 'Nuevo proveedor'

  const onSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    try {
      if (!form.nombre.trim()) {
        throw new Error('Nombre legal es obligatorio')
      }
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
        throw new Error('Email inválido')
      }
      if (form.iban && form.iban !== form.iban_confirmacion) {
        throw new Error('El IBAN y su confirmación deben coincidir')
      }

      const payload = toPayload(form)
      if (id) await updateProveedor(id, payload)
      else await createProveedor(payload)

      success('Proveedor guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const addContacto = () => setForm((prev) => ({ ...prev, contactos: [...prev.contactos, { ...emptyContact, id: undefined }] }))
  const removeContacto = (index: number) => setForm((prev) => ({ ...prev, contactos: prev.contactos.filter((_, i) => i !== index) }))
  const updateContacto = (index: number, patch: Partial<ProveedorContacto>) =>
    setForm((prev) => {
      const copy = [...prev.contactos]
      copy[index] = { ...copy[index], ...patch }
      return { ...prev, contactos: copy }
    })

  const addDireccion = () => setForm((prev) => ({ ...prev, direcciones: [...prev.direcciones, { ...emptyAddress, id: undefined }] }))
  const removeDireccion = (index: number) => setForm((prev) => ({ ...prev, direcciones: prev.direcciones.filter((_, i) => i !== index) }))
  const updateDireccion = (index: number, patch: Partial<ProveedorDireccion>) =>
    setForm((prev) => {
      const copy = [...prev.direcciones]
      copy[index] = { ...copy[index], ...patch }
      return { ...prev, direcciones: copy }
    })

  const hasContactos = useMemo(() => form.contactos.length > 0, [form.contactos])
  const hasDirecciones = useMemo(() => form.direcciones.length > 0, [form.direcciones])

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold text-slate-800 mb-4">{heading}</h3>
      <form onSubmit={onSubmit} className="space-y-8 max-w-4xl">
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h4 className="text-lg font-semibold text-slate-800 mb-3">Identificación</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Nombre legal *</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.nombre}
                onChange={(e) => setForm((prev) => ({ ...prev, nombre: e.target.value }))}
                required
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Nombre comercial</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.nombre_comercial ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, nombre_comercial: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">NIF / CIF</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.nif ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, nif: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">País</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                placeholder="ES, PT, FR…"
                value={form.pais ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, pais: e.target.value.toUpperCase() }))}
                maxLength={3}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Idioma</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                placeholder="es-ES"
                value={form.idioma ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, idioma: e.target.value }))}
                maxLength={8}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Email principal</span>
              <input
                type="email"
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.email ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Teléfono principal</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.telefono ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, telefono: e.target.value }))}
              />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h4 className="text-lg font-semibold text-slate-800 mb-3">Fiscalidad</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Tipo de IVA / IGIC</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.tipo_impuesto ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, tipo_impuesto: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Retención IRPF (%)</span>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.retencion_irpf ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, retencion_irpf: e.target.value }))}
              />
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
              <input
                type="checkbox"
                checked={form.exento_impuestos}
                onChange={(e) => setForm((prev) => ({ ...prev, exento_impuestos: e.target.checked }))}
              />
              Exento de impuestos
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Régimen especial</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.regimen_especial ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, regimen_especial: e.target.value }))}
              />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h4 className="text-lg font-semibold text-slate-800 mb-3">Pagos</h4>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Condiciones (ej. Net 30)</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.condiciones_pago ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, condiciones_pago: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Plazo pago (días)</span>
              <input
                type="number"
                min="0"
                max="365"
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.plazo_pago_dias ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, plazo_pago_dias: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Descuento pronto pago (%)</span>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.descuento_pronto_pago ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, descuento_pronto_pago: e.target.value }))}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Divisa</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                placeholder="EUR"
                value={form.divisa ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, divisa: e.target.value.toUpperCase() }))}
                maxLength={3}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Método de pago</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2"
                placeholder="transferencia, sepa, efectivo…"
                value={form.metodo_pago ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, metodo_pago: e.target.value }))}
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 mt-4">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">IBAN</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono"
                value={form.iban ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, iban: e.target.value.toUpperCase() }))}
                maxLength={34}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-600">Confirmar IBAN</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono"
                value={form.iban_confirmacion ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, iban_confirmacion: e.target.value.toUpperCase() }))}
                maxLength={34}
              />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <h4 className="text-lg font-semibold text-slate-800">Contactos</h4>
            <button type="button" className="gc-button gc-button--ghost" onClick={addContacto}>
              Añadir contacto
            </button>
          </div>
          {!hasContactos && <p className="text-sm text-slate-500">Puedes definir contactos por área (facturación, entrega, soporte…).</p>}
          <div className="space-y-4">
            {form.contactos.map((c, idx) => (
              <div key={idx} className="rounded-xl border border-slate-200 p-4">
                <div className="flex justify-between items-center mb-3">
                  <strong className="text-slate-700">Contacto #{idx + 1}</strong>
                  <button type="button" className="text-sm text-red-600" onClick={() => removeContacto(idx)}>
                    Quitar
                  </button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Tipo</span>
                    <select
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={c.tipo}
                      onChange={(e) => updateContacto(idx, { tipo: e.target.value as ProveedorContacto['tipo'] })}
                    >
                      {contactoTipos.map((tipo) => (
                        <option key={tipo} value={tipo}>{tipo}</option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Nombre</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={c.nombre ?? ''}
                      onChange={(e) => updateContacto(idx, { nombre: e.target.value })}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Email</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={c.email ?? ''}
                      onChange={(e) => updateContacto(idx, { email: e.target.value })}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Teléfono</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={c.telefono ?? ''}
                      onChange={(e) => updateContacto(idx, { telefono: e.target.value })}
                    />
                  </label>
                  <label className="sm:col-span-2 space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Notas</span>
                    <textarea
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      rows={2}
                      value={c.notas ?? ''}
                      onChange={(e) => updateContacto(idx, { notas: e.target.value })}
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <h4 className="text-lg font-semibold text-slate-800">Direcciones</h4>
            <button type="button" className="gc-button gc-button--ghost" onClick={addDireccion}>
              Añadir dirección
            </button>
          </div>
          {!hasDirecciones && <p className="text-sm text-slate-500">Registra direcciones de facturación, entrega u otras ubicaciones clave.</p>}
          <div className="space-y-4">
            {form.direcciones.map((d, idx) => (
              <div key={idx} className="rounded-xl border border-slate-200 p-4">
                <div className="flex justify-between items-center mb-3">
                  <strong className="text-slate-700">Dirección #{idx + 1}</strong>
                  <button type="button" className="text-sm text-red-600" onClick={() => removeDireccion(idx)}>
                    Quitar
                  </button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Tipo</span>
                    <select
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.tipo}
                      onChange={(e) => updateDireccion(idx, { tipo: e.target.value as ProveedorDireccion['tipo'] })}
                    >
                      {direccionTipos.map((tipo) => (
                        <option key={tipo} value={tipo}>{tipo}</option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Línea 1</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.linea1}
                      onChange={(e) => updateDireccion(idx, { linea1: e.target.value })}
                      required
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Línea 2</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.linea2 ?? ''}
                      onChange={(e) => updateDireccion(idx, { linea2: e.target.value })}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Ciudad</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.ciudad ?? ''}
                      onChange={(e) => updateDireccion(idx, { ciudad: e.target.value })}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Región / Provincia</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.region ?? ''}
                      onChange={(e) => updateDireccion(idx, { region: e.target.value })}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Código postal</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.codigo_postal ?? ''}
                      onChange={(e) => updateDireccion(idx, { codigo_postal: e.target.value })}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">País</span>
                    <input
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      value={d.pais ?? ''}
                      onChange={(e) => updateDireccion(idx, { pais: e.target.value.toUpperCase() })}
                      maxLength={3}
                    />
                  </label>
                  <label className="sm:col-span-2 space-y-1 text-sm">
                    <span className="font-medium text-slate-600">Notas</span>
                    <textarea
                      className="w-full rounded-lg border border-slate-200 px-3 py-2"
                      rows={2}
                      value={d.notas ?? ''}
                      onChange={(e) => updateDireccion(idx, { notas: e.target.value })}
                    />
                  </label>
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="gc-button gc-button--primary"
            disabled={loading}
          >
            Guardar
          </button>
          <button
            type="button"
            className="gc-button gc-button--ghost"
            onClick={() => nav('..')}
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
