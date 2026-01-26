import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listAsientos, removeAsiento, postAsiento, type AsientoContable } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function AsientosList() {
    const { t } = useTranslation()
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
        if (!confirm(t('accounting.journalEntries.deleteConfirm', { number: numero }))) return
        try {
            await removeAsiento(id)
            success(t('accounting.journalEntries.deleted'))
            load()
        } catch (e: any) {
            error(getErrorMessage(e))
        }
    }

    const onPost = async (id: string, numero: string) => {
        if (!confirm(t('accounting.journalEntries.postConfirm', { number: numero }))) return
        try {
            await postAsiento(id)
            success(t('accounting.journalEntries.posted'))
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
                <h3 className="text-2xl font-semibold">{t('accounting.journalEntries.title')}</h3>
                <button
                    onClick={() => nav('asientos/nuevo')}
                    className="bg-blue-600 text-white px-3 py-2 rounded"
                >
                    {t('accounting.journalEntries.new')}
                </button>
            </div>

            <div className="mb-4">
                <input
                    type="search"
                    placeholder={t('accounting.journalEntries.searchPlaceholder')}
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
                            <th className="border px-3 py-2 text-left">{t('accounting.journalEntries.columns.number')}</th>
                            <th className="border px-3 py-2 text-left">{t('common.date')}</th>
                            <th className="border px-3 py-2 text-left">{t('common.description')}</th>
                            <th className="border px-3 py-2 text-right">{t('accounting.journalEntries.columns.debit')}</th>
                            <th className="border px-3 py-2 text-right">{t('accounting.journalEntries.columns.credit')}</th>
                            <th className="border px-3 py-2 text-center">{t('common.status')}</th>
                            <th className="border px-3 py-2 text-center">{t('common.actions')}</th>
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
                                        {t(`accounting.journalEntries.status.${a.status}`, { defaultValue: a.status })}
                                    </span>
                                </td>
                                <td className="border px-3 py-2 text-center">
                                    {a.status === 'DRAFT' && (
                                        <>
                                            <button
                                                onClick={() => nav(`asientos/${a.id}/editar`)}
                                                className="text-blue-600 hover:underline mr-2"
                                            >
                                                {t('common.edit')}
                                            </button>
                                            <button
                                                onClick={() => onPost(a.id, a.numero)}
                                                className="text-green-600 hover:underline mr-2"
                                            >
                                                {t('accounting.journalEntries.actions.post')}
                                            </button>
                                            <button
                                                onClick={() => onDelete(a.id, a.numero)}
                                                className="text-red-600 hover:underline"
                                            >
                                                {t('common.delete')}
                                            </button>
                                        </>
                                    )}
                                    {a.status === 'POSTED' && (
                                        <span className="text-gray-500 text-sm">{t('accounting.journalEntries.actions.posted')}</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                        {!loading && filtered.length === 0 && (
                            <tr>
                                <td colSpan={7} className="border px-3 py-8 text-center text-gray-500">
                                    {t('accounting.journalEntries.empty')}{' '}
                                    <button onClick={() => nav('asientos/nuevo')} className="text-blue-600 hover:underline">
                                        {t('accounting.journalEntries.createFirst')}
                                    </button>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
