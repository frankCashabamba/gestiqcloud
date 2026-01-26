import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listVacaciones, aprobarVacacion, rechazarVacacion } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Vacacion } from '../../types/hr'

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
      success('Vacation approved')
      await loadData()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const handleRechazar = async (id: string) => {
    const motivo = prompt('Reason for rejection (optional):')
    try {
      await rechazarVacacion(id, { motivo })
      success('Vacation rejected')
      await loadData()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-lg">Vacations and Leaves</h2>
        <button
          className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
          onClick={() => nav('nueva')}
        >
          New Request
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white border rounded p-3 mb-3 grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Status</label>
          <select
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value)}
            className="border px-2 py-1 rounded w-full text-sm"
          >
            <option value="">All</option>
            <option value="pendiente">Pending</option>
            <option value="aprobada">Approved</option>
            <option value="rechazada">Rejected</option>
            <option value="cancelada">Cancelled</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Search employee</label>
          <input
            type="text"
            placeholder="Employee ID..."
            value={empleadoSearch}
            onChange={(e) => setEmpleadoSearch(e.target.value)}
            className="border px-2 py-1 rounded w-full text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Per page</label>
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

      {/* Table */}
      <div className="overflow-x-auto bg-white border rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-3 py-2 text-left">Employee</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">From</th>
              <th className="px-3 py-2 text-left">To</th>
              <th className="px-3 py-2 text-center">Days</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="text-center py-4 text-gray-500">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && view.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center py-4 text-gray-500">
                  No vacations recorded
                </td>
              </tr>
            )}
            {!loading && view.map((v) => (
              <tr key={v.id} className="border-t hover:bg-gray-50">
                <td className="px-3 py-2">
                  <Link to={`/hr/employees/${v.empleado_id}`} className="text-blue-600 hover:underline">
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
                        Approve
                      </button>
                      <button
                        onClick={() => handleRechazar(v.id)}
                        className="bg-red-600 text-white px-2 py-1 rounded text-xs hover:bg-red-700"
                      >
                        Reject
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
        Showing {view.length} of {filtered.length} vacations
      </p>
    </div>
  )
}
