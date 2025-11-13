// src/hooks/useAdminStats.ts
import { useState, useEffect } from 'react'
import { getAdminStats, AdminStats } from '../services/stats'

export function useAdminStats() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadStats() {
    try {
      setLoading(true)
      setError(null)
      const data = await getAdminStats()
      setStats(data)
    } catch (e) {
      console.error('Error cargando estadísticas:', e)
      setError('Error al cargar estadísticas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  return {
    stats,
    loading,
    error,
    refresh: loadStats
  }
}
