import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { createProductionOrder, getProductionOrder, updateProductionOrder, type ProductionOrder } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type FieldCfg = { field: string; visible?: boolean; required?: boolean; ord?: number | null; label?: string | null; help?: string | null }

export default function OrderForm() {
    const { id, empresa } = useParams()
    const [search] = useSearchParams()
    const nav = useNavigate()
    const [form, setForm] = useState<Partial<Omit<ProductionOrder, 'id'>>>({
        qty_planned: 0,
        status: 'draft'
    })
    const { success, error } = useToast()
    const [fields, setFields] = useState<FieldCfg[] | null>(null)
    const [loadingCfg, setLoadingCfg] = useState(false)

    useEffect(() => {
        if (!id) return
        getProductionOrder(id).then((x) => setForm({ ...x }))
    }, [id])

    // Prefill from query when creating a new order
    useEffect(() => {
        if (id) return
        const recipeId = search.get('recipeId')
        const productId = search.get('productId')
        if (recipeId || productId) {
            setForm((prev) => ({ ...prev, ...(recipeId ? { recipe_id: recipeId } : {}), ...(productId ? { product_id: productId } : {} ) }))
        }
    }, [id, search])

    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                setLoadingCfg(true)
                const q = new URLSearchParams({ module: 'produccion', ...(empresa ? { empresa } : {}) }).toString()
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
            { field: 'recipe_id', visible: true, required: false, ord: 20, label: 'Receta ID' },
            { field: 'product_id', visible: true, required: true, ord: 30, label: 'Producto ID' },
            { field: 'warehouse_id', visible: true, required: false, ord: 40, label: 'Almacén ID' },
            { field: 'qty_planned', visible: true, required: true, ord: 50, label: 'Cantidad Planificada' },
            { field: 'scheduled_date', visible: true, required: false, ord: 60, label: 'Fecha Programada' },
            { field: 'batch_number', visible: true, required: false, ord: 70, label: 'Número de Lote' },
            { field: 'notes', visible: true, required: false, ord: 80, label: 'Notas' }
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
            if (id) await updateProductionOrder(id, form as any)
            else await createProductionOrder(form as any)
            success('Orden de producción guardada')
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const getInputType = (field: string): string => {
        if (field.includes('date')) return 'date'
        if (field.includes('qty') || field.includes('cantidad')) return 'number'
        if (field === 'notes' || field === 'notas') return 'textarea'
        return 'text'
    }

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? 'Editar orden de producción' : 'Nueva orden de producción'}</h3>
            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
                {loadingCfg && <div className="text-sm text-gray-500">Cargando campos…</div>}
                {fieldList.map((f) => {
                    const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
                    const type = getInputType(f.field)
                    const value = (form as any)[f.field] ?? ''
                    return (
                        <div key={f.field}>
                            <label className="block mb-1">{label}</label>
                            {type === 'textarea' ? (
                                <textarea
                                    value={value}
                                    onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
                                    className="border px-2 py-1 w-full rounded"
                                    required={!!f.required}
                                    placeholder={f.help || ''}
                                    rows={3}
                                />
                            ) : (
                                <input
                                    type={type}
                                    value={value}
                                    onChange={(e) => setForm({ ...form, [f.field]: type === 'number' ? Number(e.target.value) : e.target.value })}
                                    className="border px-2 py-1 w-full rounded"
                                    required={!!f.required}
                                    placeholder={f.help || ''}
                                    step={type === 'number' ? '0.01' : undefined}
                                />
                            )}
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
