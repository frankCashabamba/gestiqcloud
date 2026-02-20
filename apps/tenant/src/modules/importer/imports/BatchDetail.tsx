import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ImportadorLayout from '../components/ImportadorLayout'
import {
  getBatch,
  listItems,
  patchItem,
  validateBatch,
  downloadErrorsCsv,
  uploadBatchPhotos,
  uploadItemPhotos,
  type ImportItem,
  type ImportAttachment,
} from '../services/importsApi'

type FilterState = {
  status: string
  q: string
}

const statusTone: Record<string, string> = {
  OK: 'bg-emerald-50 text-emerald-700',
  READY: 'bg-blue-50 text-blue-700',
  VALIDATED: 'bg-blue-50 text-blue-700',
  EMPTY: 'bg-neutral-100 text-neutral-600',
  ERROR_VALIDATION: 'bg-amber-50 text-amber-600',
  ERROR_PROMOTION: 'bg-amber-50 text-amber-600',
  PROMOTED: 'bg-blue-100 text-blue-800',
  PENDING: 'bg-neutral-100 text-neutral-600',
}

export default function BatchDetail() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [batch, setBatch] = useState<any>(null)
  const [items, setItems] = useState<ImportItem[]>([])
  const [filters, setFilters] = useState<FilterState>({ status: '', q: '' })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [messageTone, setMessageTone] = useState<'info' | 'success' | 'error'>('info')
  const [savingItemId, setSavingItemId] = useState<string | null>(null)
  const [batchAttachments, setBatchAttachments] = useState<ImportAttachment[]>([])
  const [itemAttachments, setItemAttachments] = useState<Record<string, ImportAttachment[]>>({})
  const [uploadingBatch, setUploadingBatch] = useState(false)
  const [uploadingItemId, setUploadingItemId] = useState<string | null>(null)
  const statusOptions = useMemo(
    () => [
      { value: '', label: t('importerBatchDetail.statusOptions.all') },
      { value: 'OK', label: 'OK' },
      { value: 'ERROR_VALIDATION', label: t('importerBatchDetail.statusOptions.validationError') },
      { value: 'ERROR_PROMOTION', label: t('importerBatchDetail.statusOptions.promotionError') },
      { value: 'PROMOTED', label: t('importerBatchDetail.statusOptions.promoted') },
    ],
    [t]
  )

  async function load() {
    if (!id) return
    setLoading(true)
    setMessage(null)
    try {
      const [batchData, itemsData] = await Promise.all([
        getBatch(id),
        listItems(id, {
          status: filters.status || undefined,
          q: filters.q || undefined,
        }),
      ])
      setBatch(batchData)
      setItems(itemsData)
      setBatchAttachments(batchData.attachments ?? [])
      const attachmentsMap: Record<string, ImportAttachment[]> = {}
      itemsData.forEach((itemData) => {
        attachmentsMap[itemData.id] = itemData.attachments ?? []
      })
      setItemAttachments(attachmentsMap)
    } catch (err: any) {
      setMessage(err?.message || t('importerBatchDetail.errors.loadBatchFailed'))
      setMessageTone('error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, filters.status])

  async function onValidate() {
    await validateBatch(id)
    await load()
    setMessage(t('importerBatchDetail.messages.batchRevalidated'))
    setMessageTone('success')
  }

  function onOpenPreview() {
    if (!id) return
    navigate(`../preview?batch_id=${encodeURIComponent(id)}`)
  }

  async function onDownloadCsv() {
    const csv = await downloadErrorsCsv(id)
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `errors_${id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function onInlineEdit(item: ImportItem, field: string, value: string) {
    setSavingItemId(item.id)
    try {
      await patchItem(id, item.id, field, value)
      await load()
      setMessage(t('importerBatchDetail.messages.itemUpdated'))
      setMessageTone('success')
    } finally {
      setSavingItemId(null)
    }
  }

  const onBatchPhotosChange: React.ChangeEventHandler<HTMLInputElement> = async (event) => {
    if (!id) {
      event.target.value = ''
      return
    }
    const files = event.target.files ? Array.from(event.target.files) : []
    if (!files.length) {
      event.target.value = ''
      return
    }
    setUploadingBatch(true)
    try {
      const { attachments } = await uploadBatchPhotos(id, files)
      setBatchAttachments((prev) => [...prev, ...attachments])
      setMessage(t('importerBatchDetail.messages.batchPhotosUploaded'))
      setMessageTone('success')
    } catch (err: any) {
      setMessage(err?.message || t('importerBatchDetail.errors.batchPhotosUploadFailed'))
      setMessageTone('error')
    } finally {
      setUploadingBatch(false)
      event.target.value = ''
    }
  }

  const onItemPhotosChange = async (itemId: string, fileList: FileList | null) => {
    if (!id || !fileList || !fileList.length) return
    const files = Array.from(fileList)
    setUploadingItemId(itemId)
    try {
      const { attachments } = await uploadItemPhotos(id, itemId, files)
      setItemAttachments((prev) => ({
        ...prev,
        [itemId]: [...(prev[itemId] || []), ...attachments],
      }))
      setMessage(t('importerBatchDetail.messages.itemPhotosUploaded'))
      setMessageTone('success')
    } catch (err: any) {
      setMessage(err?.message || t('importerBatchDetail.errors.itemPhotosUploadFailed'))
      setMessageTone('error')
    } finally {
      setUploadingItemId(null)
    }
  }

  const renderAttachment = (attachment: ImportAttachment) => (
    <a
      key={attachment.id}
      href={attachment.url}
      target="_blank"
      rel="noreferrer"
      className="group block h-16 w-16 overflow-hidden rounded border border-neutral-200 hover:border-blue-400"
    >
      {attachment.kind === 'photo' ? (
        <img src={attachment.url} alt={t('importerBatchDetail.attachments.attachmentAlt')} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-neutral-50 text-[11px] font-medium text-neutral-500">
          {t('importerBatchDetail.actions.view')}
        </div>
      )}
    </a>
  )

  const total = useMemo(() => items.length, [items])
  const activeStatus = filters.status
  const messageToneClasses: Record<'info' | 'success' | 'error', string> = {
    info: 'border-blue-200 bg-blue-50 text-blue-700',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    error: 'border-rose-200 bg-rose-50 text-rose-700',
  }

  return (
    <ImportadorLayout
      title={t('importerBatchDetail.title', { id: id.slice(0, 8) })}
      description={t('importerBatchDetail.description')}
      actions={
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
            onClick={onValidate}
            disabled={loading}
          >
            {t('importerBatchDetail.actions.revalidateBatch')}
          </button>
          <button
            type="button"
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white shadow hover:bg-blue-500"
            onClick={onOpenPreview}
            disabled={loading}
          >
            {t('importerBatchDetail.actions.openInPreview')}
          </button>
          <button
            type="button"
            className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
            onClick={onDownloadCsv}
            disabled={loading}
          >
            {t('importerBatchDetail.actions.downloadErrorsCsv')}
          </button>
        </div>
      }
    >
      <section className="space-y-4">
        {batch && (
          <div className="grid gap-4 rounded-lg border border-neutral-200 bg-white p-4 shadow-sm md:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-neutral-500">{t('importerBatchDetail.summary.origin')}</p>
              <p className="text-sm font-medium text-neutral-900">{batch.origin || t('importerBatchDetail.summary.withoutOrigin')}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-neutral-500">{t('importerBatchDetail.summary.type')}</p>
              <p className="text-sm font-medium text-neutral-900">{batch.source_type}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-neutral-500">{t('importerBatchDetail.summary.currentStatus')}</p>
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
                statusTone[batch.status] || 'bg-neutral-100 text-neutral-700'
              }`}>
                {batch.status}
              </span>
            </div>
          </div>
        )}

        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-neutral-900">{t('importerBatchDetail.attachments.batchTitle')}</p>
              <p className="text-xs text-neutral-500">{t('importerBatchDetail.attachments.batchDescription')}</p>
            </div>
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60">
              <span>{uploadingBatch ? t('importerBatchDetail.actions.uploading') : t('importerBatchDetail.actions.uploadPhotos')}</span>
              <input
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={onBatchPhotosChange}
                disabled={uploadingBatch}
              />
            </label>
          </div>
          <div className="mt-3 flex flex-wrap gap-3">
            {batchAttachments.length ?
              batchAttachments.map(renderAttachment) : (
                <span className="text-xs text-neutral-400">{t('importerBatchDetail.attachments.noneLoaded')}</span>
              )}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            {statusOptions.map((opt) => {
              const isActive = activeStatus === opt.value
              return (
                <button
                  key={opt.value || 'all'}
                  type="button"
                  onClick={() => setFilters((prev) => ({ ...prev, status: opt.value }))}
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
          <form
            className="flex items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault()
              load()
            }}
          >
            <input
              className="rounded-md border border-neutral-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
              placeholder={t('importerBatchDetail.filters.searchPlaceholder')}
              value={filters.q}
              onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))}
            />
            <button
              type="submit"
              className="rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-700"
              disabled={loading}
            >
              {t('importerBatchDetail.filters.search')}
            </button>
          </form>
        </div>

        {message && (
          <div
            className={'rounded-md border px-3 py-2 text-sm ' + messageToneClasses[messageTone]}
            role={messageTone === 'error' ? 'alert' : 'status'}
          >
            {message}
          </div>
        )}

        <div className="overflow-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">{t('importerBatchDetail.table.status')}</th>
                <th className="px-4 py-3">{t('importerBatchDetail.table.field')}</th>
                <th className="px-4 py-3">{t('importerBatchDetail.table.value')}</th>
                <th className="px-4 py-3">{t('importerBatchDetail.table.errors')}</th>
                <th className="px-4 py-3">{t('importerBatchDetail.table.attachments')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const data = item.normalized || item.raw || {}
                const keys = Object.keys(data)
                const firstKey = keys[0] || ''
                const value = firstKey ? String((data as Record<string, unknown>)[firstKey] ?? '') : ''
                const errors = item.errors || []
                const saving = savingItemId === item.id
                const attachments = itemAttachments[item.id] || item.attachments || []
                const uploadingItem = uploadingItemId === item.id

                return (
                  <tr key={item.id} className="border-t border-neutral-100 hover:bg-neutral-50">
                    <td className="px-4 py-3 text-xs text-neutral-500">{item.idx}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
                        statusTone[item.status] || 'bg-neutral-100 text-neutral-700'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <input
                        className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                        defaultValue={firstKey}
                        onBlur={(event) => {
                          const nextField = event.currentTarget.value
                          if (nextField && nextField !== firstKey) {
                            onInlineEdit(item, nextField, value)
                          }
                        }}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <input
                        className="w-full rounded-md border border-neutral-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                        defaultValue={value}
                        onBlur={(event) => onInlineEdit(item, firstKey, event.currentTarget.value)}
                      />
                      {saving && <p className="mt-1 text-[11px] text-neutral-500">{t('importerBatchDetail.actions.saving')}</p>}
                    </td>
                    <td className="px-4 py-3">
                      {errors.length === 0 ? (
                        <span className="text-xs text-neutral-400">{t('importerBatchDetail.table.noErrors')}</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {errors.map((error, idxError) => (
                            <span
                              key={idxError}
                              className="rounded-full bg-rose-50 px-2 py-1 text-[11px] font-medium text-rose-700"
                            >
                              {error.field || t('importerBatchDetail.table.fieldFallback')}: {error.msg || t('importerBatchDetail.table.reviewFallback')}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        {attachments.length ? (
                          attachments.map(renderAttachment)
                        ) : (
                          <span className="text-xs text-neutral-400">{t('importerBatchDetail.attachments.none')}</span>
                        )}
                      </div>
                      <label className="mt-2 inline-flex cursor-pointer items-center gap-2 rounded-md border border-neutral-200 px-2 py-1 text-[11px] font-medium text-neutral-600 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60">
                        <span>{uploadingItem ? t('importerBatchDetail.actions.uploading') : t('importerBatchDetail.actions.uploadPhotos')}</span>
                        <input
                          type="file"
                          accept="image/*"
                          multiple
                          className="hidden"
                          onChange={(event) => {
                            onItemPhotosChange(item.id, event.target.files)
                            event.target.value = ''
                          }}
                          disabled={uploadingItem}
                        />
                      </label>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {loading && (
            <div className="px-4 py-6 text-center text-sm text-neutral-500">{t('importerBatchDetail.loadingItems')}</div>
          )}
          {!loading && total === 0 && (
            <div className="px-4 py-6 text-center text-sm text-neutral-500">{t('importerBatchDetail.empty')}</div>
          )}
        </div>
      </section>
    </ImportadorLayout>
  )
}
