/**
 * types/incidents.ts
 * Tipos para incidencias y alertas
 */

export interface Incident {
  id: string
  tenant_id?: string
  user_id?: string
  tipo: string
  severidad: 'low' | 'medium' | 'high' | 'critical'
  titulo: string
  description: string
  estado: 'open' | 'in_progress' | 'resolved' | 'auto_resolved' | 'closed'
  auto_detected: boolean
  auto_resolved: boolean
  stack_trace?: string
  metadata?: Record<string, any>
  ia_analysis?: string | Record<string, any>
  ia_suggestion?: string
  assigned_to?: string
  resolution_notes?: string
  created_at: string
  updated_at: string
  resolved_at?: string
}

export interface StockAlert {
  id: string
  tenant_id: string
  product_id: string
  product_name: string
  warehouse_id: string
  warehouse_name: string
  qty_on_hand: number
  min_qty: number
  estado: 'active' | 'notified' | 'resolved'
  detected_at: string
  notified_at?: string
  resolved_at?: string
}
