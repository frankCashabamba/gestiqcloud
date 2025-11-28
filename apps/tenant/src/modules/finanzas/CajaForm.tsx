import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createMovimientoCaja, type Movimiento } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type FieldCfg = { field: string; visible?: boolean; required?: boolean; ord?: number | null; label?: string | null; help?: string | null }

export default function CajaForm() {
    const { id, empresa } = useParams()
    const nav = useNavigate()
    const [form, setForm] = useState<Partial<Omit<Movimiento, 'id'>>>({
        fecha: new Date().toISOString().slice(0, 10),
        tipo: 'ingreso',
        monto: 0
    })
    const { success, error } = useToast()
    const [fields, setFields] = useState<FieldCfg[] | null>(null)
    const [loadingCfg, setLoadingCfg] = useState(false)

    useEffect(() => {
        if (!id) return
        // TODO: Implementar getMovimientoCaja cuando esté disponible en services
        // getMovimientoCaja(id).then((x) => setForm({ ...x }))
    }, [id])

    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                setLoadingCfg(true)
                const q = new URLSearchParams({ module: 'caja', ...(empresa ? { empresa } : {}) }).toString()
                const data = await apiFetch<{ items?: FieldCfg[] }>(`/api/v1/tenant/settings/fields?${q}`)
                if (!cancelled) setFields((data?.items || []).filter(it => it.visible !== false))
            } catch {
                if (!cancelled) setFields(null)
            } finally {
                if (!cancelled) setLoadingCfg(false)
            }
        })()
        return () => { cancelled = true }
    }, [empresa])

    const fieldList = useMemo(() => {
        const base: FieldCfg[] = [
            { field: 'fecha', visible: true, required: true, ord: 10, label: 'Date' },
            { field: 'tipo', visible: true, required: true, ord: 20, label: 'Type' },
            { field: 'concepto', visible: true, required: true, ord: 30, label: 'Concepto' },
            { field: 'monto', visible: true, required: true, ord: 40, label: 'Monto' },
            { field: 'referencia', visible: true, required: false, ord: 50, label: 'Referencia' },
            { field: 'categoria', visible: true, required: false, ord: 60, label: 'Categoría' }
        ]

        const map = new Map(base.map((cfg) => [cfg.field, cfg]))
        ;(fields || []).forEach((cfg) => {
            if (cfg.visible === false) {
                map.delete(cfg.field)
                return
            }
            const prev = map.get(cfg.field) || {}
            map.set(cfg.field, { ...prev, ...cfg })
        })

        return Array.from(map.values()).sort((a, b) => (a.ord || 999) - (b.ord || 999))
    }, [fields])

    const onSubmit: React.FormEventHandler = async (e) => {
        e.preventDefault()
        try {
            for (const f of (fieldList || [])) {
                if (f.required && f.visible !== false) {
                    const val = (form as any)[f.field]
                    if (val === undefined || val === null || String(val).trim() === '') {
                        throw new Error(`El campo "${f.label || f.field}" es obligatorio`)
                    }
                }
            }
            // TODO: Implementar update cuando esté disponible
            // if (id) await updateMovimientoCaja(id, form as any)
            await createMovimientoCaja(form as any)
            success('Movimiento de caja guardado')
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const getInputType = (field: string): string => {
        if (field === 'fecha') return 'date'
        if (field === 'monto') return 'number'
        return 'text'
    }

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? 'Editar movimiento de caja' : 'Nuevo movimiento de caja'}</h3>
            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
                {loadingCfg && <div className="text-sm text-gray-500">Cargando campos…</div>}
                {fieldList.map((f) => {
                    const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
                    const type = getInputType(f.field)
                    const value = (form as any)[f.field] ?? ''

                    if (f.field === 'tipo') {
                        return (
                            <div key={f.field}>
                                <label className="block mb-1">{label}</label>
                                <select
                                    value={value}
                                    onChange={(e) => setForm({ ...form, tipo: e.target.value as 'ingreso' | 'egreso' })}
                                    className="border px-2 py-1 w-full rounded"
                                    required={!!f.required}
                                >
                                    <option value="ingreso">Ingreso</option>
                                    <option value="egreso">Egreso</option>
                                </select>
                            </div>
                        )
                    }

                    return (
                        <div key={f.field}>
                            <label className="block mb-1">{label}</label>
                            <input
                                type={type}
                                value={value}
                                onChange={(e) => setForm({ ...form, [f.field]: type === 'number' ? Number(e.target.value) : e.target.value })}
                                className="border px-2 py-1 w-full rounded"
                                required={!!f.required}
                                placeholder={f.help || ''}
                                step={type === 'number' ? '0.01' : undefined}
                            />
                        </div>
                    )
                })}
                <div className="pt-2">
                    <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
                    <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>Cancelar</button>
                </div>
            </form>
        </div>
    )
}
