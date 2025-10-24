/**
 * Payment Link Generator - Generar enlaces de pago
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createPaymentLink } from './services'

export default function PaymentLinkGenerator() {
  const navigate = useNavigate()
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [generatedLink, setGeneratedLink] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!amount || parseFloat(amount) <= 0) {
      alert('Ingrese un monto válido')
      return
    }
    
    try {
      setLoading(true)
      
      const result = await createPaymentLink({
        amount: parseFloat(amount),
        currency,
        description,
      })
      
      setGeneratedLink(result.url)
    } catch (err: any) {
      alert(err.message || 'Error al generar link')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (generatedLink) {
      navigator.clipboard.writeText(generatedLink)
      alert('Link copiado al portapapeles')
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Generar Link de Pago</h1>
        <p className="mt-1 text-sm text-slate-500">
          Crea enlaces de pago para enviar por email o WhatsApp
        </p>
      </div>

      <form onSubmit={handleGenerate} className="rounded-xl border bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Monto</label>
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Moneda</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
            >
              <option value="EUR">EUR (€)</option>
              <option value="USD">USD ($)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium">Descripción</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
              rows={3}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
          >
            {loading ? 'Generando...' : 'Generar Link'}
          </button>
        </div>
      </form>

      {generatedLink && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-6">
          <h3 className="font-semibold text-green-900">✅ Link Generado</h3>
          <div className="mt-3 flex items-center gap-2">
            <input
              type="text"
              value={generatedLink}
              readOnly
              className="flex-1 rounded-lg border px-3 py-2 text-sm font-mono"
            />
            <button
              onClick={handleCopy}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
            >
              Copiar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
