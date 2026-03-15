import { useCallback, useEffect, useState } from 'react'
import type { Fichaje } from '../types/fichaje'
import { getFichajes } from '../services/fichajes'

export function useFichajes(params?: { empleadoId?: string; fromDate?: string; toDate?: string }) {
  const [fichajes, setFichajes] = useState<Fichaje[]>([])
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getFichajes(params)
      setFichajes(data)
    } catch {
      setFichajes([])
    } finally {
      setLoading(false)
    }
  }, [params?.empleadoId, params?.fromDate, params?.toDate])

  useEffect(() => {
    void reload()
  }, [reload])

  return { fichajes, loading, reload }
}
