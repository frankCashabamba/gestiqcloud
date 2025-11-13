import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listVacaciones, aprobarVacacion, rechazarVacacion } from '../../services/api/rrhh'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Vacacion } from '../../types/rrhh'

export default function VacacionesList() {
  const [items, setItems] = useState<Vacacion[]>([])
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [estadoFilter, setEstadoFilter] = useState('')
  const [empleadoSearch, setEmpleadoSearch] = useState('')
  const [per, setPer] = useState(10)

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await listVacaciones()
      setItems(data?.items || data || [])
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filtered = useMemo(() => items.filter(v => {
    if (estadoFilter && v.estado !== estadoFilter) return false
    if (empleadoSearch) {
      const s = empleadoSearch.toLowerCase()
      if (!v.empleado_id.toLowerCase().includes(s)) return false
    }
    return true
  }), [items, estadoFilter, empleadoSearch])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(filtered, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const handleAprobar = async (id: string) => {
    try {
      await aprobarVacacion(id)
      success('Vacación aprobada')
      await loadData()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const handleRechazar = async (id: string) => {
    const motivo = prompt('Motivo del rechazo (opcional):')
    try {
      await rechazarVacacion(id, { motivo })
      success('Vacación rechazada')
      await loadData()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-lg">Vacaciones y Permisos</h2>
        <button
          className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
          onClick={() => nav('nueva')}
        >
          Nueva Solicitud
        </button>
      </div>

      {/* Filtros */}
      <div className="bg-white border rounded p-3 mb-3 grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Estado</label>
          <select
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value)}
            className="border px-2 py-1 rounded w-full text-sm"
          >
            <option value="">Todos</option>
            <option value="pendiente">Pendiente</option>
            <option value="aprobada">Aprobada</option>
            <option value="rechazada">Rechazada</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Buscar empleado</label>
          <input
            type="text"
            placeholder="ID empleado..."
            value={empleadoSearch}
            onChange={(e) => setEmpleadoSearch(e.target.value)}
            className="border px-2 py-1 rounded w-full text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Por página</label>
          <select
            value={per}
            onChange={(e) => setPer(Number(e.target.value))}
            className="border px-2 py-1 rounded w-full text-sm"
          >
            <option value="10">10</option>
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </div>
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto bg-white border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-3 py-2 text-left">Empleado</th>
              <th className="px-3 py-2 text-left">Tipo</th>
              <th className="px-3 py-2 text-left">Desde</th>
              <th className="px-3 py-2 text-left">Hasta</th>
              <th className="px-3 py-2 text-center">Días</th>
              <th className="px-3 py-2 text-center">Estado</th>
              <th className="px-3 py-2 text-center">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="text-center py-4 text-gray-500">
                  Cargando...
                </td>
              </tr>
            )}
            {!loading && view.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center py-4 text-gray-500">
                  No hay vacaciones registradas
                </td>
              </tr>
            )}
            {!loading && view.map((v) => (
              <tr key={v.id} className="border-t hover:bg-gray-50">
                <td className="px-3 py-2">
                  <Link to={`/rrhh/empleados/${v.empleado_id}`} className="text-blue-600 hover:underline">
                    {v.empleado_id}
                  </Link>
                </td>
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
                <td className="px-3 py-2 text-center">
                  {v.estado === 'pendiente' && (
                    <div className="flex gap-1 justify-center">
                      <button
                        onClick={() => handleAprobar(v.id)}
                        className="bg-green-600 text-white px-2 py-1 rounded text-xs hover:bg-green-700"
                      >
                        Aprobar
                      </button>
                      <button
                        onClick={() => handleRechazar(v.id)}
                        className="bg-red-600 text-white px-2 py-1 rounded text-xs hover:bg-red-700"
                      >
                        Rechazar
                      </button>
                    </div>
                  )}
                  {v.estado !== 'pendiente' && (
                    <span className="text-gray-400 text-xs">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        className="mt-3"
      />

      <p className="text-xs text-gray-500 mt-2">
        Mostrando {view.length} de {filtered.length} vacaciones
      </p>
    </div>
  )
}
