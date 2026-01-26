import React, { useEffect, useState } from 'react'
import { fetchBodegas } from '../services/inventory'
import { ensureArray } from '../../../shared/utils/array'
import type { Bodega } from '../types/producto'

export default function BodegasList() {
  const [items, setItems] = useState<Bodega[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetchBodegas().then((d)=> {
      setItems(ensureArray<Bodega>(d))
      setLoading(false)
    })
  }, [])
  if (loading) return <div className="p-4 text-sm text-gray-500">Loading…</div>

  return (
    <div className="p-4">
      <h2 className="font-semibold text-lg mb-4">Warehouses</h2>
      <ul className="list-disc pl-6">
        {(Array.isArray(items) ? items : []).map(b => <li key={b.id}><strong>{b.name}</strong> {b.ubicacion ? `( ${b.ubicacion} )` : ''}</li>)}
      </ul>
    </div>
  )
}
