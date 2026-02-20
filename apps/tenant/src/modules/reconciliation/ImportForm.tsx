import React, { useState } from 'react'
import { useToast } from '../../shared/toast'
import { importStatement } from './services'

interface TransactionRow {
  transaction_date: string
  description: string
  reference: string
  amount: string
  transaction_type: 'credit' | 'debit'
}

const emptyRow = (): TransactionRow => ({
  transaction_date: '',
  description: '',
  reference: '',
  amount: '',
  transaction_type: 'credit',
})

interface ImportFormProps {
  onSuccess: () => void
  onCancel: () => void
}

export default function ImportForm({ onSuccess, onCancel }: ImportFormProps) {
  const { success, error: showError } = useToast()
  const [bankName, setBankName] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [statementDate, setStatementDate] = useState('')
  const [transactions, setTransactions] = useState<TransactionRow[]>([emptyRow()])
  const [loading, setLoading] = useState(false)

  const addRow = () => setTransactions(prev => [...prev, emptyRow()])

  const removeRow = (index: number) => {
    setTransactions(prev => prev.filter((_, i) => i !== index))
  }

  const updateRow = (index: number, field: keyof TransactionRow, value: string) => {
    setTransactions(prev =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!bankName || !accountNumber || !statementDate) {
      showError('Completa todos los campos del extracto')
      return
    }
    if (transactions.length === 0) {
      showError('Agrega al menos una transacción')
      return
    }

    setLoading(true)
    try {
      await importStatement({
        bank_name: bankName,
        account_number: accountNumber,
        statement_date: statementDate,
        transactions: transactions.map(t => ({
          transaction_date: t.transaction_date,
          description: t.description,
          reference: t.reference,
          amount: parseFloat(t.amount) || 0,
          transaction_type: t.transaction_type,
        })),
      })
      success('Extracto importado correctamente')
      onSuccess()
    } catch {
      showError('Error al importar el extracto')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Importar Extracto Bancario</h2>
        <button type="button" onClick={onCancel} className="text-sm text-gray-500 hover:text-gray-700">
          Cancelar
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium">Banco</label>
          <input
            type="text"
            value={bankName}
            onChange={e => setBankName(e.target.value)}
            placeholder="ej: BCP, BBVA"
            className="mt-1 w-full border rounded px-3 py-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Nº Cuenta</label>
          <input
            type="text"
            value={accountNumber}
            onChange={e => setAccountNumber(e.target.value)}
            placeholder="ej: 123-456-789"
            className="mt-1 w-full border rounded px-3 py-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Fecha del Extracto</label>
          <input
            type="date"
            value={statementDate}
            onChange={e => setStatementDate(e.target.value)}
            className="mt-1 w-full border rounded px-3 py-2"
            required
          />
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium">Transacciones</label>
          <button
            type="button"
            onClick={addRow}
            className="text-sm px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            + Agregar fila
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">Fecha</th>
                <th className="px-3 py-2 text-left font-semibold">Descripción</th>
                <th className="px-3 py-2 text-left font-semibold">Referencia</th>
                <th className="px-3 py-2 text-left font-semibold">Monto</th>
                <th className="px-3 py-2 text-left font-semibold">Tipo</th>
                <th className="px-3 py-2 text-right font-semibold"></th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((row, idx) => (
                <tr key={idx} className="border-b">
                  <td className="px-3 py-2">
                    <input
                      type="date"
                      value={row.transaction_date}
                      onChange={e => updateRow(idx, 'transaction_date', e.target.value)}
                      className="w-full border rounded px-2 py-1"
                      required
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={row.description}
                      onChange={e => updateRow(idx, 'description', e.target.value)}
                      placeholder="Descripción"
                      className="w-full border rounded px-2 py-1"
                      required
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={row.reference}
                      onChange={e => updateRow(idx, 'reference', e.target.value)}
                      placeholder="Ref."
                      className="w-full border rounded px-2 py-1"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      step="0.01"
                      value={row.amount}
                      onChange={e => updateRow(idx, 'amount', e.target.value)}
                      placeholder="0.00"
                      className="w-full border rounded px-2 py-1"
                      required
                    />
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={row.transaction_type}
                      onChange={e => updateRow(idx, 'transaction_type', e.target.value)}
                      className="w-full border rounded px-2 py-1"
                    >
                      <option value="credit">Crédito</option>
                      <option value="debit">Débito</option>
                    </select>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {transactions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRow(idx)}
                        className="text-red-600 hover:bg-red-50 rounded px-2 py-1"
                      >
                        ✕
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Importando...' : 'Importar Extracto'}
      </button>
    </form>
  )
}
