import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCuenta, getCuenta, updateCuenta, listCuentas, type PlanCuenta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function PlanCuentasForm() {
    const { id } = useParams()
    const nav = useNavigate()
    const [form, setForm] = useState<Partial<PlanCuenta>>({
        codigo: '',
        nombre: '',
        tipo: 'ACTIVO',
        nivel: 1,
        activo: true,
    })
    const { success, error } = useToast()
    const [cuentasPadre, setCuentasPadre] = useState<PlanCuenta[]>([])

    useEffect(() => {
        if (!id) return
        getCuenta(id).then((x) => setForm({ ...x }))
    }, [id])

    useEffect(() => {
        listCuentas().then(setCuentasPadre).catch(() => setCuentasPadre([]))
    }, [])

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            if (!form.codigo || !form.nombre) throw new Error('Código y nombre son obligatorios')
            if (id) await updateCuenta(id, form)
            else await createCuenta(form)
            success('Cuenta guardada')
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? 'Editar cuenta' : 'Nueva cuenta'}</h3>
            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
                <div>
                    <label className="block mb-1">Código *</label>
                    <input
                        type="text"
                        value={form.codigo || ''}
                        onChange={(e) => setForm({ ...form, codigo: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        required
                        placeholder="Ej: 1000, 2000"
                    />
                </div>

                <div>
                    <label className="block mb-1">Nombre *</label>
                    <input
                        type="text"
                        value={form.nombre || ''}
                        onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        required
                    />
                </div>

                <div>
                    <label className="block mb-1">Tipo *</label>
                    <select
                        value={form.tipo || 'ACTIVO'}
                        onChange={(e) => setForm({ ...form, tipo: e.target.value as any })}
                        className="border px-2 py-1 w-full rounded"
                        required
                    >
                        <option value="ACTIVO">Activo</option>
                        <option value="PASIVO">Pasivo</option>
                        <option value="PATRIMONIO">Patrimonio</option>
                        <option value="INGRESO">Ingreso</option>
                        <option value="GASTO">Gasto</option>
                    </select>
                </div>

                <div>
                    <label className="block mb-1">Nivel</label>
                    <input
                        type="number"
                        value={form.nivel || 1}
                        onChange={(e) => setForm({ ...form, nivel: parseInt(e.target.value) || 1 })}
                        className="border px-2 py-1 w-full rounded"
                        min="1"
                        max="5"
                    />
                </div>

                <div>
                    <label className="block mb-1">Cuenta Padre (Opcional)</label>
                    <select
                        value={form.padre_id || ''}
                        onChange={(e) => setForm({ ...form, padre_id: e.target.value || null })}
                        className="border px-2 py-1 w-full rounded"
                    >
                        <option value="">Sin padre (cuenta de nivel superior)</option>
                        {cuentasPadre.map((c) => (
                            <option key={c.id} value={c.id}>
                                {c.codigo} - {c.nombre}
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            checked={form.activo ?? true}
                            onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                        />
                        <span>Activo</span>
                    </label>
                </div>

                <div className="pt-2 flex gap-2">
                    <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">
                        Guardar
                    </button>
                    <button type="button" className="px-3 py-2 border rounded" onClick={() => nav('..')}>
                        Cancelar
                    </button>
                </div>
            </form>
        </div>
    )
}
