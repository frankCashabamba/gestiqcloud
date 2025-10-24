import { useEffect, useState } from 'react'
import type { ReciboNomina } from '../types/nomina'
import { getRecibos } from '../services/nomina'

export function useNomina() {
  const [recibos, setRecibos] = useState<ReciboNomina[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRecibos().then((data) => { setRecibos(data); setLoading(false) })
  }, [])

  return { recibos, loading }
}

