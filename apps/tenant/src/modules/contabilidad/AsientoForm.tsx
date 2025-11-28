import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createAsiento, getAsiento, updateAsiento, listCuentas, type AsientoContable, type AsientoLinea, type PlanCuenta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function AsientoForm() {
    const { id } = useParams()
    const nav = useNavigate()
    const [form, setForm] = useState<Partial<AsientoContable>>({
        numero: '',
        fecha: new Date().toISOString().split('T')[0],
        descripcion: '',
        status: 'DRAFT',
        lineas: [],
    })
    const { success, error } = useToast()
    const [cuentas, setCuentas] = useState<PlanCuenta[]>([])

    useEffect(() => {
        if (!id) return
        getAsiento(id).then((x) => setForm({ ...x }))
    }, [id])

    useEffect(() => {
        listCuentas().then(setCuentas).catch(() => setCuentas([]))
    }, [])

    const addLinea = () => {
        const newLinea: Partial<AsientoLinea> = {
            cuenta_id: '',
            debe: 0,
            haber: 0,
            descripcion: '',
        }
        setForm({ ...form, lineas: [...(form.lineas || []), newLinea as AsientoLinea] })
    }

    const updateLinea = (index: number, field: keyof AsientoLinea, value: any) => {
        const updated = [...(form.lineas || [])]
        updated[index] = { ...updated[index], [field]: value }
        setForm({ ...form, lineas: updated })
    }

    const removeLinea = (index: number) => {
        const updated = [...(form.lineas || [])]
        updated.splice(index, 1)
        setForm({ ...form, lineas: updated })
    }

    const calcularTotales = () => {
        let debe = 0
        let haber = 0
        for (const l of form.lineas || []) {
            debe += parseFloat(String(l.debe || 0))
            haber += parseFloat(String(l.haber || 0))
        }
        return { debe, haber, balance: debe - haber }
    }

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            if (!form.numero || !form.fecha) throw new Error('Number and date are required')
            if (!form.lineas || form.lineas.length === 0) throw new Error('Must add at least one line')

            const { debe, haber, balance } = calcularTotales()
            if (Math.abs(balance) > 0.01) throw new Error(`Asiento descuadrado: Debe=${debe.toFixed(2)}, Haber=${haber.toFixed(2)}`)

            const payload = {
                ...form,
                total_debe: debe,
                total_haber: haber,
            }

            if (id) await updateAsiento(id, payload)
            else await createAsiento(payload)

            success('Entry saved')
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const totales = calcularTotales()

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? 'Edit Entry' : 'New Entry'}</h3>
            <form onSubmit={onSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block mb-1">Número *</label>
                        <input
                            type="text"
                            value={form.numero || ''}
                            onChange={(e) => setForm({ ...form, numero: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            required
                            placeholder="A-001"
                        />
                    </div>

                    <div>
                        <label className="block mb-1">Fecha *</label>
                        <input
                            type="date"
                            value={form.fecha || ''}
                            onChange={(e) => setForm({ ...form, fecha: e.target.value })}
                            className="border px-2 py-1 w-full rounded"
                            required
                        />
                    </div>
                </div>

                <div>
                    <label className="block mb-1">Descripción</label>
                    <textarea
                        value={form.descripcion || ''}
                        onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        rows={2}
                    />
                </div>

                <div className="border-t pt-4">
                    <div className="flex justify-between items-center mb-3">
                        <h4 className="font-semibold">Líneas del Asiento</h4>
                        <button
                            type="button"
                            onClick={addLinea}
                            className="bg-green-600 text-white px-3 py-1 rounded text-sm"
                        >
                            + Añadir Línea
                        </button>
                    </div>

                    <table className="w-full border">
                        <thead className="bg-gray-100">
                            <tr>
                                <th className="border px-2 py-1 text-left">Cuenta</th>
                                <th className="border px-2 py-1 text-right">Debe</th>
                                <th className="border px-2 py-1 text-right">Haber</th>
                                <th className="border px-2 py-1 text-left">Descripción</th>
                                <th className="border px-2 py-1 w-20"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {(form.lineas || []).map((linea, idx) => (
                                <tr key={idx}>
                                    <td className="border px-2 py-1">
                                        <select
                                            value={linea.cuenta_id || ''}
                                            onChange={(e) => updateLinea(idx, 'cuenta_id', e.target.value)}
                                            className="w-full border px-1 py-1 rounded"
                                            required
                                        >
                                            <option value="">Seleccionar...</option>
                                            {cuentas.map((c) => (
                                                <option key={c.id} value={c.id}>
                                                    {c.codigo} - {c.nombre}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="border px-2 py-1">
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={linea.debe || 0}
                                            onChange={(e) => updateLinea(idx, 'debe', parseFloat(e.target.value) || 0)}
                                            className="w-full border px-1 py-1 rounded text-right"
                                        />
                                    </td>
                                    <td className="border px-2 py-1">
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={linea.haber || 0}
                                            onChange={(e) => updateLinea(idx, 'haber', parseFloat(e.target.value) || 0)}
                                            className="w-full border px-1 py-1 rounded text-right"
                                        />
                                    </td>
                                    <td className="border px-2 py-1">
                                        <input
                                            type="text"
                                            value={linea.descripcion || ''}
                                            onChange={(e) => updateLinea(idx, 'descripcion', e.target.value)}
                                            className="w-full border px-1 py-1 rounded"
                                        />
                                    </td>
                                    <td className="border px-2 py-1 text-center">
                                        <button
                                            type="button"
                                            onClick={() => removeLinea(idx)}
                                            className="text-red-600 hover:underline text-sm"
                                        >
                                            Eliminar
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                        <tfoot className="bg-gray-100 font-semibold">
                            <tr>
                                <td className="border px-2 py-2 text-right">TOTALES:</td>
                                <td className="border px-2 py-2 text-right">{totales.debe.toFixed(2)}</td>
                                <td className="border px-2 py-2 text-right">{totales.haber.toFixed(2)}</td>
                                <td className="border px-2 py-2" colSpan={2}>
                                    {Math.abs(totales.balance) < 0.01 ? (
                                        <span className="text-green-600">✅ Cuadrado</span>
                                    ) : (
                                        <span className="text-red-600">❌ Descuadrado ({totales.balance.toFixed(2)})</span>
                                    )}
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <div className="pt-4 flex gap-2">
                    <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
                        Guardar Asiento
                    </button>
                    <button type="button" className="px-4 py-2 border rounded" onClick={() => nav('..')}>
                        Cancelar
                    </button>
                </div>
            </form>
        </div>
    )
}
