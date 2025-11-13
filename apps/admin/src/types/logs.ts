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
