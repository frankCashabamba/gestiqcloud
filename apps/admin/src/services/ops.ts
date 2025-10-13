import { apiFetch } from '../lib/http'

export async function runMigrations(): Promise<{ ok: boolean; job_id?: string }>{
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
}

export async function getMigrationStatus(): Promise<MigrationState> {
  return apiFetch('/v1/admin/ops/migrate/status', { method: 'GET' })
}
