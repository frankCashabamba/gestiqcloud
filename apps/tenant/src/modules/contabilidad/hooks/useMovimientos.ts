import { useEffect, useState } from 'react'
import type { Asiento } from '../types/movimiento'
import { fetchMovimientos } from '../services/contabilidad'

export function useMovimientos() {
  const [asientos, setAsientos] = useState<Asiento[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMovimientos().then((data) => { setAsientos(data); setLoading(false) })
  }, [])

  return { asientos, loading }
}
