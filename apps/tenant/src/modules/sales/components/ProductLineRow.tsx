import React from 'react'
import type { VentaLinea } from '../services'

interface Props {
  linea: VentaLinea
  idx: number
  onUpdate: (idx: number, field: keyof VentaLinea, value: any) => void
  onRemove: (idx: number) => void
}

export default function ProductLineRow({ linea, idx, onUpdate, onRemove }: Props) {
  const lineBase = linea.cantidad * linea.precio_unitario * (1 - (linea.descuento || 0) / 100)
  const lineTotal = lineBase + lineBase * (linea.impuesto_tasa || 0) / 100

  return (
    <div className="border rounded p-3 mb-2 bg-white flex gap-3 items-start">
      {/* Nombre */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{linea.producto_nombre || '—'}</p>
      </div>

      {/* Cantidad */}
      <div className="w-20 shrink-0">
        <label className="text-xs text-slate-500 block">Cant.</label>
        <input
          type="number" step="1" min="1"
          value={linea.cantidad}
          onChange={e => onUpdate(idx, 'cantidad', Math.max(1, parseInt(e.target.value) || 1))}
          className="gc-input text-center"
        />
      </div>

      {/* Precio */}
      <div className="w-24 shrink-0">
        <label className="text-xs text-slate-500 block">Precio</label>
        <input
          type="number" step="0.01" min="0"
          value={linea.precio_unitario}
          onChange={e => onUpdate(idx, 'precio_unitario', Number(e.target.value))}
          className="gc-input"
        />
      </div>

      {/* Total + Eliminar */}
      <div className="shrink-0 text-right">
        <p className="text-xs text-slate-500">Total</p>
        <p className="text-sm font-semibold">${lineTotal.toFixed(2)}</p>
        <button
          type="button"
          onClick={() => onRemove(idx)}
          className="text-red-500 text-xs hover:underline mt-1"
        >
          ✕ quitar
        </button>
      </div>
    </div>
  )
}
