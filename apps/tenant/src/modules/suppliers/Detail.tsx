import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getProveedor, removeProveedor, type Proveedor } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function ProveedorDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation(['suppliers', 'common'])
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [loading, setLoading] = useState(false)
  const [confirmDeactivate, setConfirmDeactivate] = useState(false)
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
    setConfirmDeactivate(false)
    try {
      await removeProveedor(id!)
      success(t('suppliers:messages.deactivated'))
      nav('..')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-sm text-slate-500">{t('suppliers:detail.loading')}</div>
      </div>
    )
  }

  if (!proveedor) {
    return (
      <div className="p-6">
        <div className="text-sm text-slate-500">{t('suppliers:detail.notFound')}</div>
        <button className="gc-button gc-button--ghost mt-4" onClick={() => nav('..')}>
          {t('common:back')}
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
              {proveedor.active !== false ? t('suppliers:status.active') : t('suppliers:status.inactive')}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {t('suppliers:detail.code')}: PRV-{String(proveedor.id).padStart(5, '0')}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="editar" className="gc-button gc-button--primary">
            {t('common:edit')}
          </Link>
          <button className="gc-button gc-button--ghost" onClick={() => setConfirmDeactivate(true)}>
            {t('suppliers:actions.deactivate')}
          </button>
          <button className="gc-button gc-button--ghost" onClick={() => nav('..')}>
            {t('common:back')}
          </button>
        </div>
      </div>

      {/* General Information */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">{t('suppliers:detail.generalInfo')}</h3>
        <div className="grid gap-4 sm:grid-cols-2 text-sm">
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.tradeName')}:</span>
            <p className="text-slate-900">{proveedor.nombre_comercial || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.nif')}:</span>
            <p className="text-slate-900">{proveedor.nif || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.country')}:</span>
            <p className="text-slate-900">{proveedor.pais || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.language')}:</span>
            <p className="text-slate-900">{proveedor.idioma?.toUpperCase() || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.email')}:</span>
            <p className="text-slate-900">{proveedor.email || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.phone')}:</span>
            <p className="text-slate-900">{proveedor.phone || '—'}</p>
          </div>
        </div>
      </div>

      {/* Tax and Payment Settings */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">{t('suppliers:detail.taxPayment')}</h3>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.taxType')}:</span>
            <p className="text-slate-900">{proveedor.tipo_impuesto || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.irpf')}:</span>
            <p className="text-slate-900">
              {proveedor.retencion_irpf != null ? `${proveedor.retencion_irpf}%` : '—'}
            </p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.taxExempt')}:</span>
            <p className="text-slate-900">{proveedor.exento_impuestos ? t('common:yes') : t('common:no')}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.paymentTerm')}:</span>
            <p className="text-slate-900">
              {proveedor.plazo_pago_dias != null ? t('suppliers:detail.days', { count: proveedor.plazo_pago_dias }) : '—'}
            </p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.currency')}:</span>
            <p className="text-slate-900">{proveedor.divisa || '—'}</p>
          </div>
          <div>
            <span className="font-medium text-slate-600">{t('suppliers:form.paymentMethod')}:</span>
            <p className="text-slate-900 capitalize">{proveedor.metodo_pago || '—'}</p>
          </div>
          {proveedor.iban && (
            <div className="sm:col-span-3">
              <span className="font-medium text-slate-600">{t('suppliers:form.iban')}:</span>
              <p className="text-slate-900 font-mono text-xs">{proveedor.iban}</p>
            </div>
          )}
        </div>
      </div>

      {/* Contacts */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">
          {t('suppliers:detail.contacts')} ({proveedor.contactos?.length || 0})
        </h3>
        {!proveedor.contactos || proveedor.contactos.length === 0 ? (
          <p className="text-sm text-slate-500">{t('suppliers:detail.noContacts')}</p>
        ) : (
          <div className="space-y-3">
            {proveedor.contactos.map((contacto, index) => (
              <div
                key={index}
                className="border border-slate-200 rounded-xl p-4 bg-slate-50 text-sm"
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700 capitalize">
                      {t(`suppliers:contactTypes.${contacto.tipo}`, contacto.tipo)}
                    </span>
                    {(contacto.name || contacto.nombre) && (
                      <span className="font-medium text-slate-900">{contacto.name || contacto.nombre}</span>
                    )}
                  </div>
                  {contacto.email && (
                    <div className="text-slate-600">
                      <span className="font-medium">{t('suppliers:form.email')}:</span> {contacto.email}
                    </div>
                  )}
                  {(contacto.phone || contacto.telefono) && (
                    <div className="text-slate-600">
                      <span className="font-medium">{t('suppliers:form.phone')}:</span> {contacto.phone || contacto.telefono}
                    </div>
                  )}
                  {contacto.notas && (
                    <div className="text-slate-500 text-xs">{contacto.notas}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Addresses */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="text-base font-semibold text-slate-700 mb-4">
          {t('suppliers:detail.addresses')} ({proveedor.direcciones?.length || 0})
        </h3>
        {!proveedor.direcciones || proveedor.direcciones.length === 0 ? (
          <p className="text-sm text-slate-500">{t('suppliers:detail.noAddresses')}</p>
        ) : (
          <div className="space-y-3">
            {proveedor.direcciones.map((direccion, index) => (
              <div
                key={index}
                className="border border-slate-200 rounded-xl p-4 bg-slate-50 text-sm"
              >
                <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700 capitalize mb-2">
                  {t(`suppliers:addressTypes.${direccion.tipo}`, direccion.tipo)}
                </span>
                <div className="space-y-1 text-slate-700 mt-2">
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

      {confirmDeactivate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setConfirmDeactivate(false)}>
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="font-bold text-gray-900 mb-2">{t('suppliers:confirmDelete')}</h3>
            <p className="text-sm text-gray-500 mb-5">{t('suppliers:confirmDeleteBody', 'Esta acción desactivará al proveedor.')}</p>
            <div className="flex gap-2 justify-end">
              <button className="px-4 py-2 border rounded-xl text-sm" onClick={() => setConfirmDeactivate(false)}>{t('common:cancel')}</button>
              <button className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-sm font-semibold" onClick={() => void handleRemove()}>{t('suppliers:actions.deactivate')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
