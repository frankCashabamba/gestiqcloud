import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listAsientos, removeAsiento, postAsiento, type AsientoContable } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function AsientosList() {
    const nav = useNavigate()
    const [items, setItems] = useState<AsientoContable[]>([])
    const [loading, setLoading] = useState(false)
    const [filter, setFilter] = useState('')
    const { success, error } = useToast()

    const load = async () => {
        try {
            setLoading(true)
            const data = await listAsientos()
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

    const onDelete = async (id: string, numero: string) => {
        if (!confirm(`¿Eliminar asiento "${numero}"?`)) return
        try {
            await removeAsiento(id)
            success('Asiento eliminado')
            load()
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const onPost = async (id: string, numero: string) => {
        if (!confirm(`¿Contabilizar asiento "${numero}"? Esta acción no se puede deshacer.`)) return
        try {
            await postAsiento(id)
            success('Asiento contabilizado')
            load()
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const filtered = items.filter(
        (a) =>
            a.numero.toLowerCase().includes(filter.toLowerCase()) ||
            a.descripcion?.toLowerCase().includes(filter.toLowerCase())
    )

    const getStatusBadge = (status: string) => {
        const colors = {
            DRAFT: 'bg-gray-100 text-gray-800',
            POSTED: 'bg-green-100 text-green-800',
            VOIDED: 'bg-red-100 text-red-800',
        }
        return colors[status as keyof typeof colors] || colors.DRAFT
    }

    return (
        <div className="p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-2xl font-semibold">Asientos Contables</h3>
                <button
                    onClick={() => nav('asientos/nuevo')}
                    className="bg-blue-600 text-white px-3 py-2 rounded"
                >
                    + Nuevo Asiento
                </button>
            </div>

            <div className="mb-4">
                <input
                    type="search"
                    placeholder="Buscar por número o descripción..."
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
                            <th className="border px-3 py-2 text-left">Número</th>
                            <th className="border px-3 py-2 text-left">Fecha</th>
                            <th className="border px-3 py-2 text-left">Descripción</th>
                            <th className="border px-3 py-2 text-right">Debe</th>
                            <th className="border px-3 py-2 text-right">Haber</th>
                            <th className="border px-3 py-2 text-center">Estado</th>
                            <th className="border px-3 py-2 text-center">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((a) => (
                            <tr key={a.id} className="hover:bg-gray-50">
                                <td className="border px-3 py-2">
                                    <span className="font-mono">{a.numero}</span>
                                </td>
                                <td className="border px-3 py-2">{a.fecha}</td>
                                <td className="border px-3 py-2">{a.descripcion}</td>
                                <td className="border px-3 py-2 text-right font-mono">
                                    {a.total_debe?.toFixed(2) || '0.00'}
                                </td>
                                <td className="border px-3 py-2 text-right font-mono">
                                    {a.total_haber?.toFixed(2) || '0.00'}
                                </td>
                                <td className="border px-3 py-2 text-center">
                                    <span className={`px-2 py-1 rounded text-xs ${getStatusBadge(a.status)}`}>
                                        {a.status}
                                    </span>
                                </td>
                                <td className="border px-3 py-2 text-center">
                                    {a.status === 'DRAFT' && (
                                        <>
                                            <button
                                                onClick={() => nav(`asientos/${a.id}/editar`)}
                                                className="text-blue-600 hover:underline mr-2"
                                            >
                                                Editar
                                            </button>
                                            <button
                                                onClick={() => onPost(a.id, a.numero)}
                                                className="text-green-600 hover:underline mr-2"
                                            >
                                                Contabilizar
                                            </button>
                                            <button
                                                onClick={() => onDelete(a.id, a.numero)}
                                                className="text-red-600 hover:underline"
                                            >
                                                Eliminar
                                            </button>
                                        </>
                                    )}
                                    {a.status === 'POSTED' && (
                                        <span className="text-gray-500 text-sm">Contabilizado</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                        {!loading && filtered.length === 0 && (
                            <tr>
                                <td colSpan={7} className="border px-3 py-8 text-center text-gray-500">
                                    No hay asientos. <button onClick={() => nav('asientos/nuevo')} className="text-blue-600 hover:underline">Crear el primero</button>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
