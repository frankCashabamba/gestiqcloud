import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ImportadorLayout from '../components/ImportadorLayout'
import { listBatches, type ImportBatch } from '../services/importsApi'
import { useAuth } from '../../../auth/AuthContext'

export default function BatchesList() {
  const { token, profile } = useAuth() as { token: string | null; profile: any }
  const { t } = useTranslation()
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<ImportBatch[]>([])

  const statusOptions = useMemo(
    () => [
      { value: '', label: t('importerBatches.statusOptions.all') },
      { value: 'READY', label: t('importerBatches.statusOptions.ready') },
      { value: 'VALIDATED', label: t('importerBatches.statusOptions.validated') },
      { value: 'PROMOTED', label: t('importerBatches.statusOptions.promoted') },
      { value: 'EMPTY', label: t('importerBatches.statusOptions.empty') },
      { value: 'ERROR', label: t('importerBatches.statusOptions.error') },
    ],
    [t]
  )

  const statusLabels: Record<string, string> = useMemo(
    () => ({
      EMPTY: t('importerBatches.statusLabels.empty'),
    }),
    [t]
  )

  async function load() {
    if (!token) {
      setError(t('importerBatches.errors.noSession'))
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await listBatches(status || undefined, profile?.tenant_id)
      setRows(data)
    } catch (err: any) {
      setError(err?.message || t('importerBatches.errors.fetchFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const empty = !loading && rows.length === 0
  const total = useMemo(() => rows.length, [rows])

  return (
    <ImportadorLayout
      title={t('importerBatches.title')}
      description={t('importerBatches.description')}
      actions={
        <button
          type="button"
          className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
          onClick={load}
          disabled={loading}
        >
          {loading ? t('importerBatches.actions.refreshing') : t('importerBatches.actions.refresh')}
        </button>
      }
    >
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {statusOptions.map((opt) => {
              const isActive = status === opt.value
              return (
                <button
                  key={opt.value || 'all'}
                  type="button"
                  onClick={() => setStatus(opt.value)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    isActive
                      ? 'bg-blue-600 text-white shadow'
                      : 'border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                  }`}
                >
                  {opt.label}
                </button>
              )
            })}
          </div>
          <span className="text-xs text-neutral-500">{t('importerBatches.totalBatches', { count: total })}</span>
        </div>

        {error && (
          <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
            {error}
          </div>
        )}

        <div className="overflow-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-4 py-3">{t('importerBatches.table.batch')}</th>
                <th className="px-4 py-3">{t('importerBatches.table.origin')}</th>
                <th className="px-4 py-3">{t('importerBatches.table.status')}</th>
                <th className="px-4 py-3">{t('importerBatches.table.created')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((batch) => (
                <tr key={batch.id} className="border-t border-neutral-100 hover:bg-neutral-50">
                  <td className="px-4 py-3 font-mono text-xs text-blue-700">
                    <Link to={`./${batch.id}`} className="hover:underline">
                      {batch.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-neutral-700">
                    <div className="font-medium text-neutral-900">{batch.source_type}</div>
                    <div className="text-xs text-neutral-500">{batch.origin || t('importerBatches.withoutOrigin')}</div>
                  </td>
                  <td className="px-4 py-3 text-neutral-700">{statusLabels[batch.status] || batch.status}</td>
                  <td className="px-4 py-3 text-neutral-700">{new Date(batch.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && <div className="px-4 py-6 text-center text-sm text-neutral-500">{t('importerBatches.loading')}</div>}
          {empty && <div className="px-4 py-6 text-center text-sm text-neutral-500">{t('importerBatches.empty')}</div>}
        </div>
      </section>
    </ImportadorLayout>
  )
}
