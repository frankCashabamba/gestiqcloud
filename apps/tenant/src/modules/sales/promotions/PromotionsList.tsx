import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { BackButton } from '@ui'
import { useToast, getErrorMessage } from '../../../shared/toast'
import { usePagination, Pagination } from '../../../shared/pagination'
import { usePermission } from '../../../hooks/usePermission'
import ProtectedButton from '../../../components/ProtectedButton'
import PromotionStatusBadge from './PromotionStatusBadge'
import PromotionsForm from './PromotionsForm'
import {
  listPromotions,
  removePromotion,
  getPromotionStatus,
  type Promotion,
  type PromotionStatus,
} from './promotionsService'

type FilterTab = 'all' | 'active' | 'scheduled' | 'expired' | 'inactive'

function formatValue(p: Promotion): string {
  if (p.type === 'percentage') return `${p.value}%`
  if (p.type === 'fixed') return `-$${Number(p.value).toFixed(2)}`
  return 'Buy X Get Y'
}

function formatDateRange(validFrom?: string, validTo?: string): string {
  if (!validFrom && !validTo) return '—'
  const f = validFrom ?? '...'
  const t = validTo ?? '...'
  return `${f} → ${t}`
}

export default function PromotionsList() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const can = usePermission()
  const { success, error: toastError } = useToast()

  const [items, setItems] = useState<Promotion[]>([])
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<FilterTab>('all')
  const [q, setQ] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Promotion | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Promotion | null>(null)

  function load() {
    setLoading(true)
    listPromotions()
      .then(setItems)
      .catch(e => toastError(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = useMemo(() => {
    return items.filter(p => {
      const status = getPromotionStatus(p)
      if (tab !== 'all' && status !== (tab as PromotionStatus)) return false
      if (q && !(
        p.name.toLowerCase().includes(q.toLowerCase()) ||
        (p.promo_code || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.description || '').toLowerCase().includes(q.toLowerCase())
      )) return false
      return true
    })
  }, [items, tab, q])

  const { page, setPage, totalPages, view } = usePagination(filtered, 20)

  function handleNew() {
    setEditing(null)
    setFormOpen(true)
  }

  function handleEdit(p: Promotion) {
    setEditing(p)
    setFormOpen(true)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    const target = deleteTarget
    setDeleteTarget(null)
    try {
      await removePromotion(target.id)
      setItems(prev => prev.filter(p => p.id !== target.id))
      success(t('promotions.deleted'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  function handleSaved(saved: Promotion) {
    setItems(prev => {
      const idx = prev.findIndex(p => p.id === saved.id)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = saved
        return next
      }
      return [saved, ...prev]
    })
    setFormOpen(false)
  }

  const TABS: { key: FilterTab; label: string }[] = [
    { key: 'all', label: t('promotions.filterAll') },
    { key: 'active', label: t('promotions.status.active') },
    { key: 'scheduled', label: t('promotions.status.scheduled') },
    { key: 'expired', label: t('promotions.status.expired') },
    { key: 'inactive', label: t('promotions.status.inactive') },
  ]

  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}>
        <BackButton onClick={() => nav(-1)} />
      </div>

      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="font-semibold text-lg">{t('promotions.title')}</h2>
          <p className="text-sm text-slate-500">{t('promotions.subtitle')}</p>
        </div>
        {can('sales:create') && (
          <ProtectedButton permission="sales:create" variant="primary" onClick={handleNew}>
            {t('promotions.new')}
          </ProtectedButton>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b overflow-x-auto">
        {TABS.map(tb => (
          <button
            key={tb.key}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              tab === tb.key
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
            onClick={() => { setTab(tb.key); setPage(1) }}
          >
            {tb.label}
            {tb.key !== 'all' && (
              <span className="ml-1.5 text-xs text-slate-400">
                ({items.filter(p => getPromotionStatus(p) === tb.key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Búsqueda */}
      <div className="mb-3">
        <input
          placeholder={t('promotions.searchPlaceholder')}
          value={q}
          onChange={e => { setQ(e.target.value); setPage(1) }}
          className="border px-3 py-1.5 rounded text-sm w-full max-w-sm"
        />
      </div>

      {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}

      {/* Tabla */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b bg-gray-50">
              <th className="py-2 px-3">{t('promotions.colName')}</th>
              <th className="py-2 px-3">{t('promotions.colType')}</th>
              <th className="py-2 px-3">{t('promotions.colValue')}</th>
              <th className="py-2 px-3">{t('promotions.colValidity')}</th>
              <th className="py-2 px-3">{t('promotions.colUsage')}</th>
              <th className="py-2 px-3">{t('common.status')}</th>
              <th className="py-2 px-3">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {view.map(p => {
              const status = getPromotionStatus(p)
              return (
                <tr key={p.id} className="border-b hover:bg-gray-50">
                  <td className="py-2.5 px-3">
                    <div className="font-medium text-slate-900">{p.name}</div>
                    {p.promo_code && (
                      <span className="inline-block mt-0.5 text-xs font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {p.promo_code}
                      </span>
                    )}
                    {p.description && (
                      <div className="text-xs text-slate-400 mt-0.5 truncate max-w-xs">{p.description}</div>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    {t(`promotions.type.${p.type}`)}
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-slate-800">
                    {formatValue(p)}
                    {p.min_purchase > 0 && (
                      <div className="text-xs text-slate-400 font-normal">
                        {t('promotions.minPurchase', { amount: p.min_purchase.toFixed(2) })}
                      </div>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-slate-600 text-xs">
                    {formatDateRange(p.valid_from, p.valid_to)}
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">
                    {p.usage_limit
                      ? `${p.usage_count} / ${p.usage_limit}`
                      : p.usage_count > 0 ? String(p.usage_count) : '—'}
                  </td>
                  <td className="py-2.5 px-3">
                    <PromotionStatusBadge status={status} />
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex gap-3 items-center">
                      {can('sales:update') && (
                        <button
                          onClick={() => handleEdit(p)}
                          className="text-blue-600 hover:underline text-xs"
                        >
                          {t('common.edit')}
                        </button>
                      )}
                      {can('sales:delete') && (
                        <button
                          onClick={() => setDeleteTarget(p)}
                          className="text-red-500 hover:underline text-xs"
                        >
                          {t('common.delete')}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
            {!loading && view.length === 0 && (
              <tr>
                <td colSpan={7} className="py-10 text-center text-slate-400">
                  {q || tab !== 'all' ? t('promotions.emptyFiltered') : t('promotions.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />

      {/* Modal formulario */}
      {formOpen && (
        <PromotionsForm
          initial={editing}
          onSaved={handleSaved}
          onClose={() => setFormOpen(false)}
        />
      )}

      {/* Modal confirmación eliminar */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start gap-3 mb-5">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <div>
                <h3 className="font-bold text-gray-900">{t('promotions.deleteConfirmTitle')}</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  {t('promotions.deleteConfirmBody', { name: deleteTarget.name })}
                </p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                className="px-4 py-2 border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                onClick={() => setDeleteTarget(null)}
              >
                {t('common.cancel')}
              </button>
              <button
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-colors"
                onClick={() => void handleDelete()}
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
