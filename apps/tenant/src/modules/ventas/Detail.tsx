import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getVenta, type Venta } from './services'

export default function VentaDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [venta, setVenta] = useState<Venta | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getVenta(id).then((v)=> setVenta(v)).finally(()=> setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: 16 }}>Cargando…</div>
  if (!venta) return <div style={{ padding: 16 }}>No encontrada</div>

  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <button className="mb-3 underline" onClick={()=> nav('..')}>← Volver</button>
      <h2 className="text-xl font-semibold mb-2">Detalle de venta</h2>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><strong>ID:</strong> {venta.id}</div>
        <div><strong>Fecha:</strong> {venta.fecha}</div>
        <div><strong>Cliente:</strong> {venta.cliente_id ?? '-'}</div>
        <div><strong>Total:</strong> $ {venta.total.toFixed(2)}</div>
        <div><strong>Estado:</strong> {venta.estado ?? '-'}</div>
      </div>
      <div className="mt-4 text-sm text-gray-600">Más detalles de líneas e impuestos pueden integrarse aquí si están disponibles en el backend.</div>
    </div>
  )
}

