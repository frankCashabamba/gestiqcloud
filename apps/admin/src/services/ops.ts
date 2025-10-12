import { apiFetch } from '../lib/http'

export async function runMigrations(): Promise<{ ok: boolean; job_id?: string }>{
  // Backend mounts admin ops under /api/v1; Worker accepts /v1/*
  return apiFetch('/v1/admin/ops/migrate', { method: 'POST' })
}
