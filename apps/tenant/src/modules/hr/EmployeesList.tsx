import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listEmpleados } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Empleado } from '../../types/hr'
import { PAGINATION_DEFAULTS } from '../../constants/defaults'

export default function EmpleadosList() {
    const { t } = useTranslation(['hr', 'common'])
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
                <h2 className="font-semibold text-lg">{t('hr:employees.title')}</h2>
                <button
                    className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                    onClick={() => nav('nuevo')}
                >
                    {t('hr:employees.new')}
                </button>
            </div>

            {/* Filters */}
            <div className="bg-white border rounded p-3 mb-3 grid grid-cols-1 md:grid-cols-4 gap-3">
                <div>
                    <label className="block text-sm font-medium mb-1">{t('hr:employees.search')}</label>
                    <input
                        type="text"
                        placeholder={t('hr:employees.searchPlaceholder')}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="border px-2 py-1 rounded w-full text-sm"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">{t('hr:employees.department')}</label>
                    <select
                        value={departamento}
                        onChange={(e) => setDepartamento(e.target.value)}
                        className="border px-2 py-1 rounded w-full text-sm"
                    >
                        <option value="">{t('hr:employees.all')}</option>
                        {departamentos.map((d) => (
                            <option key={d} value={d}>{d}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">{t('hr:employees.status')}</label>
                    <select
                        value={estadoFilter}
                        onChange={(e) => setEstadoFilter(e.target.value)}
                        className="border px-2 py-1 rounded w-full text-sm"
                    >
                        <option value="">{t('hr:employees.all')}</option>
                        <option value="activo">{t('hr:employees.active')}</option>
                        <option value="baja">{t('hr:employees.terminatedStatus')}</option>
                        <option value="suspendido">{t('hr:employees.suspended')}</option>
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1">{t('hr:employees.perPage')}</label>
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
                            <th className="px-3 py-2 text-left">{t('hr:employees.code')}</th>
                            <th className="px-3 py-2 text-left">{t('hr:employees.name')}</th>
                            <th className="px-3 py-2 text-left">{t('hr:employees.position')}</th>
                            <th className="px-3 py-2 text-left">{t('hr:employees.department')}</th>
                            <th className="px-3 py-2 text-left">{t('hr:employees.startDate')}</th>
                            <th className="px-3 py-2 text-center">{t('hr:employees.status')}</th>
                            <th className="px-3 py-2 text-center">{t('hr:employees.actions')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && (
                            <tr>
                                <td colSpan={7} className="text-center py-4 text-gray-500">
                                    {t('hr:employees.loading')}
                                </td>
                            </tr>
                        )}
                        {!loading && view.length === 0 && (
                            <tr>
                                <td colSpan={7} className="text-center py-4 text-gray-500">
                                    {t('hr:employees.empty')}
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
                                        {t('hr:employees.edit_action')}
                                    </Link>
                                    <Link
                                        to={e.id}
                                        className="text-gray-600 hover:underline text-xs"
                                    >
                                        {t('hr:employees.view')}
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
                {t('hr:employees.showing', { current: view.length, total: filtered.length })}
            </p>
        </div>
    )
}
