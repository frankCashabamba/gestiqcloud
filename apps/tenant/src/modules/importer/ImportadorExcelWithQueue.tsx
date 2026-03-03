import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast } from '../../shared/toast'
import ImportadorLayout from './components/ImportadorLayout'
import { useAuth } from '../../auth/AuthContext'

type UploadResult = {
  batch_id: string
  items: number
  doc_type: string
  error?: string
}

export default function ImportadorExcelWithQueue() {
  const { t } = useTranslation(['importer', 'common'])
  const { token } = useAuth() as { token: string | null }
  const { success, error } = useToast()
  const [isUploading, setUploading] = useState(false)
  const [lastResult, setLastResult] = useState<UploadResult | null>(null)

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    try {
      const file = files[0]
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/v1/imports/v2/upload', {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || `HTTP ${res.status}`)
      }
      const data = (await res.json()) as UploadResult
      setLastResult(data)
      success(
        t('importer:uploadSuccess', {
          file: file.name,
          items: data.items,
          docType: data.doc_type,
        })
      )
    } catch (e: any) {
      error(e?.message || 'Error al subir')
      setLastResult({ batch_id: '', items: 0, doc_type: '', error: e?.message })
    } finally {
      setUploading(false)
    }
  }

  return (
    <ImportadorLayout
      title={t('importer:title')}
      description={t('importer:description')}
    >
      <div className="space-y-6">
        <div className="rounded-lg border-2 border-dashed border-neutral-200 bg-neutral-50 p-8 text-center">
          <h3 className="text-lg font-medium text-neutral-900 mb-2">
            {t('importer:dragFilesHere')}
          </h3>
          <p className="text-sm text-neutral-500 mb-4">
            {t('importer:acceptedFormats')}
          </p>
          <label className="inline-flex cursor-pointer items-center rounded-md border border-blue-600 bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700">
            {isUploading ? t('common:loading') : t('importer:selectFiles')}
            <input
              type="file"
              multiple={false}
              accept=".xlsx,.xls,.csv,.xml,.pdf,image/*"
              className="hidden"
              onChange={(e) => handleUpload(e.target.files)}
              disabled={isUploading}
            />
          </label>
        </div>

        {lastResult && (
          <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
            <h4 className="font-semibold text-neutral-900 mb-1">
              Último resultado
            </h4>
            {lastResult.error ? (
              <p className="text-rose-600 text-sm">{lastResult.error}</p>
            ) : (
              <ul className="text-sm text-neutral-700 space-y-1">
                <li>Batch: {lastResult.batch_id}</li>
                <li>Items: {lastResult.items}</li>
                <li>Doc type: {lastResult.doc_type}</li>
              </ul>
            )}
          </div>
        )}
      </div>
    </ImportadorLayout>
  )
}
