import React, { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { createVacacion, listEmpleados } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { VacacionCreate, Empleado } from '../../types/hr'
import { useSectorPlaceholder } from '../../hooks/useSectorPlaceholders'
import { useCompany } from '../../contexts/CompanyContext'

const INITIAL_FORM: VacacionCreate = {
  empleado_id: '',
  fecha_inicio: '',
  fecha_fin: '',
  tipo: 'vacaciones',
  motivo: '',
  notas: ''
}

export default function VacacionForm() {
  const nav = useNavigate()
  const location = useLocation()
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
      if (!form.empleado_id) throw new Error('Select an employee')
      if (!form.fecha_inicio) throw new Error('Start date is required')
      if (!form.fecha_fin) throw new Error('End date is required')
      if (dias <= 0) throw new Error('Invalid dates')

      setLoading(true)

      const payload = {
        ...form,
        dias
      }

      await createVacacion(payload)

      success('Vacation registered')
      nav('/hr/vacations')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">New Vacation/Leave Request</h3>

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 700 }}>
        <div>
          <label className="block mb-1 font-medium">Employee *</label>
          <select
            value={form.empleado_id}
            onChange={(e) => setForm({ ...form, empleado_id: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
            disabled={loading}
          >
            <option value="">Select...</option>
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
          <label className="block mb-1 font-medium">Type *</label>
          <select
            value={form.tipo}
            onChange={(e) => setForm({ ...form, tipo: e.target.value as any })}
            className="border px-2 py-1 w-full rounded"
            required
            disabled={loading}
          >
            <option value="vacaciones">Vacation</option>
            <option value="baja_medica">Medical Leave</option>
            <option value="permiso">Leave</option>
            <option value="otros">Other</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Start Date *</label>
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
            <label className="block mb-1 font-medium">End Date *</label>
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
              <strong>Calculated days:</strong> {dias} day{dias !== 1 ? 's' : ''}
            </p>
          </div>
        )}

        <div>
          <label className="block mb-1 font-medium">Reason</label>
          <input
            type="text"
            value={form.motivo}
            onChange={(e) => setForm({ ...form, motivo: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            placeholder={motivoPlaceholder || 'E.g.: Annual vacation, personal matter, etc.'}
            disabled={loading}
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">Notes</label>
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
            {loading ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            className="bg-gray-300 px-4 py-2 rounded hover:bg-gray-400"
            onClick={() => nav('/hr/vacations')}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
