import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation(['reconciliation', 'common'])
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
      showError(t('reconciliation:import.requiredFields'))
      return
    }
    if (transactions.length === 0) {
      showError(t('reconciliation:import.addTransaction'))
      return
    }

    setLoading(true)
    try {
      await importStatement({
        bank_name: bankName,
        account_number: accountNumber,
        statement_date: statementDate,
        transactions: transactions.map(tx => ({
          transaction_date: tx.transaction_date,
          description: tx.description,
          reference: tx.reference,
          amount: parseFloat(tx.amount) || 0,
          transaction_type: tx.transaction_type,
        })),
      })
      success(t('reconciliation:import.success'))
      onSuccess()
    } catch {
      showError(t('reconciliation:import.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">{t('reconciliation:import.title')}</h2>
        <button type="button" onClick={onCancel} className="text-sm text-gray-500 hover:text-gray-700">
          {t('reconciliation:cancel')}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium">{t('reconciliation:bank')}</label>
          <input
            type="text"
            value={bankName}
            onChange={e => setBankName(e.target.value)}
            placeholder={t('reconciliation:import.bankPlaceholder')}
            className="mt-1 w-full border rounded px-3 py-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium">{t('reconciliation:import.accountNumber')}</label>
          <input
            type="text"
            value={accountNumber}
            onChange={e => setAccountNumber(e.target.value)}
            placeholder={t('reconciliation:import.accountPlaceholder')}
            className="mt-1 w-full border rounded px-3 py-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium">{t('reconciliation:import.statementDate')}</label>
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
          <label className="block text-sm font-medium">{t('reconciliation:import.transactions')}</label>
          <button
            type="button"
            onClick={addRow}
            className="text-sm px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            {t('reconciliation:import.addRow')}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">{t('reconciliation:date')}</th>
                <th className="px-3 py-2 text-left font-semibold">{t('reconciliation:detail.description')}</th>
                <th className="px-3 py-2 text-left font-semibold">{t('reconciliation:detail.reference')}</th>
                <th className="px-3 py-2 text-left font-semibold">{t('reconciliation:detail.amount')}</th>
                <th className="px-3 py-2 text-left font-semibold">{t('reconciliation:detail.type')}</th>
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
                      placeholder={t('reconciliation:detail.description')}
                      className="w-full border rounded px-2 py-1"
                      required
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      value={row.reference}
                      onChange={e => updateRow(idx, 'reference', e.target.value)}
                      placeholder={t('reconciliation:import.refPlaceholder')}
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
                      <option value="credit">{t('reconciliation:detail.credit')}</option>
                      <option value="debit">{t('reconciliation:detail.debit')}</option>
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
        {loading ? t('reconciliation:import.importing') : t('reconciliation:importStatement')}
      </button>
    </form>
  )
}
