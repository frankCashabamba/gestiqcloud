import { useEffect, useState } from 'react'
import type { Fichaje } from '../types/fichaje'
import { getFichajes } from '../services/fichajes'

export function useFichajes() {
  const [fichajes, setFichajes] = useState<Fichaje[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getFichajes()
      .then((data) => {
        setFichajes(data)
      })
      .catch(() => {
        setFichajes([])
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  return { fichajes, loading }
}
