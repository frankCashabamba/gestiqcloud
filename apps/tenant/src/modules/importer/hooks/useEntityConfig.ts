import { useEffect, useState } from 'react'
import { getDynamicEntityConfig, type EntityType, type EntityTypeConfig } from '../config/entityTypes'
import { useAuth } from '../../../auth/AuthContext'

type Options = {
  module?: EntityType | null
}

export function useEntityConfig(options: Options) {
  const { profile } = useAuth()
  const [config, setConfig] = useState<EntityTypeConfig | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const mod = options.module
    if (!mod) return
    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const cfg = await getDynamicEntityConfig(mod, { empresa: profile?.empresa_slug })
        if (!cancelled) {
          setConfig(cfg)
          setError(null)
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || 'Error al cargar configuración')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [options.module, profile?.empresa_slug])

  return { config, loading, error }
}
