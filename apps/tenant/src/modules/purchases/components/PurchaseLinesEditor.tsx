import React from 'react'
import { useTranslation } from 'react-i18next'
import type { PurchaseLine } from '../services'

type Props = {
  lines: PurchaseLine[]
  onChange: (lines: PurchaseLine[]) => void
}

export default function PurchaseLinesEditor({ lines, onChange }: Props) {
  const { t } = useTranslation(['purchases', 'common'])
  const addLine = () => {
    onChange([
      ...lines,
      { product_id: '', quantity: 1, unit_price: 0, subtotal: 0 }
    ])
  }

  const updateLine = (idx: number, field: keyof PurchaseLine, value: any) => {
    const updated = [...lines]
    updated[idx] = { ...updated[idx], [field]: value }

    // Recalcular subtotal
    if (field === 'quantity' || field === 'unit_price') {
      const qty = field === 'quantity' ? value : updated[idx].quantity
      const price = field === 'unit_price' ? value : updated[idx].unit_price
      updated[idx].subtotal = qty * price
    }

    onChange(updated)
  }

  const removeLine = (idx: number) => {
    onChange(lines.filter((_, i) => i !== idx))
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <label className="font-medium">{t('purchases:lines.label')}</label>
        <button
          type="button"
          onClick={addLine}
          className="bg-green-600 text-white px-3 py-1 rounded text-sm"
        >
          {t('purchases:lines.addLine')}
        </button>
      </div>

      <div className="border rounded overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-2 py-2">{t('purchases:lines.product')}</th>
              <th className="text-left px-2 py-2">{t('purchases:lines.quantity')}</th>
              <th className="text-left px-2 py-2">{t('purchases:lines.unitPrice')}</th>
              <th className="text-left px-2 py-2">{t('purchases:lines.subtotal')}</th>
              <th className="px-2 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, idx) => (
              <tr key={idx} className="border-t">
                <td className="px-2 py-2">
                  <input
                    type="text"
                    placeholder={t('purchases:lines.productPlaceholder')}
                    value={line.product_id}
                    onChange={(e) => updateLine(idx, 'product_id', e.target.value)}
                    className="border px-2 py-1 rounded w-full"
                    required
                  />
                </td>
                <td className="px-2 py-2">
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={line.quantity}
                    onChange={(e) => updateLine(idx, 'quantity', Number(e.target.value))}
                    className="border px-2 py-1 rounded w-full"
                    required
                  />
                </td>
                <td className="px-2 py-2">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={line.unit_price}
                    onChange={(e) => updateLine(idx, 'unit_price', Number(e.target.value))}
                    className="border px-2 py-1 rounded w-full"
                    required
                  />
                </td>
                <td className="px-2 py-2 font-medium">
                  ${line.subtotal.toFixed(2)}
                </td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    onClick={() => removeLine(idx)}
                    className="text-red-600 hover:underline"
                  >
                    {t('purchases:lines.remove')}
                  </button>
                </td>
              </tr>
            ))}
            {lines.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2 py-4 text-center text-gray-500">
                  {t('purchases:lines.emptyLines')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
