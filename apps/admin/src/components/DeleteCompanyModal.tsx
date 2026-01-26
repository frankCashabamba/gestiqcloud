import React, { useState } from 'react'

type DeleteResult = {
  ok: boolean
  tenant_id: string
  name: string
  registros_eliminados: {
    usuarios: number
    productos: number
    facturas: number
    clientes: number
    modulos: number
    roles: number
  }
}

type Props = {
  empresa: {
    id: string
    name: string
  }
  onClose: () => void
  onConfirm: (tenantId: string) => Promise<DeleteResult>
}

export const DeleteEmpresaModal: React.FC<Props> = ({ empresa, onClose, onConfirm }) => {
  const [loading, setLoading] = useState(false)
  const [confirmText, setConfirmText] = useState('')
  const [result, setResult] = useState<DeleteResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (confirmText !== empresa.name) {
      setError('Name does not match')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const res = await onConfirm(empresa.id)
      setResult(res)
    } catch (e: any) {
      setError(e.message || 'Error deleting company')
      setLoading(false)
    }
  }

  if (result) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
        <div
          className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
          onClick={e => e.stopPropagation()}
        >
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <svg className="text-green-600" style={{ width: 40, height: 40 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h2 className="mb-2 text-2xl font-semibold text-slate-900">
              Company deleted
            </h2>

            <p className="mb-4 text-slate-600">
              <strong>{result.name}</strong> has been completely deleted from the system.
            </p>

            <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4 text-left">
              <h3 className="mb-2 font-semibold text-blue-900">Deleted records:</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-blue-800">
                <li><strong>{result.registros_eliminados?.usuarios || 0}</strong> users</li>
                <li><strong>{result.registros_eliminados?.productos || 0}</strong> products</li>
                <li><strong>{result.registros_eliminados?.facturas || 0}</strong> invoices</li>
                <li><strong>{result.registros_eliminados?.clientes || 0}</strong> clients</li>
                <li><strong>{result.registros_eliminados?.modulos || 0}</strong> modules</li>
                <li><strong>{result.registros_eliminados?.roles || 0}</strong> roles</li>
              </ul>
            </div>

            <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              All data will be saved in <strong>audit_log</strong> for complete traceability.
            </div>

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
        className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <svg className="text-red-600" style={{ width: 24, height: 24 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>

          <div className="flex-1">
            <h2 className="mb-1 text-xl font-semibold text-slate-900">
              Delete company
            </h2>
            <p className="text-sm text-slate-600">
              This action is <strong className="text-red-600">IRREVERSIBLE</strong> and will delete all associated data.
            </p>
          </div>
        </div>

        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4">
          <h3 className="mb-2 font-semibold text-red-900">Will be deleted:</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-red-800">
            <li>All company users</li>
            <li>Products and stock</li>
            <li>Invoices and sales</li>
            <li>Clients and suppliers</li>
            <li>Configurations and roles</li>
            <li>ALL history and data</li>
          </ul>
        </div>

        <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-800">
          Data will be saved in <strong>audit_log</strong> for auditing, but cannot be recovered for normal use.
        </div>

        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-slate-700">
            To confirm, type the company name:
          </label>
          <div className="mb-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800">
            {empresa.name}
          </div>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => {
              setConfirmText(e.target.value)
              setError(null)
            }}
            placeholder="Type the exact name here"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            autoFocus
          />
          {error && (
            <p className="mt-1 text-xs text-red-600">{error}</p>
          )}
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
            onClick={handleDelete}
            disabled={loading || confirmText !== empresa.name}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Deleting...' : 'Delete company'}
          </button>
        </div>
      </div>
    </div>
  )
}
