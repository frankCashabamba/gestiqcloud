import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createEmpleado, getEmpleado, updateEmpleado } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { EmpleadoCreate } from '../../types/hr'

const INITIAL_FORM: EmpleadoCreate = {
  sku: '',
  name: '',
  apellidos: '',
  tipo_documento: 'ID',
  numero_documento: '',
  email: '',
  phone: '',
  fecha_nacimiento: '',
  fecha_ingreso: new Date().toISOString().slice(0, 10),
  departamento_id: '',
  puesto: '',
  tipo_contrato: 'indefinido',
  jornada: 'completa',
  salario_base: 0,
  banco: '',
  numero_cuenta: '',
  seguridad_social: '',
  estado: 'activo',
  notas: ''
}

export default function EmpleadoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()

  const [form, setForm] = useState<EmpleadoCreate>(INITIAL_FORM)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getEmpleado(id)
        .then((x) => {
          setForm({
            sku: x.sku || '',
            name: x.name,
            apellidos: x.apellidos,
            tipo_documento: x.tipo_documento,
            numero_documento: x.numero_documento,
            email: x.email || '',
            phone: x.phone || '',
            fecha_nacimiento: x.fecha_nacimiento || '',
            fecha_ingreso: x.fecha_ingreso,
            departamento_id: x.departamento_id || '',
            puesto: x.puesto || '',
            tipo_contrato: x.tipo_contrato,
            jornada: x.jornada,
            salario_base: x.salario_base,
            banco: x.banco || '',
            numero_cuenta: x.numero_cuenta || '',
            seguridad_social: x.seguridad_social || '',
            estado: x.estado,
            notas: x.notas || ''
          })
        })
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()

    try {
      if (!form.name.trim()) throw new Error('Name is required')
      if (!form.apellidos.trim()) throw new Error('Last names is required')
      if (!form.numero_documento.trim()) throw new Error('Document number is required')
      if (!form.fecha_ingreso) throw new Error('Start date is required')
      if (form.salario_base <= 0) throw new Error('Base salary must be greater than 0')

      setLoading(true)

      if (id) {
        await updateEmpleado(id, form)
      } else {
        await createEmpleado(form)
      }

      success('Employee saved')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">
        {id ? 'Edit Employee' : 'New Employee'}
      </h3>

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 900 }}>
        {/* Personal Data */}
        <fieldset className="border rounded p-4">
          <legend className="font-semibold text-gray-700 px-2">Personal Data</legend>

          <div className="grid grid-cols-2 gap-4 mt-2">
            <div>
              <label className="block mb-1 font-medium text-sm">Code</label>
              <input
                type="text"
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                placeholder="EMP001"
                disabled={loading}
              />
            </div>
            <div />
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block mb-1 font-medium text-sm">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Last Name *</label>
              <input
                type="text"
                value={form.apellidos}
                onChange={(e) => setForm({ ...form, apellidos: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className="block mb-1 font-medium text-sm">Doc. Type *</label>
              <select
                value={form.tipo_documento}
                onChange={(e) => setForm({ ...form, tipo_documento: e.target.value as any })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              >
                <option value="ID">ID</option>
                <option value="Foreigner ID">Foreigner ID</option>
                <option value="PASAPORTE">Passport</option>
                <option value="CEDULA">Cedula</option>
              </select>
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Doc. Number *</label>
              <input
                type="text"
                value={form.numero_documento}
                onChange={(e) => setForm({ ...form, numero_documento: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Birth Date</label>
              <input
                type="date"
                value={form.fecha_nacimiento}
                onChange={(e) => setForm({ ...form, fecha_nacimiento: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block mb-1 font-medium text-sm">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Phone</label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              />
            </div>
          </div>
        </fieldset>

        {/* Employment Data */}
        <fieldset className="border rounded p-4">
          <legend className="font-semibold text-gray-700 px-2">Employment Data</legend>

          <div className="grid grid-cols-3 gap-4 mt-2">
            <div>
              <label className="block mb-1 font-medium text-sm">Start Date *</label>
              <input
                type="date"
                value={form.fecha_ingreso}
                onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Department</label>
              <input
                type="text"
                value={form.departamento_id}
                onChange={(e) => setForm({ ...form, departamento_id: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                placeholder="Sales, HR, etc."
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Position</label>
              <input
                type="text"
                value={form.puesto}
                onChange={(e) => setForm({ ...form, puesto: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                placeholder="Cashier, Manager, etc."
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className="block mb-1 font-medium text-sm">Contract Type *</label>
              <select
                value={form.tipo_contrato}
                onChange={(e) => setForm({ ...form, tipo_contrato: e.target.value as any })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              >
                <option value="indefinido">Permanent</option>
                <option value="temporal">Temporary</option>
                <option value="practicas">Internship</option>
                <option value="formacion">Training</option>
                <option value="autonomo">Freelance</option>
              </select>
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Work Schedule *</label>
              <select
                value={form.jornada}
                onChange={(e) => setForm({ ...form, jornada: e.target.value as any })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              >
                <option value="completa">Full-time</option>
                <option value="parcial">Part-time</option>
                <option value="por_horas">Hourly</option>
              </select>
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Base Salary *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.salario_base}
                onChange={(e) => setForm({ ...form, salario_base: Number(e.target.value) })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block mb-1 font-medium text-sm">Bank</label>
              <input
                type="text"
                value={form.banco}
                onChange={(e) => setForm({ ...form, banco: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Account Number (IBAN)</label>
              <input
                type="text"
                value={form.numero_cuenta}
                onChange={(e) => setForm({ ...form, numero_cuenta: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                placeholder="ES00 0000 0000 0000 0000 0000"
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className="block mb-1 font-medium text-sm">Social Security</label>
              <input
                type="text"
                value={form.seguridad_social}
                onChange={(e) => setForm({ ...form, seguridad_social: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block mb-1 font-medium text-sm">Status *</label>
              <select
                value={form.estado}
                onChange={(e) => setForm({ ...form, estado: e.target.value as any })}
                className="border px-2 py-1 w-full rounded"
                required
                disabled={loading}
              >
                <option value="activo">Active</option>
                <option value="baja">Terminated</option>
                <option value="suspendido">Suspended</option>
              </select>
            </div>
          </div>
        </fieldset>

        {/* Notes */}
        <div>
          <label className="block mb-1 font-medium text-sm">Notes</label>
          <textarea
            value={form.notas}
            onChange={(e) => setForm({ ...form, notas: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={3}
            disabled={loading}
          />
        </div>

        {/* Botones */}
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
            onClick={() => nav('..')}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
