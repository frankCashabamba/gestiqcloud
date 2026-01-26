import React, { useRef } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import ImportadorLayout from './components/ImportadorLayout'
import { useImportQueue } from './context/ImportQueueContext'

const statusConfig: Record<string, { label: string; tone: string }> = {
  pending: { label: 'Pending', tone: 'bg-neutral-100 text-neutral-700' },
  processing: { label: 'Processing...', tone: 'bg-blue-50 text-blue-700' },
  ready: { label: 'Ready', tone: 'bg-emerald-50 text-emerald-700' },
  saving: { label: 'Saving...', tone: 'bg-blue-50 text-blue-700' },
  saved: { label: 'Saved', tone: 'bg-emerald-100 text-emerald-800' },
  error: { label: 'Error', tone: 'bg-rose-100 text-rose-800' },
}

export default function ImportadorExcelWithQueue() {
  const { queue, addToQueue, removeFromQueue, clearQueue } = useImportQueue()
  const { empresa } = useParams()
  const location = useLocation()
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Extraer empresa de la URL
  const empresaFromUrl = React.useMemo(() => {
    if (empresa) return empresa
    const match = location.pathname.match(/^\/([^/]+)\//)
    return match ? match[1] : ''
  }, [empresa, location.pathname])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addToQueue(e.target.files)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addToQueue(e.dataTransfer.files)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  return (
    <ImportadorLayout
      title="Universal Importer"
      description="Upload Excel, CSV, PDF or image files to process them automatically"
    >
      <div className="space-y-6">
        {/* Zona de carga */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className="rounded-lg border-2 border-dashed border-neutral-200 bg-neutral-50 p-8 text-center transition hover:border-blue-400 hover:bg-blue-50"
        >
          <div className="mx-auto max-w-md space-y-4">
            <div className="flex justify-center">
              <svg
                className="h-12 w-12 text-neutral-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-medium text-neutral-900">
                Drag files here or click to select
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                Excel (.xlsx, .xls), CSV, PDF or images
              </p>
            </div>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".xlsx,.xls,.csv,.pdf,image/*"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-flex cursor-pointer items-center rounded-md border border-blue-600 bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
              >
                Select files
              </label>
            </div>
          </div>
        </div>

        {/* Cola de procesamiento */}
        {queue.length > 0 && (
          <div className="rounded-lg border border-neutral-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-neutral-900">
                Files in queue ({queue.length})
              </h3>
              <button
                onClick={clearQueue}
                className="text-xs text-neutral-500 hover:text-neutral-700"
              >
                Clear completed
              </button>
            </div>

            <div className="divide-y divide-neutral-100">
              {queue.map((item) => {
                const config = statusConfig[item.status] || statusConfig.pending
                return (
                  <div key={item.id} className="px-4 py-3">
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-sm font-medium text-neutral-900">
                            {item.name}
                          </p>
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${config.tone}`}
                          >
                            {config.label}
                          </span>
                        </div>
                        {item.info && (
                          <p className="mt-1 text-xs text-neutral-500">{item.info}</p>
                        )}
                        {item.error && (
                          <p className="mt-1 text-xs text-rose-600">{item.error}</p>
                        )}
                        {item.batchId && (
                          <div className="mt-2">
                            <Link
                              to={`/${empresaFromUrl}/importador/preview?batch_id=${item.batchId}`}
                              className="text-xs font-medium text-blue-600 hover:text-blue-700"
                            >
                              View results →
                            </Link>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {item.status === 'processing' && (
                          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
                        )}
                        {item.status === 'saved' && (
                          <svg
                            className="h-5 w-5 text-emerald-600"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        )}
                        {item.status === 'error' && (
                          <button
                            onClick={() => removeFromQueue(item.id)}
                            className="text-xs text-neutral-400 hover:text-neutral-600"
                          >
                            <svg
                              className="h-5 w-5"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M6 18L18 6M6 6l12 12"
                              />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Enlaces rápidos */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Link
            to={`/${empresaFromUrl}/importador/batches`}
            className="block rounded-lg border border-neutral-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md"
          >
            <h4 className="font-medium text-neutral-900">Pending imports</h4>
            <p className="mt-1 text-sm text-neutral-500">
              Review and continue with created batches
            </p>
          </Link>

          <Link
            to={`/${empresaFromUrl}/importador/preview`}
            className="block rounded-lg border border-neutral-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md"
          >
            <h4 className="font-medium text-neutral-900">Preview</h4>
            <p className="mt-1 text-sm text-neutral-500">
              Open the detail screen by passing ?batch_id=...
            </p>
          </Link>
        </div>
      </div>
    </ImportadorLayout>
  )
}
