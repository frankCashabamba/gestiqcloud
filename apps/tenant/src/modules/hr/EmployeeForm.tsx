import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation(['hr', 'common'])
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
      if (!form.name.trim()) throw new Error(t('hr:form.nameRequired'))
      if (!form.apellidos.trim()) throw new Error(t('hr:form.lastNameRequired'))
      if (!form.numero_documento.trim()) throw new Error(t('hr:form.docNumberRequired'))
      if (!form.fecha_ingreso) throw new Error(t('hr:form.startDateRequired'))
      if (form.salario_base <= 0) throw new Error(t('hr:form.salaryRequired'))

      setLoading(true)

      if (id) {
        await updateEmpleado(id, form)
      } else {
        await createEmpleado(form)
      }

      success(t('hr:employees.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="gc-container py-6">
      <h3 className="gc-page-header__title mb-4">
        {id ? t('hr:employees.edit') : t('hr:employees.new')}
      </h3>

      <form onSubmit={onSubmit} className="space-y-6 max-w-4xl">
        {/* Personal Data */}
        <fieldset className="gc-card">
          <legend className="gc-section-title px-2">{t('hr:form.personalData')}</legend>

          <div className="grid grid-cols-2 gap-4 mt-2">
            <div>
              <label className="gc-label">{t('hr:employees.code')}</label>
              <input
                type="text"
                value={form.sku}
                onChange={(e) => setForm({ ...form, sku: e.target.value })}
                className="gc-input"
                placeholder="EMP001"
                disabled={loading}
              />
            </div>
            <div />
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="gc-label">{t('hr:employees.name')} *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="gc-input"
                required
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:form.lastName')} *</label>
              <input
                type="text"
                value={form.apellidos}
                onChange={(e) => setForm({ ...form, apellidos: e.target.value })}
                className="gc-input"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className="gc-label">{t('hr:form.docType')} *</label>
              <select
                value={form.tipo_documento}
                onChange={(e) => setForm({ ...form, tipo_documento: e.target.value as any })}
                className="gc-input"
                required
                disabled={loading}
              >
                <option value="ID">ID</option>
                <option value="Foreigner ID">{t('hr:form.foreigner')}</option>
                <option value="PASAPORTE">{t('hr:form.passport')}</option>
                <option value="CEDULA">{t('hr:form.cedula')}</option>
              </select>
            </div>
            <div>
              <label className="gc-label">{t('hr:form.docNumber')} *</label>
              <input
                type="text"
                value={form.numero_documento}
                onChange={(e) => setForm({ ...form, numero_documento: e.target.value })}
                className="gc-input"
                required
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:form.birthDate')}</label>
              <input
                type="date"
                value={form.fecha_nacimiento}
                onChange={(e) => setForm({ ...form, fecha_nacimiento: e.target.value })}
                className="gc-input"
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="gc-label">{t('hr:form.email')}</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="gc-input"
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:form.phone')}</label>
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                className="gc-input"
                disabled={loading}
              />
            </div>
          </div>
        </fieldset>

        {/* Employment Data */}
        <fieldset className="gc-card">
          <legend className="gc-section-title px-2">{t('hr:form.employmentData')}</legend>

          <div className="grid grid-cols-3 gap-4 mt-2">
            <div>
              <label className="gc-label">{t('hr:employees.startDate')} *</label>
              <input
                type="date"
                value={form.fecha_ingreso}
                onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })}
                className="gc-input"
                required
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:form.department')}</label>
              <input
                type="text"
                value={form.departamento_id}
                onChange={(e) => setForm({ ...form, departamento_id: e.target.value })}
                className="gc-input"
                placeholder={t('hr:form.departmentPlaceholder')}
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:form.position')}</label>
              <input
                type="text"
                value={form.puesto}
                onChange={(e) => setForm({ ...form, puesto: e.target.value })}
                className="gc-input"
                placeholder={t('hr:form.positionPlaceholder')}
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className="gc-label">{t('hr:form.contractType')} *</label>
              <select
                value={form.tipo_contrato}
                onChange={(e) => setForm({ ...form, tipo_contrato: e.target.value as any })}
                className="gc-input"
                required
                disabled={loading}
              >
                <option value="indefinido">{t('hr:form.permanent')}</option>
                <option value="temporal">{t('hr:form.temporary')}</option>
                <option value="practicas">{t('hr:form.internship')}</option>
                <option value="formacion">{t('hr:form.training')}</option>
                <option value="autonomo">{t('hr:form.freelance')}</option>
              </select>
            </div>
            <div>
              <label className="gc-label">{t('hr:form.workSchedule')} *</label>
              <select
                value={form.jornada}
                onChange={(e) => setForm({ ...form, jornada: e.target.value as any })}
                className="gc-input"
                required
                disabled={loading}
              >
                <option value="completa">{t('hr:form.fullTime')}</option>
                <option value="parcial">{t('hr:form.partTime')}</option>
                <option value="por_horas">{t('hr:form.hourly')}</option>
              </select>
            </div>
            <div>
              <label className="gc-label">{t('hr:form.baseSalary')} *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.salario_base}
                onChange={(e) => setForm({ ...form, salario_base: Number(e.target.value) })}
                className="gc-input"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <label className="gc-label">{t('hr:form.bank')}</label>
              <input
                type="text"
                value={form.banco}
                onChange={(e) => setForm({ ...form, banco: e.target.value })}
                className="gc-input"
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:form.accountNumber')}</label>
              <input
                type="text"
                value={form.numero_cuenta}
                onChange={(e) => setForm({ ...form, numero_cuenta: e.target.value })}
                className="gc-input"
                placeholder="ES00 0000 0000 0000 0000 0000"
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-3">
            <div>
              <label className="gc-label">{t('hr:form.socialSecurity')}</label>
              <input
                type="text"
                value={form.seguridad_social}
                onChange={(e) => setForm({ ...form, seguridad_social: e.target.value })}
                className="gc-input"
                disabled={loading}
              />
            </div>
            <div>
              <label className="gc-label">{t('hr:employees.status')} *</label>
              <select
                value={form.estado}
                onChange={(e) => setForm({ ...form, estado: e.target.value as any })}
                className="gc-input"
                required
                disabled={loading}
              >
                <option value="activo">{t('hr:employees.active')}</option>
                <option value="baja">{t('hr:employees.terminatedStatus')}</option>
                <option value="suspendido">{t('hr:employees.suspended')}</option>
              </select>
            </div>
          </div>
        </fieldset>

        {/* Notes */}
        <div>
          <label className="gc-label">{t('hr:form.notes')}</label>
          <textarea
            value={form.notas}
            onChange={(e) => setForm({ ...form, notas: e.target.value })}
            className="gc-input"
            rows={3}
            disabled={loading}
          />
        </div>

        {/* Botones */}
        <div className="flex gap-2">
          <button
            type="submit"
            className="gc-btn gc-btn--primary"
            disabled={loading}
          >
            {loading ? t('hr:form.saving') : t('hr:form.save')}
          </button>
          <button
            type="button"
            className="gc-btn gc-btn--ghost"
            onClick={() => nav('..')}
            disabled={loading}
          >
            {t('hr:form.cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
