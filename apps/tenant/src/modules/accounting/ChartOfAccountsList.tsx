import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listCuentas, removeCuenta, seedCuentas, type PlanCuenta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function PlanCuentasList() {
    const { t } = useTranslation()
    const nav = useNavigate()
    const [items, setItems] = useState<PlanCuenta[]>([])
    const [loading, setLoading] = useState(false)
    const [seeding, setSeeding] = useState(false)
    const [filter, setFilter] = useState('')
    const { success, error } = useToast()
    const [seedPending, setSeedPending] = useState<boolean | null>(null)
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; nombre: string } | null>(null)

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

    const onSeed = (force = false) => setSeedPending(force)

    const doSeed = async () => {
        const force = seedPending === true
        setSeedPending(null)
        try {
            setSeeding(true)
            const res = await seedCuentas(force)
            success(res.message)
            load()
        } catch (e: any) {
            error(getErrorMessage(e))
        } finally {
            setSeeding(false)
        }
    }

    const doDelete = async () => {
        if (!deleteTarget) return
        try {
            await removeCuenta(deleteTarget.id)
            success(t('accounting.chartOfAccounts.deleted'))
            load()
        } catch (e: any) {
            error(getErrorMessage(e))
        } finally {
            setDeleteTarget(null)
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
                <h3 className="text-2xl font-semibold">{t('accounting.chartOfAccounts.title')}</h3>
                <div className="flex gap-2">
                    {items.length === 0 ? (
                        <button
                            onClick={() => onSeed(false)}
                            disabled={seeding}
                            className="bg-green-600 text-white px-3 py-2 rounded font-medium"
                        >
                            {seeding ? 'Generando...' : '⚡ Generar plan de cuentas'}
                        </button>
                    ) : (
                        <button
                            onClick={() => onSeed(true)}
                            disabled={seeding}
                            className="bg-gray-100 text-gray-700 border px-3 py-2 rounded text-sm"
                            title="Añade las cuentas estándar que falten sin borrar las existentes"
                        >
                            {seeding ? '...' : '+ Completar con estándar'}
                        </button>
                    )}
                    <button
                        onClick={() => nav('../plan-cuentas/nuevo')}
                        className="bg-blue-600 text-white px-3 py-2 rounded"
                    >
                        {t('accounting.chartOfAccounts.new')}
                    </button>
                </div>
            </div>

            <div className="mb-4">
                <input
                    type="search"
                    placeholder={t('accounting.chartOfAccounts.searchPlaceholder')}
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="border px-3 py-2 rounded w-full max-w-md"
                />
            </div>

            {loading && <div>{t('common.loading')}</div>}

            <div className="overflow-x-auto">
                <table className="min-w-full border">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="border px-3 py-2 text-left">{t('accounting.chartOfAccounts.columns.code')}</th>
                            <th className="border px-3 py-2 text-left">{t('common.name')}</th>
                            <th className="border px-3 py-2 text-left">{t('common.type')}</th>
                            <th className="border px-3 py-2 text-center">{t('accounting.chartOfAccounts.columns.level')}</th>
                            <th className="border px-3 py-2 text-center">{t('common.active')}</th>
                            <th className="border px-3 py-2 text-center">{t('common.actions')}</th>
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
                                        {t(`accounting.accountTypes.${c.tipo}`, { defaultValue: c.tipo })}
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
                                        {t('common.edit')}
                                    </button>
                                    <button
                                        onClick={() => setDeleteTarget({ id: c.id, nombre: c.nombre })}
                                        className="text-red-600 hover:underline"
                                    >
                                        {t('common.delete')}
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {!loading && filtered.length === 0 && (
                            <tr>
                                <td colSpan={6} className="border px-3 py-8 text-center text-gray-500">
                                    {items.length === 0 ? (
                                        <div>
                                            <p className="mb-3">No hay cuentas.</p>
                                            <button
                                                onClick={() => onSeed(false)}
                                                disabled={seeding}
                                                className="bg-green-600 text-white px-4 py-2 rounded font-medium mr-2"
                                            >
                                                {seeding ? 'Generando...' : '⚡ Generar plan de cuentas estándar'}
                                            </button>
                                            <button onClick={() => nav('../plan-cuentas/nuevo')} className="text-blue-600 hover:underline text-sm">
                                                {t('accounting.chartOfAccounts.createFirst')}
                                            </button>
                                        </div>
                                    ) : (
                                        <span>No hay resultados para esa búsqueda.</span>
                                    )}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        {seedPending !== null && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
                    <h3 className="font-semibold text-lg mb-2">{seedPending ? '+ Completar con estándar' : '⚡ Generar plan de cuentas'}</h3>
                    <p className="text-sm text-slate-600 mb-4">
                        {seedPending
                            ? 'Se añadirán las cuentas estándar que aún no existan.'
                            : 'Se generará un plan de cuentas estándar.'}
                    </p>
                    <div className="flex justify-end gap-2">
                        <button onClick={() => setSeedPending(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common.cancel')}</button>
                        <button onClick={doSeed} className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 text-sm">Continuar</button>
                    </div>
                </div>
            </div>
        )}

        {deleteTarget && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
                    <h3 className="font-semibold text-lg mb-2">{t('common.delete')}</h3>
                    <p className="text-sm text-slate-600 mb-4">{t('accounting.chartOfAccounts.deleteConfirm', { name: deleteTarget.nombre })}</p>
                    <div className="flex justify-end gap-2">
                        <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common.cancel')}</button>
                        <button onClick={doDelete} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">{t('common.delete')}</button>
                    </div>
                </div>
            </div>
        )}
        </div>
    )
}
