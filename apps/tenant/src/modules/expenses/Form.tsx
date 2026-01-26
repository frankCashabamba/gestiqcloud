import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createGasto, getGasto, updateGasto, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanySector } from '../../contexts/CompanyConfigContext'
import { useSectorPlaceholders, getFieldPlaceholder } from '../../hooks/useSectorPlaceholders'

type FormT = Omit<Gasto, 'id' | 'created_at' | 'updated_at'>

const CATEGORIAS = [
  'Rent',
  'Services',
  'Personnel',
  'Marketing',
  'Supplies',
  'Transport',
  'Taxes',
  'Maintenance',
  'Other'
]

const SUBCATEGORIAS: Record<string, string[]> = {
  'Services': ['Electricity', 'Water', 'Internet', 'Phone', 'Gas'],
  'Personnel': ['Salaries', 'Social Security', 'Bonuses', 'Meals'],
  'Marketing': ['Advertising', 'Social Media', 'Events', 'Promotional Materials'],
  'Supplies': ['Office', 'Cleaning', 'Packaging', 'Materials'],
  'Transport': ['Fuel', 'Vehicle Maintenance', 'Tolls', 'Parking']
}

export default function GastoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const sector = useCompanySector()
  const { placeholders } = useSectorPlaceholders(sector?.plantilla, 'expenses')

  const [form, setForm] = useState<FormT>({
    date: new Date().toISOString().slice(0, 10),
    category: '',
    subcategory: '',
    concept: '',
    amount: 0,
    payment_method: 'cash',
    supplier_id: '',
    supplier_name: '',
    status: 'pending',
    invoice_number: '',
    notes: ''
  })

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      getGasto(id)
        .then((x) => {
          setForm({
            date: x.date,
            category: x.category,
            subcategory: x.subcategory || '',
            concept: x.concept || '',
            amount: x.amount,
            payment_method: x.payment_method || 'cash',
            supplier_id: x.supplier_id || '',
            supplier_name: x.supplier_name || '',
            status: x.status || 'pending',
            invoice_number: x.invoice_number || '',
            notes: x.notes || ''
          })
        })
        .catch((e) => error(getErrorMessage(e)))
        .finally(() => setLoading(false))
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()

    try {
      if (!form.date) throw new Error('Date is required')
      if (!form.category) throw new Error('Category is required')
      if (!form.concept) throw new Error('Concept is required')
      if (form.amount <= 0) throw new Error('Amount must be greater than 0')

      setLoading(true)

      if (id) {
        await updateGasto(id, form)
      } else {
        await createGasto(form as Omit<Gasto, 'id'>)
      }

      success('Expense saved')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const subcategorias = form.category ? (SUBCATEGORIAS[form.category] || []) : []

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">
         {id ? 'Edit expense' : 'New expense'}
       </h3>

      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 700 }}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Date *</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label className="block mb-1 font-medium">Amount *</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Category *</label>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value, subcategory: '' })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            >
              <option value="">Select...</option>
              {CATEGORIAS.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {subcategorias.length > 0 && (
            <div>
              <label className="block mb-1 font-medium">Subcategory</label>
              <select
                value={form.subcategory || ''}
                onChange={(e) => setForm({ ...form, subcategory: e.target.value })}
                className="border px-2 py-1 w-full rounded"
                disabled={loading}
              >
                <option value="">Select...</option>
                {subcategorias.map(sub => (
                  <option key={sub} value={sub}>{sub}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="block mb-1 font-medium">Concept *</label>
          <input
            type="text"
            placeholder="Expense description"
            value={form.concept}
            onChange={(e) => setForm({ ...form, concept: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
            disabled={loading}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Payment Method *</label>
            <select
              value={form.payment_method}
              onChange={(e) => setForm({ ...form, payment_method: e.target.value as any })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            >
              <option value="cash">Cash</option>
              <option value="transfer">Transfer</option>
              <option value="card">Card</option>
              <option value="check">Check</option>
            </select>
          </div>

          <div>
            <label className="block mb-1 font-medium">Status *</label>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as any })}
              className="border px-2 py-1 w-full rounded"
              required
              disabled={loading}
            >
              <option value="pending">Pending</option>
              <option value="paid">Paid</option>
              <option value="voided">Voided</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-1 font-medium">Supplier ID</label>
            <input
              type="text"
              placeholder="Supplier ID"
              value={form.supplier_id || ''}
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block mb-1 font-medium">Supplier Name</label>
            <input
              type="text"
              placeholder="Supplier name"
              value={form.supplier_name || ''}
              onChange={(e) => setForm({ ...form, supplier_name: e.target.value })}
              className="border px-2 py-1 w-full rounded"
              disabled={loading}
            />
          </div>
        </div>

        <div>
          <label className="block mb-1 font-medium">Invoice Number</label>
           <input
             type="text"
             placeholder={getFieldPlaceholder(placeholders, 'invoice_number', 'E.g: INV-2025-001')}
             value={form.invoice_number || ''}
             onChange={(e) => setForm({ ...form, invoice_number: e.target.value })}
             className="border px-2 py-1 w-full rounded"
             disabled={loading}
           />
        </div>

        <div>
          <label className="block mb-1 font-medium">Notes</label>
          <textarea
            value={form.notes || ''}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={3}
            placeholder="Additional notes..."
            disabled={loading}
          />
        </div>

        <div className="pt-2 flex gap-3">
          <button
            type="submit"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            className="px-4 py-2 border rounded hover:bg-gray-50"
            onClick={() => nav('..')}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
