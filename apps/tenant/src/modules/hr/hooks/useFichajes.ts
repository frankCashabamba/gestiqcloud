import { useCallback, useEffect, useState } from 'react'
import type { Fichaje } from '../types/fichaje'
import { getFichajes } from '../services/fichajes'

export function useFichajes() {
  const [fichajes, setFichajes] = useState<Fichaje[]>([])
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getFichajes()
      setFichajes(data)
    } catch {
      setFichajes([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { fichajes, loading, reload }
}
