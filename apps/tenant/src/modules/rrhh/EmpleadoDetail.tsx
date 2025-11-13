import React, { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { getEmpleado, updateEmpleado } from '../../services/api/rrhh'
import { listVacaciones } from '../../services/api/rrhh'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { Empleado, Vacacion } from '../../types/rrhh'

export default function EmpleadoDetail() {
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
    if (!confirm('¿Dar de baja a este empleado?')) return

    try {
      await updateEmpleado(id, { estado: 'baja', fecha_salida: new Date().toISOString().slice(0, 10) })
      success('Empleado dado de baja')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  if (loading || !empleado) {
    return (
      <div className="p-4">
        <p className="text-gray-500">Cargando...</p>
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
            Editar
          </Link>
          {empleado.estado === 'activo' && (
            <button
              onClick={handleBaja}
              className="bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 text-sm"
            >
              Dar de Baja
            </button>
          )}
          <button
            onClick={() => nav('..')}
            className="bg-gray-300 px-3 py-1 rounded hover:bg-gray-400 text-sm"
          >
            Volver
          </button>
        </div>
      </div>

      {/* Info Personal */}
      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold text-lg mb-3">Información Personal</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Código:</span>
            <p className="font-medium">{empleado.sku || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Documento:</span>
            <p className="font-medium">{empleado.tipo_documento} {empleado.numero_documento}</p>
          </div>
          <div>
            <span className="text-gray-500">Fecha Nacimiento:</span>
            <p className="font-medium">{empleado.fecha_nacimiento || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Email:</span>
            <p className="font-medium">{empleado.email || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Teléfono:</span>
            <p className="font-medium">{empleado.phone || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Estado:</span>
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

      {/* Info Laboral */}
      <div className="bg-white border rounded p-4 mb-4">
        <h3 className="font-semibold text-lg mb-3">Información Laboral</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Fecha Ingreso:</span>
            <p className="font-medium">{empleado.fecha_ingreso}</p>
          </div>
          {empleado.fecha_salida && (
            <div>
              <span className="text-gray-500">Fecha Salida:</span>
              <p className="font-medium">{empleado.fecha_salida}</p>
            </div>
          )}
          <div>
            <span className="text-gray-500">Departamento:</span>
            <p className="font-medium">{empleado.departamento_id || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Puesto:</span>
            <p className="font-medium">{empleado.puesto || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Tipo Contrato:</span>
            <p className="font-medium capitalize">{empleado.tipo_contrato.replace('_', ' ')}</p>
          </div>
          <div>
            <span className="text-gray-500">Jornada:</span>
            <p className="font-medium capitalize">{empleado.jornada.replace('_', ' ')}</p>
          </div>
          <div>
            <span className="text-gray-500">Salario Base:</span>
            <p className="font-medium">${empleado.salario_base.toFixed(2)}</p>
          </div>
          <div>
            <span className="text-gray-500">Banco:</span>
            <p className="font-medium">{empleado.banco || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Cuenta:</span>
            <p className="font-medium">{empleado.numero_cuenta || '-'}</p>
          </div>
          <div>
            <span className="text-gray-500">Seguridad Social:</span>
            <p className="font-medium">{empleado.seguridad_social || '-'}</p>
          </div>
        </div>
        {empleado.notas && (
          <div className="mt-3">
            <span className="text-gray-500 text-sm">Notas:</span>
            <p className="text-sm mt-1">{empleado.notas}</p>
          </div>
        )}
      </div>

      {/* Vacaciones */}
      <div className="bg-white border rounded p-4">
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-lg">Vacaciones y Permisos</h3>
          <Link
            to="/rrhh/vacaciones/nueva"
            state={{ empleadoId: id }}
            className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
          >
            Nueva Solicitud
          </Link>
        </div>

        {vacaciones.length === 0 ? (
          <p className="text-gray-500 text-sm">No hay vacaciones registradas</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left">Tipo</th>
                  <th className="px-3 py-2 text-left">Desde</th>
                  <th className="px-3 py-2 text-left">Hasta</th>
                  <th className="px-3 py-2 text-center">Días</th>
                  <th className="px-3 py-2 text-center">Estado</th>
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
