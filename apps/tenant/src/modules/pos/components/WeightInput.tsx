/**
 * WeightInput - Input manual de peso para productos a granel
 */
import React, { useState } from 'react'

interface WeightInputProps {
    productName: string
    pricePerUnit: number // Precio por kg/unidad
    onConfirm: (weight: number) => void
    onCancel: () => void
    uom?: string // 'kg', 'g', 'lb'
}

export default function WeightInput({
    productName,
    pricePerUnit,
    onConfirm,
    onCancel,
    uom = 'kg'
}: WeightInputProps) {
    const [weight, setWeight] = useState('')
    const [error, setError] = useState('')

    const handleConfirm = () => {
        const w = parseFloat(weight)
        if (isNaN(w) || w <= 0) {
            setError('Ingrese un peso válido mayor a 0')
            return
        }
        if (w > 999) {
            setError('Peso demasiado alto')
            return
        }
        onConfirm(w)
    }

    const handleQuickWeight = (w: number) => {
        setWeight(w.toString())
        setError('')
    }

    const total = parseFloat(weight) * pricePerUnit || 0

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
                <h2 className="text-xl font-bold mb-4">⚖️ Ingresar Peso</h2>

                <div className="mb-4 p-3 bg-blue-50 rounded">
                    <p className="text-sm text-gray-600">Producto:</p>
                    <p className="font-bold">{productName}</p>
                    <p className="text-sm text-gray-600 mt-2">
                        price: €{pricePerUnit.toFixed(2)}/{uom}
                    </p>
                </div>

                <div className="mb-4">
                    <label className="block text-sm font-medium mb-2">
                        Peso ({uom})
                    </label>
                    <input
                        type="number"
                        step="0.001"
                        value={weight}
                        onChange={(e) => {
                            setWeight(e.target.value)
                            setError('')
                        }}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') handleConfirm()
                        }}
                        className="w-full px-3 py-2 border rounded text-xl text-center font-bold focus:ring-2 focus:ring-blue-500"
                        placeholder="0.000"
                        autoFocus
                    />
                    {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
                </div>

                {/* Botones rápidos */}
                <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">Accesos rápidos:</p>
                    <div className="grid grid-cols-4 gap-2">
                        {[0.25, 0.5, 1, 2].map((w) => (
                            <button
                                key={w}
                                onClick={() => handleQuickWeight(w)}
                                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm font-medium"
                            >
                                {w} {uom}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Total */}
                {total > 0 && (
                    <div className="mb-4 p-3 bg-green-50 rounded">
                        <p className="text-sm text-gray-600">Total estimado:</p>
                        <p className="text-2xl font-bold text-green-700">
                            €{total.toFixed(2)}
                        </p>
                    </div>
                )}

                <div className="flex gap-2">
                    <button
                        onClick={handleConfirm}
                        className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-blue-700"
                    >
                        Confirmar
                    </button>
                    <button
                        onClick={onCancel}
                        className="px-6 py-3 bg-gray-300 rounded-lg hover:bg-gray-400"
                    >
                        Cancel
                    </button>
                </div>

                {/* Nota integración futura */}
                <p className="text-xs text-gray-400 mt-4 text-center">
                    💡 Próximamente: Integración con balanza automática
                </p>
            </div>
        </div>
    )
}
