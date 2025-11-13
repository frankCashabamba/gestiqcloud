/**
 * useParserRegistry.ts
 * Hook para obtener el registry de parsers disponibles desde el backend
 * 
 * Usado en Sprint 2 para mostrar opciones de override en el Wizard
 */

import { useState, useEffect } from 'react'
import { getParserRegistry, ParserRegistry } from '../services/importsApi'

interface UseParserRegistryReturn {
  /** Registry de parsers */
  registry: ParserRegistry | null
  /** Estado de carga */
  loading: boolean
  /** Error durante la carga */
  error: Error | null
  /** Actualizar registry manualmente */
  refresh: () => Promise<void>
  /** Lista de IDs de parsers (conveniencia) */
  parserIds: string[]
}

export function useParserRegistry(authToken?: string): UseParserRegistryReturn {
  const [registry, setRegistry] = useState<ParserRegistry | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const refresh = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getParserRegistry(authToken)
      setRegistry(data)
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error')
      setError(error)
      setRegistry(null)
    } finally {
      setLoading(false)
    }
  }

  // Cargar al montar
  useEffect(() => {
    refresh()
  }, [authToken])

  const parserIds = registry ? Object.keys(registry.parsers) : []

  return {
    registry,
    loading,
    error,
    refresh,
    parserIds,
  }
}

export default useParserRegistry
