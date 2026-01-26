import { useEffect, useState } from 'react'
import type { Asiento } from '../types/movimiento'
import { fetchMovimientos } from '../services/contabilidad'
import i18n from '../../../i18n'

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
        console.error('Error loading transactions:', err)
        setAsientos([])
        setError(i18n.t('accounting.errors.loadTransactions'))
      })
      .finally(() => setLoading(false))
  }, [])

  return { asientos, loading, error }
}
