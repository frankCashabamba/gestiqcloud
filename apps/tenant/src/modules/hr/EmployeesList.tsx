import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listEmpleados } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Empleado } from '../../types/hr'
import { PAGINATION_DEFAULTS } from '../../constants/defaults'

export default function EmpleadosList() {
    const [items, setItems] = useState<Empleado[]>([])
    const [loading, setLoading] = useState(false)
    const nav = useNavigate()
    const { error: toastError } = useToast()

    const [search, setSearch] = useState('')
    const [departamento, setDepartamento] = useState('')
    const [estadoFilter, setEstadoFilter] = useState('')
    const [per, setPer] = useState(PAGINATION_DEFAULTS.RRHH_PER_PAGE)

    useEffect(() => {
        (async () => {
            try {
                setLoading(true)
                const data = await listEmpleados()
                setItems(data?.items || data || [])
            } catch (e: any) {
                toastError(getErrorMessage(e))
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    const filtered = useMemo(() => items.filter(v => {
        if (departamento && v.departamento_id !== departamento) return false
        if (estadoFilter && v.estado !== estadoFilter) return false
        if (search) {
            const s = search.toLowerCase()
            const matches =
                (v.sku || '').toLowerCase().includes(s) ||
                v.name.toLowerCase().includes(s) ||
                v.apellidos.toLowerCase().includes(s) ||
                v.numero_documento.toLowerCase().includes(s) ||
                (v.puesto || '').toLowerCase().includes(s)
            if (!matches) return false
        }
        return true
    }), [items, departamento, estadoFilter, search])

    const { page, setPage, totalPages, view, setPerPage } = usePagination(filtered, per)
    useEffect(() => setPerPage(per), [per, setPerPage])

    const departamentos = Array.from(new Set(items.map(e => e.departamento_id).filter(Boolean)))

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-4">
                <h2 className="font-semibold text-lg">Employees</h2>
                <button
                    className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                    onClick={() => nav('nuevo')}
                >
                    New Employee
                </button>
            </div>

            {/* Filters */}
            <div className="bg-white border rounded p-3 mb-3 grid grid-cols-1 md:grid-cols-4 gap-3">
                <div>
                    <label className="block text-sm font-medium mb-1">Search</label>
                    <input
                        type="text"
                        placeholder="Code, name, document..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="border px-2 py-1 rounded w-full text-sm"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">Department</label>
                    <select
                        value={departamento}
                        onChange={(e) => setDepartamento(e.target.value)}
                        className="border px-2 py-1 rounded w-full text-sm"
                    >
                        <option value="">All</option>
                        {departamentos.map((d) => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">Status</label>
                    <select
                        value={estadoFilter}
                        onChange={(e) => setEstadoFilter(e.target.value)}
                        className="border px-2 py-1 rounded w-full text-sm"
                    >
                        <option value="">All</option>
                        <option value="activo">Active</option>
                        <option value="baja">Terminated</option>
                        <option value="suspendido">Suspended</option>
                    </select>
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
                            <th className="px-3 py-2 text-left">Code</th>
                            <th className="px-3 py-2 text-left">Name</th>
                            <th className="px-3 py-2 text-left">Position</th>
                            <th className="px-3 py-2 text-left">Department</th>
                            <th className="px-3 py-2 text-left">Start Date</th>
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
                                    No employees
                                </td>
                            </tr>
                        )}
                        {!loading && view.map((e) => (
                            <tr key={e.id} className="border-t hover:bg-gray-50">
                                <td className="px-3 py-2">{e.sku || '-'}</td>
                                <td className="px-3 py-2">
                                    <Link to={e.id} className="text-blue-600 hover:underline">
                                        {e.name} {e.apellidos}
                                    </Link>
                                </td>
                                <td className="px-3 py-2">{e.puesto || '-'}</td>
                                <td className="px-3 py-2">{e.departamento_id || '-'}</td>
                                <td className="px-3 py-2">{e.fecha_ingreso}</td>
                                <td className="px-3 py-2 text-center">
                                    <span
                                        className={`inline-block px-2 py-1 text-xs rounded ${e.estado === 'activo'
                                                ? 'bg-green-100 text-green-800'
                                                : e.estado === 'baja'
                                                    ? 'bg-red-100 text-red-800'
                                                    : 'bg-yellow-100 text-yellow-800'
                                            }`}
                                    >
                                        {e.estado}
                                    </span>
                                </td>
                                <td className="px-3 py-2 text-center">
                                    <Link
                                        to={`${e.id}/editar`}
                                        className="text-blue-600 hover:underline text-xs mr-2"
                                    >
                                        Edit
                                    </Link>
                                    <Link
                                        to={e.id}
                                        className="text-gray-600 hover:underline text-xs"
                                    >
                                        View
                                    </Link>
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
                Showing {view.length} of {filtered.length} employees
            </p>
        </div>
    )
}
