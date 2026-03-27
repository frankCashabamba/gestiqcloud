export interface LogEntry {
  id: string
  tenant_id: string
  tipo: string
  canal?: string
  destinatario: string
  asunto?: string
  mensaje: string
  estado: string
  extra_data?: Record<string, any>
  error_message?: string
  ref_type?: string
  ref_id?: string
  sent_at?: string
  created_at: string
}

export interface LogFilters {
  tipo: string
  estado: string
  ref_type: string
  days: number
  page: number
  limit: number
}

export interface LogStats {
  period_days: number
  total: number
  by_status: Record<string, number>
  by_tipo: Record<string, number>
}

export interface AuditEntry {
  id: string
  tenant_id: string | null
  tenant_name: string | null
  user_id: string | null
  actor_type: string
  action: 'create' | 'update' | 'delete' | string
  entity_type: string
  entity_id: string | null
  source: string
  changes: Record<string, { old: any; new: any }> | null
  ip: string | null
  created_at: string
}

export interface AuditFilters {
  tenant_id: string
  action: string
  entity_type: string
  search: string
  days: number
  page: number
  limit: number
}

export interface AuditStats {
  period_days: number
  total: number
  by_action: Record<string, number>
  by_entity_type: Record<string, number>
  by_tenant: Array<{ tenant_id: string | null; tenant_name: string | null; total: number }>
}
