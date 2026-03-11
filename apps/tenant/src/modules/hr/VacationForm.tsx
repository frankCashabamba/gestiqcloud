import React, { useEffect, useState } from 'react'
import { useNavigate, useLocation, useParams } from 'react-router-dom'
import { createVacacion, listEmpleados } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { VacacionCreate, Empleado } from '../../types/hr'
import { useSectorPlaceholder } from '../../hooks/useSectorPlaceholders'
import { useCompany } from '../../contexts/CompanyContext'
import { useTranslation } from 'react-i18next'

const INITIAL_FORM: VacacionCreate = {
  empleado_id: '',
  fecha_inicio: '',
  fecha_fin: '',
  tipo: 'vacaciones',
  motivo: '',
  notas: ''
}

export default function VacacionForm() {
  const { t } = useTranslation(['hr', 'common'])
  const nav = useNavigate()
  const location = useLocation()
  const { empresa } = useParams()
  const { success, error } = useToast()
  const { sector } = useCompany()

  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [form, setForm] = useState<VacacionCreate>(INITIAL_FORM)
  const [loading, setLoading] = useState(false)
  const [dias, setDias] = useState(0)

  const { placeholder: motivoPlaceholder } = useSectorPlaceholder(
    sector?.plantilla || null,
    'motivo',
    'vacation'
  )

  useEffect(() => {
    listEmpleados()
      .then((data) => setEmpleados(data?.items || data || []))
      .catch((e) => error(getErrorMessage(e)))
  }, [])

  // If coming from EmpleadoDetail, preselect employee
  useEffect(() => {
    const state = location.state as any
    if (state?.empleadoId) {
      setForm((f) => ({ ...f, empleado_id: state.empleadoId }))
    }
  }, [location.state])

  // Calculate days automatically
  useEffect(() => {
    if (form.fecha_inicio && form.fecha_fin) {
      const inicio = new Date(form.fecha_inicio)
      const fin = new Date(form.fecha_fin)
      const diff = Math.ceil((fin.getTime() - inicio.getTime()) / (1000 * 60 * 60 * 24)) + 1
      setDias(diff > 0 ? diff : 0)
    } else {
      setDias(0)
    }
  }, [form.fecha_inicio, form.fecha_fin])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()

    try {
      if (!form.empleado_id) throw new Error(t('hr:vacations.selectEmployee'))
      if (!form.fecha_inicio) throw new Error(t('hr:vacations.startDateRequired'))
      if (!form.fecha_fin) throw new Error(t('hr:vacations.endDateRequired'))
      if (dias <= 0) throw new Error(t('hr:vacations.invalidDates'))

      setLoading(true)

      const payload = {
        ...form,
        dias
      }

      await createVacacion(payload)

      success(t('hr:vacations.registered'))
      nav(empresa ? `/${empresa}/hr/vacations` : '/hr/vacations')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{t('hr:vacations.newRequest')}</h3>

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 700 }}>
        <div>
          <label className="block mb-1 font-medium">{t('hr:vacations.employee')} *</label>
          <select
            value={form.empleado_id}
            onChange={(e) => setForm({ ...form, empleado_id: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
            disabled={loading}
          >
            <option value="">{t('hr:vacations.select')}</option>
            {empleados
              .filter((e) => e.estado === 'activo')
              .map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} {e.apellidos} - {e.sku || e.numero_documento}
                </option>
              ))}
          </select>
        </div>

        <div>
          <label className="block mb-1 font-medium">{t('hr:vacations.type')} *</label>
          <select
            value={form.tipo}
            onChange={(e) => setForm({ ...form, tipo: e.target.value as any })}
            className="border px-2 py-1 w-full rounded"
            required
            disabled={loading}
          >
            <option value="vacaciones">{t('hr:vacations.vacation')}</option>
            <option value="baja_medica">{t('hr:vacations.medicalLeave')}</option>
            <option value="permiso">{t('hr:vacations.leave')}</option>
            <option value="otros">{t('hr:vacations.other')}</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">{t('hr:vacations.from')} *</label>
            <input
              type="date"
              value={form.fecha_inicio}
              onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            />
          </div>
          <div>
            <label className="block mb-1 font-medium">{t('hr:vacations.to')} *</label>
            <input
              type="date"
              value={form.fecha_fin}
              onChange={(e) => setForm({ ...form, fecha_fin: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              min={form.fecha_inicio}
              required
              disabled={loading}
            />
          </div>
        </div>

        {dias > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm">
            <p className="text-blue-800">
              <strong>{t('hr:vacations.calculatedDays')}</strong> {dias} {dias !== 1 ? t('hr:vacations.daysUnit') : t('hr:vacations.dayUnit')}
            </p>
          </div>
        )}

        <div>
          <label className="block mb-1 font-medium">{t('hr:vacations.reason')}</label>
          <input
            type="text"
            value={form.motivo}
            onChange={(e) => setForm({ ...form, motivo: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            placeholder={motivoPlaceholder || t('hr:vacations.reasonPlaceholder')}
            disabled={loading}
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">{t('hr:form.notes')}</label>
          <textarea
            value={form.notas}
            onChange={(e) => setForm({ ...form, notas: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={3}
            disabled={loading}
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            disabled={loading}
          >
            {loading ? t('hr:form.saving') : t('hr:form.save')}
          </button>
          <button
            type="button"
            className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
            onClick={() => nav(empresa ? `/${empresa}/hr/vacations` : '/hr/vacations')}
            disabled={loading}
          >
            {t('hr:form.cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
