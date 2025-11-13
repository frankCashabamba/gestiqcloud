import { useEffect, useState } from 'react'
import type { ReciboNomina } from '../types/nomina'

export function useNomina() {
  const [recibos, setRecibos] = useState<ReciboNomina[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: Implementar getRecibos cuando esté disponible
    // getRecibos().then((data) => { setRecibos(data); setLoading(false) })
    setLoading(false)
  }, [])

  return { recibos, loading }
}
