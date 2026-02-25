import React, { useState } from 'react'

type BulkDeleteResponse = {
  ok: boolean
  total: number
  deleted_count: number
  failed_count: number
  failed?: Array<{
    tenant_id: string
    name?: string
    detail?: string
  }>
}

type Props = {
  companyCount: number
  onClose: () => void
  onConfirm: () => Promise<BulkDeleteResponse>
}

const CONFIRM_TEXT = 'DELETE ALL'

export const DeleteAllCompaniesModal: React.FC<Props> = ({ companyCount, onClose, onConfirm }) => {
  const [confirmText, setConfirmText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BulkDeleteResponse | null>(null)

  const handleSubmit = async () => {
    if (confirmText.trim().toUpperCase() !== CONFIRM_TEXT) {
      setError('Confirmation text does not match')
      return
    }
    try {
      setLoading(true)
      setError(null)
      const res = await onConfirm()
      setResult(res)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Bulk delete failed')
      setLoading(false)
    }
  }

  if (result) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
        <div
          className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-center">
            <div
              className={`mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full ${
                result.failed_count > 0 ? 'bg-amber-100' : 'bg-green-100'
              }`}
            >
              <svg
                className={result.failed_count > 0 ? 'text-amber-600' : 'text-green-600'}
                style={{ width: 40, height: 40 }}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={result.failed_count > 0 ? 'M12 8v4m0 4h.01m-7.938 4h15.876c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L2.34 17c-.77 1.333.192 3 1.732 3z' : 'M5 13l4 4L19 7'}
                />
              </svg>
            </div>

            <h2 className="mb-2 text-2xl font-semibold text-slate-900">
              {result.failed_count > 0 ? 'Bulk deletion finished with issues' : 'All companies deleted'}
            </h2>

            <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4 text-left">
              <h3 className="mb-2 font-semibold text-blue-900">Summary</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-blue-800">
                <li><strong>{result.total || 0}</strong> companies targeted</li>
                <li><strong>{result.deleted_count || 0}</strong> companies deleted</li>
                <li><strong>{result.failed_count || 0}</strong> failed deletions</li>
              </ul>
            </div>

            {Array.isArray(result.failed) && result.failed.length > 0 && (
              <div className="mb-6 max-h-44 overflow-auto rounded-xl border border-amber-200 bg-amber-50 p-4 text-left">
                <h3 className="mb-2 font-semibold text-amber-900">Failures</h3>
                <ul className="list-disc space-y-1 pl-5 text-xs text-amber-800">
                  {result.failed.slice(0, 10).map((f, idx) => (
                    <li key={`${f.tenant_id}-${idx}`}>
                      {f.name || f.tenant_id}: {f.detail || 'Unknown error'}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              onClick={onClose}
              className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <svg className="text-red-600" style={{ width: 24, height: 24 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div className="flex-1">
            <h2 className="mb-1 text-xl font-semibold text-slate-900">Delete all companies</h2>
            <p className="text-sm text-slate-600">
              This action is <strong className="text-red-600">IRREVERSIBLE</strong> and will delete all tenant data.
            </p>
          </div>
        </div>

        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4">
          <h3 className="mb-2 font-semibold text-red-900">Impact</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-red-800">
            <li><strong>{companyCount}</strong> companies will be deleted</li>
            <li>Users, products, invoices, clients, modules and roles will be removed</li>
            <li>Audit records are preserved for traceability</li>
          </ul>
        </div>

        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-slate-700">
            Type <span className="font-mono">{CONFIRM_TEXT}</span> to confirm:
          </label>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => {
              setConfirmText(e.target.value)
              setError(null)
            }}
            placeholder={CONFIRM_TEXT}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            autoFocus
          />
          {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading || confirmText.trim().toUpperCase() !== CONFIRM_TEXT}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Deleting all...' : 'Delete all companies'}
          </button>
        </div>
      </div>
    </div>
  )
}
