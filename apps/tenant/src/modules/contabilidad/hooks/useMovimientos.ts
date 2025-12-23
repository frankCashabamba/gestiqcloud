import { useEffect, useState } from 'react'
import type { Asiento } from '../types/movimiento'
import { fetchMovimientos } from '../services/contabilidad'

export function useMovimientos() {
  const [asientos, setAsientos] = useState<Asiento[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMovimientos()
      .then((data) => {
        setAsientos(data)
        setError(null)
      })
      .catch((err) => {
        console.error('Error al cargar movimientos:', err)
        setAsientos([])
        setError('No se pudieron cargar los movimientos')
      })
      .finally(() => setLoading(false))
  }, [])

  return { asientos, loading, error }
}
