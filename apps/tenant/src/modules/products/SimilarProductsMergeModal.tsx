import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getErrorMessage, useToast } from '../../shared/toast'
import {
  listSimilarProductDuplicates,
  mergeSimilarProducts,
  type SimilarProductCandidate,
  type SimilarProductGroup,
} from './productsApi'

type Props = {
  open: boolean
  onClose: () => void
  onMerged?: () => Promise<void> | void
}

type GroupState = {
  winnerId: string
  loserIds: string[]
  merging: boolean
}

function formatMoney(value: number): string {
  return Number(value || 0).toFixed(2)
}

export default function SimilarProductsMergeModal({ open, onClose, onMerged }: Props) {
  const { t } = useTranslation(['products', 'common'])
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [groups, setGroups] = useState<SimilarProductGroup[]>([])
  const [states, setStates] = useState<Record<string, GroupState>>({})
  const [matchMode, setMatchMode] = useState<'strict' | 'balanced' | 'wide'>('balanced')

  const threshold = useMemo(() => {
    if (matchMode === 'strict') return 0.95
    if (matchMode === 'wide') return 0.85
    return 0.9
  }, [matchMode])

  const reload = async () => {
    setLoading(true)
    try {
      const data = await listSimilarProductDuplicates(threshold, 20)
      const nextGroups = data.groups || []
      setGroups(nextGroups)
      const nextStates: Record<string, GroupState> = {}
      nextGroups.forEach((g, idx) => {
        const key = String(idx)
        const all = [g.winner, ...(g.candidates || [])]
        const winnerId = String(g.winner.id)
        nextStates[key] = {
          winnerId,
          loserIds: all.map((p) => String(p.id)).filter((id) => id !== winnerId),
          merging: false,
        }
      })
      setStates(nextStates)
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!open) return
    void reload()
  }, [open, threshold])

  const hasGroups = useMemo(() => groups.length > 0, [groups])

  const updateWinner = (key: string, winnerId: string, products: SimilarProductCandidate[]) => {
    setStates((prev) => ({
      ...prev,
      [key]: {
        ...(prev[key] || { winnerId, loserIds: [], merging: false }),
        winnerId,
        loserIds: products.map((p) => String(p.id)).filter((id) => id !== winnerId),
      },
    }))
  }

  const toggleLoser = (key: string, id: string) => {
    setStates((prev) => {
      const current = prev[key]
      if (!current) return prev
      const set = new Set(current.loserIds)
      if (set.has(id)) set.delete(id)
      else set.add(id)
      return {
        ...prev,
        [key]: { ...current, loserIds: Array.from(set) },
      }
    })
  }

  const doMerge = async (key: string) => {
    const current = states[key]
    if (!current || current.loserIds.length === 0) {
      toast.warning(t('products:mergeDuplicates.pickAtLeastOne'))
      return
    }
    setStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], merging: true },
    }))
    try {
      const res = await mergeSimilarProducts(current.winnerId, current.loserIds)
      toast.success(t('products:mergeDuplicates.mergeOk', { count: res.merged }))
      if (onMerged) await onMerged()
      await reload()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], merging: false },
      }))
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              {t('products:mergeDuplicates.title')}
            </h3>
            <p className="text-sm text-slate-600">{t('products:mergeDuplicates.subtitle')}</p>
          </div>
          <button
            type="button"
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={onClose}
          >
            {t('common.close')}
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto p-5 space-y-4">
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="mb-2 text-sm font-medium text-slate-800">
              {t('products:mergeDuplicates.matchModeLabel')}
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm">
                <input
                  type="radio"
                  checked={matchMode === 'strict'}
                  onChange={() => setMatchMode('strict')}
                />
                {t('products:mergeDuplicates.modeStrict')}
              </label>
              <label className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm">
                <input
                  type="radio"
                  checked={matchMode === 'balanced'}
                  onChange={() => setMatchMode('balanced')}
                />
                {t('products:mergeDuplicates.modeBalanced')}
              </label>
              <label className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm">
                <input
                  type="radio"
                  checked={matchMode === 'wide'}
                  onChange={() => setMatchMode('wide')}
                />
                {t('products:mergeDuplicates.modeWide')}
              </label>
            </div>
          </div>

          {loading && <div className="text-sm text-slate-600">{t('common.loading')}</div>}

          {!loading && !hasGroups && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
              {t('products:mergeDuplicates.empty')}
            </div>
          )}

          {!loading &&
            groups.map((group, idx) => {
              const key = String(idx)
              const all = [group.winner, ...(group.candidates || [])]
              const state = states[key]
              const winnerId = state?.winnerId || String(group.winner.id)
              const loserIds = state?.loserIds || []
              const merging = Boolean(state?.merging)
              return (
                <div key={key} className="rounded-lg border border-slate-200">
                  <div className="border-b border-slate-200 px-4 py-3 text-sm font-medium text-slate-800">
                    {t('products:mergeDuplicates.groupTitle', { number: idx + 1 })}
                  </div>
                  <div className="p-4 space-y-3">
                    {all.map((p) => {
                      const id = String(p.id)
                      const checkedWinner = winnerId === id
                      const checkedLoser = loserIds.includes(id)
                      return (
                        <div
                          key={id}
                          className="grid grid-cols-12 items-center gap-2 rounded-md border border-slate-200 p-2"
                        >
                          <div className="col-span-12 md:col-span-5">
                            <div className="font-medium text-slate-900">{p.name}</div>
                            <div className="text-xs text-slate-500">
                              SKU: {p.sku || '-'} | ID: {p.id}
                            </div>
                          </div>
                          <div className="col-span-6 md:col-span-2 text-xs text-slate-600">
                            {t('products:price')}: {formatMoney(p.price)}
                          </div>
                          <div className="col-span-6 md:col-span-2 text-xs text-slate-600">
                            Refs: {p.refs}
                          </div>
                          <label className="col-span-6 md:col-span-1 flex items-center gap-1 text-xs">
                            <input
                              type="radio"
                              name={`winner-${key}`}
                              checked={checkedWinner}
                              onChange={() => updateWinner(key, id, all)}
                            />
                            {t('products:mergeDuplicates.keep')}
                          </label>
                          <label className="col-span-6 md:col-span-2 flex items-center gap-1 text-xs">
                            <input
                              type="checkbox"
                              checked={checkedLoser}
                              disabled={checkedWinner}
                              onChange={() => toggleLoser(key, id)}
                            />
                            {t('products:mergeDuplicates.merge')}
                          </label>
                        </div>
                      )
                    })}

                    <div className="flex justify-end">
                      <button
                        type="button"
                        className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-60"
                        disabled={merging}
                        onClick={() => void doMerge(key)}
                      >
                        {merging
                          ? t('common.loading')
                          : t('products:mergeDuplicates.mergeNow', { count: loserIds.length })}
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
        </div>
      </div>
    </div>
  )
}
