import { useEffect, useMemo, useState } from 'react'
import { listMisModulos, listModulosSeleccionablesPorEmpresa, type Modulo } from '../services/modulos'
import { useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

function toSlug(m: Modulo): string {
  if (m.slug) return m.slug.toLowerCase()
  if (m.url) {
    const u = m.url.trim()
    const s = u.startsWith('/') ? u.slice(1) : u
    const seg = s.split('/')[0] || s
    return seg.toLowerCase()
  }
  // fallback: normaliza nombre
  return (m.nombre || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '')
}

export function useMisModulos() {
  const [modules, setModules] = useState<Modulo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { token } = useAuth() as { token: string | null }
  const { empresa } = useParams()

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        let mods: Modulo[] = []
        if (empresa) {
          // Público por empresa (módulos contratados por la empresa)
          try {
            mods = await listModulosSeleccionablesPorEmpresa(empresa)
          } catch (e) {
            // Fallback a endpoint autenticado si falla o no existe público
            if (token) {
              try { mods = await listMisModulos(token) } catch {}
            }
          }
          // Si el endpoint público respondió pero viene vacío, intenta también el autenticado
          if ((mods?.length ?? 0) === 0 && token) {
            try {
              const authMods = await listMisModulos(token)
              if (authMods?.length) mods = authMods
            } catch {}
          }
        } else if (token) {
          // Autenticado por usuario (módulos asignados al usuario)
          mods = await listMisModulos(token)
        } else {
          mods = []
        }
        if (!cancelled) setModules(mods || [])
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [token, empresa])

  const allowedSlugs = useMemo(() => new Set(modules.filter(m => m.activo !== false).map(toSlug)), [modules])

  return { modules, allowedSlugs, loading, error }
}
