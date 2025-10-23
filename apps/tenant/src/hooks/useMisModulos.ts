import { useEffect, useMemo, useState } from 'react'
import { listMisModulos, listModulosSeleccionablesPorEmpresa, type Modulo } from '../services/modulos'
import { useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

function toSlug(m: Modulo): string {
  if (m.slug) return m.slug.toLowerCase()
  if (m.url) {
    const u = m.url.trim()
    let s = u.startsWith('/') ? u.slice(1) : u
    // Quita prefijo /mod si existe (legacy)
    if (s.startsWith('mod/')) s = s.slice(4)
    const parts = s.split('/').filter(p => p)
    const seg = parts[parts.length - 1] || s
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
        if (token) {
          // Siempre usar endpoint autenticado cuando hay token
          try {
            mods = await listMisModulos(token)
          } catch (e: any) {
            console.error('Error loading modules:', e)
            setError(e?.message || 'Error loading modules')
          }
        } else {
          mods = []
        }
        // Asegura siempre un array aunque el backend devuelva null/objeto
        const list = Array.isArray(mods)
          ? mods
          : (mods && Array.isArray((mods as any).items))
          ? (mods as any).items
          : []
        if (!cancelled) setModules(list)
      } catch (e: any) {
        console.error('Unexpected error in useMisModulos:', e)
        if (!cancelled) setError(e?.message || 'Error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [token])

  const allowedSlugs = useMemo(() => {
    const list = Array.isArray(modules) ? modules : []
    return new Set(list.filter((m) => m.activo !== false).map(toSlug))
  }, [modules])

  return { modules, allowedSlugs, loading, error }
}
