import React, { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getEmpleado, updateEmpleado } from '../../services/api/hr'
import { listVacaciones } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { Empleado, Vacacion } from '../../types/hr'

export default function EmpleadoDetail() {
  const { t } = useTranslation(['hr', 'common'])
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()

  const [empleado, setEmpleado] = useState<Empleado | null>(null)
  const [vacaciones, setVacaciones] = useState<Vacacion[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      getEmpleado(id),
      listVacaciones({ empleadoId: id })
    ])
      .then(([emp, vacs]) => {
        setEmpleado(emp)
        setVacaciones(vacs?.items || vacs || [])
      })
      .catch((e) => error(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [id])

  const handleBaja = async () => {
    if (!empleado || !id) return
    if (!confirm(t('hr:employees.terminateConfirm'))) return

    try {
      await updateEmpleado(id, { estado: 'baja', fecha_salida: new Date().toISOString().slice(0, 10) })
      success(t('hr:employees.terminated'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  if (loading || !empleado) {
    return (
      <div className="p-4">
        <p className="text-gray-500">{t('hr:employees.loading')}</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">
          {empleado.name} {empleado.apellidos}
        </h2>
        <div className="flex gap-2">
          <Link
            to="editar"
            className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 text-sm"
          >
            {t('hr:employees.edit_action')}
          </Link>
          {empleado.estado === 'activo' && (
            <button
              onClick={handleBaja}
              className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 text-sm"
            >
              {t('hr:employees.terminate')}
            </button>
          )}
          <button
            onClick={() => nav('..')}
            className="bg-gray-300 px-3 py-1 rounded hover:bg-gray-400 text-sm"
          >
            {t('hr:employees.back')}
          </button>
        </div>
      </div>

      {/* Personal Info */}
      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold text-lg mb-3">{t('hr:detail.personalInfo')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">{t('hr:employees.code')}:</span>
            <p className="font-medium">{empleado.sku || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:detail.document')}:</span>
            <p className="font-medium">{empleado.tipo_documento} {empleado.numero_documento}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.birthDate')}:</span>
            <p className="font-medium">{empleado.fecha_nacimiento || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.email')}:</span>
            <p className="font-medium">{empleado.email || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.phone')}:</span>
            <p className="font-medium">{empleado.phone || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:employees.status')}:</span>
            <p>
              <span
                className={`inline-block px-2 py-1 text-xs rounded ${
                  empleado.estado === 'activo'
                    ? 'bg-green-100 text-green-800'
                    : empleado.estado === 'baja'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                {empleado.estado}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Employment Info */}
      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold text-lg mb-3">{t('hr:detail.employmentInfo')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">{t('hr:employees.startDate')}:</span>
            <p className="font-medium">{empleado.fecha_ingreso}</p>
          </div>
          {empleado.fecha_salida && (
            <div>
              <span className="text-gray-500">{t('hr:detail.endDate')}:</span>
              <p className="font-medium">{empleado.fecha_salida}</p>
            </div>
          )}
          <div>
            <span className="text-gray-500">{t('hr:employees.department')}:</span>
            <p className="font-medium">{empleado.departamento_id || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:employees.position')}:</span>
            <p className="font-medium">{empleado.puesto || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.contractType')}:</span>
            <p className="font-medium capitalize">{empleado.tipo_contrato.replace('_', ' ')}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.workSchedule')}:</span>
            <p className="font-medium capitalize">{empleado.jornada.replace('_', ' ')}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.baseSalary')}:</span>
            <p className="font-medium">${empleado.salario_base.toFixed(2)}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.bank')}:</span>
            <p className="font-medium">{empleado.banco || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:detail.account')}:</span>
            <p className="font-medium">{empleado.numero_cuenta || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">{t('hr:form.socialSecurity')}:</span>
            <p className="font-medium">{empleado.seguridad_social || '-'}</p>
          </div>
        </div>
        {empleado.notas && (
          <div className="mt-3">
            <span className="text-gray-500 text-sm">{t('hr:form.notes')}:</span>
            <p className="text-sm mt-1">{empleado.notas}</p>
          </div>
        )}
      </div>

      {/* Vacations */}
      <div className="bg-white border rounded p-4">
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-lg">{t('hr:vacations.title')}</h3>
          <Link
            to="/hr/vacations/new"
            state={{ empleadoId: id }}
            className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
          >
            {t('hr:vacations.newRequest')}
          </Link>
        </div>

        {vacaciones.length === 0 ? (
          <p className="text-gray-500 text-sm">{t('hr:vacations.empty')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left">{t('hr:vacations.type')}</th>
                  <th className="px-3 py-2 text-left">{t('hr:vacations.from')}</th>
                  <th className="px-3 py-2 text-left">{t('hr:vacations.to')}</th>
                  <th className="px-3 py-2 text-center">{t('hr:vacations.days')}</th>
                  <th className="px-3 py-2 text-center">{t('hr:vacations.status')}</th>
                </tr>
              </thead>
              <tbody>
                {vacaciones.map((v) => (
                  <tr key={v.id} className="border-t">
                    <td className="px-3 py-2 capitalize">{v.tipo.replace('_', ' ')}</td>
                    <td className="px-3 py-2">{v.fecha_inicio}</td>
                    <td className="px-3 py-2">{v.fecha_fin}</td>
                    <td className="px-3 py-2 text-center">{v.dias}</td>
                    <td className="px-3 py-2 text-center">
                      <span
                        className={`inline-block px-2 py-1 text-xs rounded ${
                          v.estado === 'aprobada'
                            ? 'bg-green-100 text-green-800'
                            : v.estado === 'rechazada'
                            ? 'bg-red-100 text-red-800'
                            : v.estado === 'cancelada'
                            ? 'bg-gray-100 text-gray-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {v.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
