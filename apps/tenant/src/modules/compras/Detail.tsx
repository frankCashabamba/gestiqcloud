import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getCompra, type Compra } from './services'

export default function CompraDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [compra, setCompra] = useState<Compra | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getCompra(id).then((v)=> setCompra(v)).finally(()=> setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: 16 }}>Cargando…</div>
  if (!compra) return <div style={{ padding: 16 }}>No encontrada</div>

  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <button className="mb-3 underline" onClick={()=> nav('..')}>← Volver</button>
      <h2 className="text-xl font-semibold mb-2">Detalle de compra</h2>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><strong>ID:</strong> {compra.id}</div>
        <div><strong>Fecha:</strong> {compra.fecha}</div>
        <div><strong>Proveedor:</strong> {(compra as any).proveedor_id ?? '-'}</div>
        <div><strong>Total:</strong> $ {compra.total.toFixed(2)}</div>
        <div><strong>Estado:</strong> {compra.estado ?? '-'}</div>
      </div>
      <div className="mt-4 text-sm text-gray-600">Más detalles de líneas/impuestos se pueden integrar aquí.</div>
    </div>
  )
}

