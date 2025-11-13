import React from 'react'
import type { CompraLinea } from '../services'

type Props = {
  lineas: CompraLinea[]
  onChange: (lineas: CompraLinea[]) => void
}

export default function CompraLineasEditor({ lineas, onChange }: Props) {
  const addLinea = () => {
    onChange([
      ...lineas,
      { producto_id: '', cantidad: 1, precio_unitario: 0, subtotal: 0 }
    ])
  }

  const updateLinea = (idx: number, field: keyof CompraLinea, value: any) => {
    const updated = [...lineas]
    updated[idx] = { ...updated[idx], [field]: value }

    // Recalcular subtotal
    if (field === 'cantidad' || field === 'precio_unitario') {
      const cant = field === 'cantidad' ? value : updated[idx].cantidad
      const precio = field === 'precio_unitario' ? value : updated[idx].precio_unitario
      updated[idx].subtotal = cant * precio
    }

    onChange(updated)
  }

  const removeLinea = (idx: number) => {
    onChange(lineas.filter((_, i) => i !== idx))
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <label className="font-medium">Líneas de Compra</label>
        <button
          type="button"
          onClick={addLinea}
          className="bg-green-600 text-white px-3 py-1 rounded text-sm"
        >
          + Añadir Línea
        </button>
      </div>

      <div className="border rounded overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-2 py-2">Producto</th>
              <th className="text-left px-2 py-2">Cantidad</th>
              <th className="text-left px-2 py-2">Precio Unit.</th>
              <th className="text-left px-2 py-2">Subtotal</th>
              <th className="px-2 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {lineas.map((linea, idx) => (
              <tr key={idx} className="border-t">
                <td className="px-2 py-2">
                  <input
                    type="text"
                    placeholder="ID o nombre producto"
                    value={linea.producto_id}
                    onChange={(e) => updateLinea(idx, 'producto_id', e.target.value)}
                    className="border px-2 py-1 rounded w-full"
                    required
                  />
                </td>
                <td className="px-2 py-2">
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={linea.cantidad}
                    onChange={(e) => updateLinea(idx, 'cantidad', Number(e.target.value))}
                    className="border px-2 py-1 rounded w-full"
                    required
                  />
                </td>
                <td className="px-2 py-2">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={linea.precio_unitario}
                    onChange={(e) => updateLinea(idx, 'precio_unitario', Number(e.target.value))}
                    className="border px-2 py-1 rounded w-full"
                    required
                  />
                </td>
                <td className="px-2 py-2 font-medium">
                  ${linea.subtotal.toFixed(2)}
                </td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    onClick={() => removeLinea(idx)}
                    className="text-red-600 hover:underline"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
            {lineas.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2 py-4 text-center text-gray-500">
                  No hay líneas. Añade al menos una.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
