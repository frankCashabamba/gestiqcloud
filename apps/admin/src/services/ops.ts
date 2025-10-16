import { apiFetch } from '../lib/http'

export async function runMigrations(): Promise<{ ok: boolean; job_id?: string; started?: boolean; mode?: string; message?: string; pending_count?: number }>{
  // Backend mounts admin ops under /api/v1; Worker accepts /v1/*
  return apiFetch('/v1/admin/ops/migrate', { method: 'POST' })
}

export type MigrationState = {
  running: boolean
  mode: 'inline' | 'inline_async' | 'render_job' | string | null
  started_at: string | null
  finished_at: string | null
  ok: boolean | null
  error: string | null
  run_id?: string | null
}

export async function getMigrationStatus(): Promise<MigrationState> {
  return apiFetch('/v1/admin/ops/migrate/status', { method: 'GET' })
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
