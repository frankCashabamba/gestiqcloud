import { apiFetch } from '../lib/http'

export type MigrationRecord = {
  id: number
  version: string
  name: string | null
  status: string
  mode: string | null
  started_at: string | null
  completed_at: string | null
  executed_by: string | null
  execution_time_ms: number | null
  error_message: string | null
  applied_order: number | null
  created_at: string | null
}

export async function getMigrationsList(limit = 200): Promise<MigrationRecord[]> {
  return apiFetch(`/v1/migrations/history?limit=${limit}`, { method: 'GET' })
}

export async function markMigration(version: string, status: string, note?: string): Promise<{ ok: boolean }> {
  return apiFetch('/v1/migrations/mark', {
    method: 'POST',
    body: JSON.stringify({ version, status, note }),
  })
}

export async function getMigrationDetails(): Promise<{
  running: boolean
  pending: boolean
  pending_count: number
  applied_count: number
  pending_revisions: string[]
  config: { inline_enabled: boolean; mode: string; reason?: string | null }
}> {
  return apiFetch('/v1/admin/ops/migrate/status/details', { method: 'GET' })
}

export async function runMigrations(): Promise<{ ok: boolean; job_id?: string; started?: boolean; mode?: string; message?: string; pending_count?: number; applied_count?: number; runner?: string }>{
  // Backend mounts admin ops under /api/v1; Worker accepts /v1/*
  return apiFetch('/v1/admin/ops/migrate', { method: 'POST' })
}

export type MigrationConfig = {
  ok: boolean
  render_configured: boolean
  allow_inline?: boolean
  inline_enabled: boolean
  mode: string
  runner: string
  reason?: string | null
}

export type MigrationState = {
  running: boolean
  mode: string | null
  started_at: string | null
  finished_at: string | null
  ok: boolean | null
  error: string | null
  run_id?: string | null
}

export async function getMigrationStatus(): Promise<MigrationState> {
  return apiFetch('/v1/admin/ops/migrate/status', { method: 'GET' })
}

export async function getMigrationConfig(): Promise<MigrationConfig> {
  return apiFetch('/v1/admin/ops/migrate/config', { method: 'GET' })
}

export type MigrationHistoryItem = {
  id: string
  started_at: string
  finished_at: string | null
  mode: string
  ok: boolean | null
  error: string | null
  job_id: string | null
  pending_count: number | null
  revisions: any
  triggered_by: string | null
}

export async function getMigrationHistory(limit = 20): Promise<{ ok: boolean; items: MigrationHistoryItem[] }>{
  return apiFetch(`/v1/admin/ops/migrate/history?limit=${encodeURIComponent(String(limit))}`, { method: 'GET' })
}

export async function refreshMigrations(): Promise<{ ok: boolean; updated: boolean; status: string }>{
  return apiFetch('/v1/admin/ops/migrate/refresh', { method: 'POST' })
}
