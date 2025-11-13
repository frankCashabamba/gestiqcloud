import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getProveedor, removeProveedor, type Proveedor } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function ProveedorDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [loading, setLoading] = useState(false)
  const { success, error: toastError } = useToast()

  useEffect(() => {
    if (!id) return
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const data = await getProveedor(id)
        if (cancelled) return
        setProveedor(data)
      } catch (e: any) {
        if (cancelled) return
        toastError(getErrorMessage(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  const handleRemove = async () => {
    if (!confirm('¿Desactivar este proveedor?')) return
    try {
      await removeProveedor(id!)
      success('Proveedor desactivado')
      nav('..')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-sm text-slate-500">Cargando proveedor…</div>
      </div>
    )
  }

  if (!proveedor) {
    return (
      <div className="p-6">
        <div className="text-sm text-slate-500">Proveedor no encontrado</div>
        <button className="gc-button gc-button--ghost mt-4" onClick={() => nav('..')}>
          Volver
        </button>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-slate-900">{proveedor.name}</h2>
            <span
              className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                proveedor.active !== false
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-slate-100 text-slate-500'
              }`}
            >
              {proveedor.active !== false ? 'Activo' : 'Inactivo'}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Código: PRV-{String(proveedor.id).padStart(5, '0')}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="editar" className="gc-button gc-button--primary">
            Editar
          </Link>
          <button className="gc-button gc-button--ghost" onClick={handleRemove}>
            Desactivar
          </button>
          <button className="gc-button gc-button--ghost" onClick={() => nav('..')}>
            Volver
          </button>
        </div>
      </div>

      {/* Datos Generales */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">Datos Generales</h3>
        <div className="grid gap-4 sm:grid-cols-2 text-sm">
          <div>
            <span className="font-medium text-slate-600">Nombre Comercial:</span>
            <p className="text-slate-900">{proveedor.nombre_comercial || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">NIF / Tax ID:</span>
            <p className="text-slate-900">{proveedor.nif || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">País:</span>
            <p className="text-slate-900">{proveedor.pais || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Idioma:</span>
            <p className="text-slate-900">{proveedor.idioma?.toUpperCase() || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Email:</span>
            <p className="text-slate-900">{proveedor.email || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Teléfono:</span>
            <p className="text-slate-900">{proveedor.phone || '—'}</p>
          </div>
        </div>
      </div>

      {/* Configuración Fiscal */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">Configuración Fiscal y Pagos</h3>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div>
            <span className="font-medium text-slate-600">Tipo Impuesto:</span>
            <p className="text-slate-900">{proveedor.tipo_impuesto || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Retención IRPF:</span>
            <p className="text-slate-900">
              {proveedor.retencion_irpf != null ? `${proveedor.retencion_irpf}%` : '—'}
            </p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Exento de Impuestos:</span>
            <p className="text-slate-900">{proveedor.exento_impuestos ? 'Sí' : 'No'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Plazo de Pago:</span>
            <p className="text-slate-900">
              {proveedor.plazo_pago_dias != null ? `${proveedor.plazo_pago_dias} días` : '—'}
            </p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Divisa:</span>
            <p className="text-slate-900">{proveedor.divisa || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">Método de Pago:</span>
            <p className="text-slate-900 capitalize">{proveedor.metodo_pago || '—'}</p>
          </div>
          {proveedor.iban && (
            <div className="sm:col-span-3">
              <span className="font-medium text-slate-600">IBAN:</span>
              <p className="text-slate-900 font-mono text-xs">{proveedor.iban}</p>
            </div>
          )}
        </div>
      </div>

      {/* Contactos */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">
          Contactos ({proveedor.contactos?.length || 0})
        </h3>
        {!proveedor.contactos || proveedor.contactos.length === 0 ? (
          <p className="text-sm text-slate-500">No hay contactos registrados</p>
        ) : (
          <div className="space-y-3">
            {proveedor.contactos.map((contacto, index) => (
              <div
                key={index}
                className="border border-slate-200 rounded-xl p-4 bg-slate-50 text-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700 capitalize">
                        {contacto.tipo}
                      </span>
                      {contacto.name && (
                        <span className="font-medium text-slate-900">{contacto.name}</span>
                      )}
                    </div>
                    {contacto.email && (
                      <div className="text-slate-600">
                        <span className="font-medium">Email:</span> {contacto.email}
                      </div>
                    )}
                    {contacto.phone && (
                      <div className="text-slate-600">
                        <span className="font-medium">Teléfono:</span> {contacto.phone}
                      </div>
                    )}
                    {contacto.notas && (
                      <div className="text-slate-500 text-xs">{contacto.notas}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Direcciones */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">
          Direcciones ({proveedor.direcciones?.length || 0})
        </h3>
        {!proveedor.direcciones || proveedor.direcciones.length === 0 ? (
          <p className="text-sm text-slate-500">No hay direcciones registradas</p>
        ) : (
          <div className="space-y-3">
            {proveedor.direcciones.map((direccion, index) => (
              <div
                key={index}
                className="border border-slate-200 rounded-xl p-4 bg-slate-50 text-sm"
              >
                <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700 capitalize mb-2">
                  {direccion.tipo}
                </span>
                <div className="space-y-1 text-slate-700">
                  <p>{direccion.linea1}</p>
                  {direccion.linea2 && <p>{direccion.linea2}</p>}
                  <p>
                    {[direccion.city, direccion.region, direccion.codigo_postal]
                      .filter(Boolean)
                      .join(', ')}
                  </p>
                  <p className="font-medium">{direccion.pais}</p>
                  {direccion.notas && (
                    <p className="text-slate-500 text-xs italic">{direccion.notas}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Histórico de Compras - Futuro */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">Histórico de Compras</h3>
        <p className="text-sm text-slate-500 text-center py-8">
          Próximamente: historial de facturas y pedidos con este proveedor
        </p>
      </div>
    </div>
  )
}
