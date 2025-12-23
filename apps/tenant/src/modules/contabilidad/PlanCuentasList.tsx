import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listCuentas, removeCuenta, type PlanCuenta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function PlanCuentasList() {
    const nav = useNavigate()
    const [items, setItems] = useState<PlanCuenta[]>([])
    const [loading, setLoading] = useState(false)
    const [filter, setFilter] = useState('')
    const { success, error } = useToast()

    const load = async () => {
        try {
            setLoading(true)
            const data = await listCuentas()
            setItems(data)
        } catch (e: any) {
            error(getErrorMessage(e))
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        load()
    }, [])

    const onDelete = async (id: string, nombre: string) => {
        if (!confirm(`¿Eliminar cuenta "${nombre}"?`)) return
        try {
            await removeCuenta(id)
            success('Cuenta eliminada')
            load()
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const filtered = items.filter(
        (c) =>
            c.codigo.toLowerCase().includes(filter.toLowerCase()) ||
            c.nombre.toLowerCase().includes(filter.toLowerCase())
    )

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-2xl font-semibold">Plan de Cuentas</h3>
                <button
                    onClick={() => nav('../plan-cuentas/nuevo')}
                    className="bg-blue-600 text-white px-3 py-2 rounded"
                >
                    + Nueva Cuenta
                </button>
            </div>

            <div className="mb-4">
                <input
                    type="search"
                    placeholder="Buscar por código o nombre..."
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="border px-3 py-2 rounded w-full max-w-md"
                />
            </div>

            {loading && <div>Cargando...</div>}

            <div className="overflow-x-auto">
                <table className="min-w-full border">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="border px-3 py-2 text-left">Código</th>
                            <th className="border px-3 py-2 text-left">Nombre</th>
                            <th className="border px-3 py-2 text-left">Tipo</th>
                            <th className="border px-3 py-2 text-center">Nivel</th>
                            <th className="border px-3 py-2 text-center">Activo</th>
                            <th className="border px-3 py-2 text-center">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((c) => (
                            <tr key={c.id} className="hover:bg-gray-50">
                                <td className="border px-3 py-2">
                                    <span className="font-mono">{c.codigo}</span>
                                </td>
                                <td className="border px-3 py-2">{c.nombre}</td>
                                <td className="border px-3 py-2">
                                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                                        {c.tipo}
                                    </span>
                                </td>
                                <td className="border px-3 py-2 text-center">{c.nivel}</td>
                                <td className="border px-3 py-2 text-center">
                                    {c.activo ? '✅' : '❌'}
                                </td>
                                <td className="border px-3 py-2 text-center">
                                    <button
                                        onClick={() => nav(`../plan-cuentas/${c.id}/editar`)}
                                        className="text-blue-600 hover:underline mr-2"
                                    >
                                        Editar
                                    </button>
                                    <button
                                        onClick={() => onDelete(c.id, c.nombre)}
                                        className="text-red-600 hover:underline"
                                    >
                                        Eliminar
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {!loading && filtered.length === 0 && (
                            <tr>
                                <td colSpan={6} className="border px-3 py-8 text-center text-gray-500">
                                    No hay cuentas. <button onClick={() => nav('../plan-cuentas/nuevo')} className="text-blue-600 hover:underline">Crear la primera</button>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
