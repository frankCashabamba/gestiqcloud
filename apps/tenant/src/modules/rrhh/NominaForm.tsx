import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createNomina, getNomina, updateNomina, type Nomina } from './services/nomina'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type FieldCfg = { field: string; visible?: boolean; required?: boolean; ord?: number | null; label?: string | null; help?: string | null }

export default function NominaForm() {
    const { id, empresa } = useParams()
    const nav = useNavigate()
    const [form, setForm] = useState<Partial<Omit<Nomina, 'id'>>>({
        salario_base: 0,
        complementos: 0,
        horas_extra: 0,
        otros_devengos: 0,
        seg_social: 0,
        irpf: 0,
        otras_deducciones: 0,
        status: 'draft'
    })
    const { success, error } = useToast()
    const [fields, setFields] = useState<FieldCfg[] | null>(null)
    const [loadingCfg, setLoadingCfg] = useState(false)

    useEffect(() => {
        if (!id) return
        getNomina(id).then((x) => setForm({ ...x }))
    }, [id])

    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                setLoadingCfg(true)
                const q = new URLSearchParams({ module: 'nominas', ...(empresa ? { empresa } : {}) }).toString()
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
            { field: 'numero', visible: true, required: false, ord: 10, label: 'Número' },
            { field: 'empleado_id', visible: true, required: true, ord: 20, label: 'Empleado ID' },
            { field: 'periodo_mes', visible: true, required: true, ord: 30, label: 'Mes' },
            { field: 'periodo_ano', visible: true, required: true, ord: 40, label: 'Año' },
            { field: 'tipo', visible: true, required: false, ord: 50, label: 'Type' },
            { field: 'salario_base', visible: true, required: true, ord: 60, label: 'Salario Base' },
            { field: 'complementos', visible: true, required: false, ord: 70, label: 'Complementos' },
            { field: 'horas_extra', visible: true, required: false, ord: 80, label: 'Horas Extra' },
            { field: 'otros_devengos', visible: true, required: false, ord: 90, label: 'Otros Devengos' },
            { field: 'seg_social', visible: true, required: false, ord: 100, label: 'Seg. Social' },
            { field: 'irpf', visible: true, required: false, ord: 110, label: 'IRPF' },
            { field: 'otras_deducciones', visible: true, required: false, ord: 120, label: 'Otras Deducciones' },
            { field: 'metodo_pago', visible: true, required: false, ord: 130, label: 'Método Pago' },
            { field: 'fecha_pago', visible: true, required: false, ord: 140, label: 'Fecha Pago' }
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
            if (id) await updateNomina(id, form as any)
            else await createNomina(form as any)
            success('Nómina guardada')
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const getInputType = (field: string): string => {
        if (field.includes('fecha') || field.includes('date')) return 'date'
        if (field.includes('salario') || field.includes('horas') || field.includes('devengos') || field.includes('deducciones') || field.includes('seg_social') || field.includes('irpf')) return 'number'
        if (field.includes('mes') || field.includes('ano') || field === 'periodo_mes' || field === 'periodo_ano') return 'number'
        return 'text'
    }

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? 'Editar nómina' : 'Nueva nómina'}</h3>
            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
                {loadingCfg && <div className="text-sm text-gray-500">Cargando campos…</div>}
                {fieldList.map((f) => {
                    const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
                    const type = getInputType(f.field)
                    const value = (form as any)[f.field] ?? ''
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
                                min={type === 'number' ? '0' : undefined}
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
