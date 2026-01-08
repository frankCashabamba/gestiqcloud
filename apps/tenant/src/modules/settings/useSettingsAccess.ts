import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { getLimites } from './services'

export type SettingsSection =
  | 'general'
  | 'branding'
  | 'fiscal'
  | 'horarios'
  | 'notificaciones'
  | 'operativo'
  | 'modulos'
  | 'avanzado'

type AccessMap = Partial<Record<SettingsSection, boolean>>

const ROLE_ACCESS: Record<string, AccessMap> = {
  owner: {
    general: true,
    branding: true,
    fiscal: true,
    horarios: true,
    notificaciones: true,
    operativo: true,
  },
  admin: {
    general: true,
    branding: true,
    horarios: true,
    notificaciones: true,
    operativo: true,
  },
  manager: {
    general: true,
    horarios: true,
    notificaciones: true,
  },
  supervisor: {
    horarios: true,
    notificaciones: true,
  },
  staff: {
    horarios: true,
    notificaciones: true,
  },
  default: {
    general: true,
    horarios: true,
    notificaciones: true,
  },
}

const ADMIN_ONLY_SECTIONS = new Set<SettingsSection>(['modulos', 'avanzado'])

function normalizeRole(value?: string) {
  return (value || '').trim().toLowerCase()
}

function resolveUserLimit(raw: any): number | null {
  const candidate =
    raw?.user_limit ??
    raw?.usuariosMax ??
    raw?.max_users ??
    raw?.maxUsers
  const value = Number(candidate)
  return Number.isFinite(value) ? value : null
}

export function useSettingsAccess() {
  const { profile } = useAuth()
  const [limitsLoading, setLimitsLoading] = useState(true)
  const [userLimit, setUserLimit] = useState<number | null>(null)

  const isCompanyAdmin = Boolean(
    (profile as any)?.is_company_admin ||
    (profile as any)?.is_company_admi ||
    profile?.es_admin_empresa
  )

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const data = await getLimites()
        if (!cancelled) {
          setUserLimit(resolveUserLimit(data))
        }
      } catch {
        if (!cancelled) setUserLimit(null)
      } finally {
        if (!cancelled) setLimitsLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const primaryRole = useMemo(() => {
    const roles = (profile as any)?.roles as string[] | undefined
    if (!roles || roles.length === 0) return 'default'
    return normalizeRole(roles[0]) || 'default'
  }, [profile])

  const multiUserPlan = userLimit == null ? true : userLimit > 1

  const canAccessSection = (section: SettingsSection) => {
    if (isCompanyAdmin) return true
    if (!multiUserPlan) return false
    if (ADMIN_ONLY_SECTIONS.has(section)) return false
    const roleAccess = ROLE_ACCESS[primaryRole] || ROLE_ACCESS.default
    return Boolean(roleAccess[section])
  }

  return {
    isCompanyAdmin,
    primaryRole,
    userLimit,
    multiUserPlan,
    limitsLoading,
    canAccessSection,
  }
}
