import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createCuenta, getCuenta, updateCuenta, listCuentas, type PlanCuenta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useSectorPlaceholder } from '../../hooks/useSectorPlaceholders'
import { useCompany } from '../../contexts/CompanyContext'

export default function PlanCuentasForm() {
    const { t } = useTranslation()
    const { id } = useParams()
    const nav = useNavigate()
    const { sector } = useCompany()
    const [form, setForm] = useState<Partial<PlanCuenta>>({
        codigo: '',
        nombre: '',
        tipo: 'ACTIVO',
        nivel: 1,
        activo: true,
    })
    const { success, error } = useToast()
    const [cuentasPadre, setCuentasPadre] = useState<PlanCuenta[]>([])

    const { placeholder: codigoPlaceholder } = useSectorPlaceholder(
        sector?.plantilla || null,
        'codigos_cuenta',
        'accounting_plan'
    )

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
            if (!form.codigo || !form.nombre) throw new Error(t('accounting.chartOfAccounts.form.errors.codeNameRequired'))
            if (id) await updateCuenta(id, form)
            else await createCuenta(form)
            success(t('accounting.chartOfAccounts.saved'))
            nav('..')
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    return (
        <div className="p-4">
            <h3 className="text-xl font-semibold mb-3">{id ? t('accounting.chartOfAccounts.form.editTitle') : t('accounting.chartOfAccounts.form.newTitle')}</h3>
            <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
                <div>
                    <label className="block mb-1">{t('accounting.chartOfAccounts.form.code')}</label>
                    <input
                        type="text"
                        value={form.codigo || ''}
                        onChange={(e) => setForm({ ...form, codigo: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        required
                        placeholder={codigoPlaceholder || t('accounting.chartOfAccounts.form.codePlaceholder')}
                    />
                </div>

                <div>
                    <label className="block mb-1">{t('common.name')}</label>
                    <input
                        type="text"
                        value={form.nombre || ''}
                        onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                        className="border px-2 py-1 w-full rounded"
                        required
                    />
                </div>

                <div>
                    <label className="block mb-1">{t('common.type')}</label>
                    <select
                        value={form.tipo || 'ACTIVO'}
                        onChange={(e) => setForm({ ...form, tipo: e.target.value as any })}
                        className="border px-2 py-1 w-full rounded"
                        required
                    >
                        <option value="ACTIVO">{t('accounting.accountTypes.ACTIVO')}</option>
                        <option value="PASIVO">{t('accounting.accountTypes.PASIVO')}</option>
                        <option value="PATRIMONIO">{t('accounting.accountTypes.PATRIMONIO')}</option>
                        <option value="INGRESO">{t('accounting.accountTypes.INGRESO')}</option>
                        <option value="GASTO">{t('accounting.accountTypes.GASTO')}</option>
                    </select>
                </div>

                <div>
                    <label className="block mb-1">{t('accounting.chartOfAccounts.form.level')}</label>
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
                    <label className="block mb-1">{t('accounting.chartOfAccounts.form.parentOptional')}</label>
                    <select
                        value={form.padre_id || ''}
                        onChange={(e) => setForm({ ...form, padre_id: e.target.value || null })}
                        className="border px-2 py-1 w-full rounded"
                    >
                        <option value="">{t('accounting.chartOfAccounts.form.noParent')}</option>
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
                        <span>{t('common.active')}</span>
                    </label>
                </div>

                <div className="pt-2 flex gap-2">
                    <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">
                        {t('common.save')}
                    </button>
                    <button type="button" className="px-3 py-2 border rounded" onClick={() => nav('..')}>
                        {t('common.cancel')}
                    </button>
                </div>
            </form>
        </div>
    )
}
