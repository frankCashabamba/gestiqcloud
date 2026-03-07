import React, { useEffect, useState } from 'react'

import { useNavigate, useParams } from 'react-router-dom'

import { createTipoIdentificacion, getTipoIdentificacion, updateTipoIdentificacion, type TipoIdentificacion } from '../../../services/configuracion/tipos-identificacion'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<TipoIdentificacion, 'id'>

const COUNTRY_SUGGESTIONS = ['EC', 'ES', 'CO', 'PE', 'MX', 'AR', 'CL', 'BO', 'PY', 'UY']

export default function TipoIdentificacionForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ country_code: 'EC', code: '', label: '', active: true })
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getTipoIdentificacion(id)
        .then((m) => setForm({ country_code: m.country_code, code: m.code, label: m.label, active: m.active }))
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.country_code?.trim()) throw new Error('El país es obligatorio')
      if (!form.code?.trim()) throw new Error('El código es obligatorio')
      if (!form.label?.trim()) throw new Error('La etiqueta es obligatoria')
      if (id) await updateTipoIdentificacion(id, form)
      else await createTipoIdentificacion(form)
      success('Tipo de identificación guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">
        {id ? 'Editar tipo de identificación' : 'Nuevo tipo de identificación'}
      </h3>
      {loading && <div className="text-sm text-gray-500 mb-2">Cargando...</div>}
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">País <span className="text-red-500">*</span></label>
          <input
            list="country-suggestions"
            value={form.country_code}
            onChange={(e) => setForm({ ...form, country_code: e.target.value.toUpperCase() })}
            className="border px-2 py-1 w-full rounded"
            placeholder="EC"
            maxLength={2}
            required
          />
          <datalist id="country-suggestions">
            {COUNTRY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
          </datalist>
          <p className="text-xs text-gray-400 mt-1">Código ISO 3166-1 alpha-2 (EC, ES, CO…)</p>
        </div>
        <div>
          <label className="block mb-1">Código <span className="text-red-500">*</span></label>
          <input
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
            className="border px-2 py-1 w-full rounded font-mono"
            placeholder="CEDULA"
            required
          />
          <p className="text-xs text-gray-400 mt-1">Ej: CEDULA, RUC, PASSPORT, DNI, NIE</p>
        </div>
        <div>
          <label className="block mb-1">Etiqueta <span className="text-red-500">*</span></label>
          <input
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            placeholder="Cédula de identidad"
            required
          />
        </div>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
          Activo
        </label>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
