/**
 * StoreCreditsModal - Gestión de vales de descuento
 */

import React, { useState, useEffect } from 'react'
import { listStoreCredits, getStoreCreditByCode, redeemStoreCredit } from '../services'
import type { StoreCredit } from '../../../types/pos'

interface StoreCreditsModalProps {
  onSelect: (credit: StoreCredit) => void
  onClose: () => void
}

export default function StoreCreditsModal({ onSelect, onClose }: StoreCreditsModalProps) {
  const [credits, setCredits] = useState<StoreCredit[]>([])
  const [loading, setLoading] = useState(false)
  const [searchCode, setSearchCode] = useState('')
  const [foundCredit, setFoundCredit] = useState<StoreCredit | null>(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    loadCredits()
  }, [])

  const loadCredits = async () => {
    try {
      setLoading(true)
      const data = await listStoreCredits()
      setCredits(data)
    } catch (error) {
      console.error('Error loading credits:', error)
    } finally {
      setLoading(false)
    }
  }

  const searchByCode = async () => {
    if (!searchCode.trim()) return

    try {
      setSearching(true)
      const credit = await getStoreCreditByCode(searchCode.toUpperCase())
      setFoundCredit(credit)
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Vale no encontrado')
      setFoundCredit(null)
    } finally {
      setSearching(false)
    }
  }

  const handleSelect = (credit: StoreCredit) => {
    if (credit.status !== 'active' || credit.amount_remaining <= 0) {
      alert('Este vale no es válido')
      return
    }
    onSelect(credit)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Vales de Descuento</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Buscador por código */}
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold mb-2">Buscar por Código</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={searchCode}
              onChange={(e) => setSearchCode(e.target.value.toUpperCase())}
              placeholder="Ingrese código del vale"
              className="flex-1 px-3 py-2 border rounded uppercase"
              onKeyPress={(e) => e.key === 'Enter' && searchByCode()}
            />
            <button
              onClick={searchByCode}
              disabled={searching || !searchCode.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {searching ? 'Buscando...' : 'Buscar'}
            </button>
          </div>

          {foundCredit && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
              <p><strong>Vale encontrado:</strong> {foundCredit.code}</p>
              <p>Cliente: {foundCredit.customer_id || 'Sin asignar'}</p>
              <p>Monto restante: €{foundCredit.amount_remaining.toFixed(2)}</p>
              <p>Expira: {foundCredit.expires_at ? new Date(foundCredit.expires_at).toLocaleDateString() : 'Sin expiración'}</p>
              <button
                onClick={() => handleSelect(foundCredit)}
                className="mt-2 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
              >
                Usar este vale
              </button>
            </div>
          )}
        </div>

        {/* Lista de vales */}
        <div>
          <h3 className="font-semibold mb-3">Vales Disponibles</h3>

          {loading ? (
            <div className="text-center py-4">Cargando vales...</div>
          ) : credits.length === 0 ? (
            <div className="text-center py-4 text-gray-500">No hay vales disponibles</div>
          ) : (
            <div className="grid gap-3 max-h-96 overflow-y-auto">
              {credits.map((credit) => (
                <div
                  key={credit.id}
                  className={`p-4 border rounded-lg ${
                    credit.status === 'active' && credit.amount_remaining > 0
                      ? 'border-green-200 bg-green-50 cursor-pointer hover:bg-green-100'
                      : 'border-gray-200 bg-gray-50 opacity-60'
                  }`}
                  onClick={() => handleSelect(credit)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-mono text-lg font-bold">{credit.code}</p>
                      <p className="text-sm text-gray-600">
                        Cliente: {credit.customer_id || 'Sin asignar'}
                      </p>
                      <p className="text-sm text-gray-600">
                        Estado: <span className={`font-medium ${
                          credit.status === 'active' ? 'text-green-600' :
                          credit.status === 'redeemed' ? 'text-blue-600' :
                          'text-red-600'
                        }`}>
                          {credit.status}
                        </span>
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="text-xl font-bold text-green-600">
                        €{credit.amount_remaining.toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-500">
                        de €{credit.amount_initial.toFixed(2)}
                      </p>
                      {credit.expires_at && (
                        <p className="text-xs text-orange-600">
                          Expira: {new Date(credit.expires_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>

                  {credit.status === 'active' && credit.amount_remaining > 0 && (
                    <div className="mt-2 text-xs text-green-600">
                      ✓ Click para usar
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
