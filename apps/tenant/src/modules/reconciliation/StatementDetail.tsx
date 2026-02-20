import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useToast } from '../../shared/toast'
import {
  getStatementDetail,
  getStatementLines,
  autoMatch,
  manualMatch,
  BankStatement,
  StatementLine,
} from './services'

const statusConfig: Record<string, { label: string; bg: string; text: string }> = {
  imported: { label: 'Importado', bg: 'bg-blue-100', text: 'text-blue-800' },
  processing: { label: 'Procesando', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  reconciled: { label: 'Conciliado', bg: 'bg-green-100', text: 'text-green-800' },
  partial: { label: 'Parcial', bg: 'bg-orange-100', text: 'text-orange-800' },
}

const matchStatusConfig: Record<string, { label: string; bg: string; text: string }> = {
  matched: { label: 'Conciliado', bg: 'bg-green-100', text: 'text-green-800' },
  unmatched: { label: 'Pendiente', bg: 'bg-red-100', text: 'text-red-800' },
  partial: { label: 'Parcial', bg: 'bg-yellow-100', text: 'text-yellow-800' },
}

function formatAmount(value: number): string {
  return `$${value.toFixed(2)}`
}

export default function StatementDetail() {
  const { statementId } = useParams<{ statementId: string }>()
  const navigate = useNavigate()
  const { success, error: showError } = useToast()

  const [loading, setLoading] = useState(true)
  const [statement, setStatement] = useState<BankStatement | null>(null)
  const [lines, setLines] = useState<StatementLine[]>([])
  const [autoMatching, setAutoMatching] = useState(false)
  const [matchingLineId, setMatchingLineId] = useState<string | null>(null)
  const [invoiceId, setInvoiceId] = useState('')

  useEffect(() => {
    if (statementId) loadData()
  }, [statementId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [stmt, lns] = await Promise.all([
        getStatementDetail(statementId!),
        getStatementLines(statementId!),
      ])
      setStatement(stmt)
      setLines(lns)
    } catch {
      showError('Error al cargar el extracto')
    } finally {
      setLoading(false)
    }
  }

  const handleAutoMatch = async () => {
    setAutoMatching(true)
    try {
      const updated = await autoMatch(statementId!)
      setStatement(updated)
      const lns = await getStatementLines(statementId!)
      setLines(lns)
      success(`Auto-match completado: ${updated.matched_count} conciliadas`)
    } catch {
      showError('Error en auto-match')
    } finally {
      setAutoMatching(false)
    }
  }

  const handleManualMatch = async (lineId: string) => {
    if (!invoiceId.trim()) {
      showError('Ingresa un ID de factura')
      return
    }
    try {
      const updatedLine = await manualMatch(lineId, invoiceId.trim())
      setLines(prev => prev.map(l => (l.id === lineId ? updatedLine : l)))
      setMatchingLineId(null)
      setInvoiceId('')
      success('Línea conciliada manualmente')
    } catch {
      showError('Error al conciliar la línea')
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>
  if (!statement) return <div className="p-6 text-red-500">Extracto no encontrado</div>

  const cfg = statusConfig[statement.status] ?? statusConfig.imported

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('..')}
          className="text-sm px-3 py-1 text-gray-600 hover:bg-gray-100 rounded"
        >
          ← Volver
        </button>
        <h1 className="text-3xl font-bold">
          {statement.bank_name} — {statement.account_number}
        </h1>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <p className="text-sm text-gray-500">Fecha</p>
              <p className="font-medium">
                {new Date(statement.statement_date).toLocaleDateString('es-PE')}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Estado</p>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
                {cfg.label}
              </span>
            </div>
            <div>
              <p className="text-sm text-gray-500">Conciliadas</p>
              <p className="font-medium">
                {statement.matched_count} / {statement.total_transactions}
              </p>
            </div>
          </div>
          <button
            onClick={handleAutoMatch}
            disabled={autoMatching}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {autoMatching ? 'Procesando...' : 'Auto-Match'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold">Fecha</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">Descripción</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">Referencia</th>
              <th className="px-6 py-3 text-right text-sm font-semibold">Monto</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">Tipo</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">Estado</th>
              <th className="px-6 py-3 text-right text-sm font-semibold">Confianza</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">Factura</th>
              <th className="px-6 py-3 text-right text-sm font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-6 py-8 text-center text-gray-500">
                  No hay líneas en este extracto.
                </td>
              </tr>
            ) : (
              lines.map(line => {
                const mCfg = matchStatusConfig[line.match_status] ?? matchStatusConfig.unmatched
                return (
                  <tr key={line.id} className="border-b hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(line.transaction_date).toLocaleDateString('es-PE')}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium">{line.description}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{line.reference}</td>
                    <td className={`px-6 py-4 text-sm text-right font-medium ${
                      line.transaction_type === 'credit' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {line.transaction_type === 'credit' ? '+' : '-'}{formatAmount(Math.abs(line.amount))}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        line.transaction_type === 'credit'
                          ? 'bg-green-50 text-green-700'
                          : 'bg-red-50 text-red-700'
                      }`}>
                        {line.transaction_type === 'credit' ? 'Crédito' : 'Débito'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${mCfg.bg} ${mCfg.text}`}>
                        {mCfg.label}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-gray-600">
                      {line.match_confidence > 0 ? `${Math.round(line.match_confidence)}%` : '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {line.matched_invoice_id ?? '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {line.match_status === 'unmatched' && (
                        <>
                          {matchingLineId === line.id ? (
                            <div className="flex items-center gap-2 justify-end">
                              <input
                                type="text"
                                value={invoiceId}
                                onChange={e => setInvoiceId(e.target.value)}
                                placeholder="ID Factura"
                                className="border rounded px-2 py-1 text-sm w-32"
                                autoFocus
                              />
                              <button
                                onClick={() => handleManualMatch(line.id)}
                                className="text-sm px-2 py-1 text-green-600 hover:bg-green-50 rounded"
                              >
                                ✓
                              </button>
                              <button
                                onClick={() => { setMatchingLineId(null); setInvoiceId('') }}
                                className="text-sm px-2 py-1 text-gray-500 hover:bg-gray-100 rounded"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setMatchingLineId(line.id)}
                              className="text-sm px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
                            >
                              Conciliar
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
