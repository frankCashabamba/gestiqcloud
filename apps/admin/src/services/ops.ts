import { apiFetch } from '../lib/http'

export async function runMigrations(): Promise<{ ok: boolean; job_id?: string }>{
  return apiFetch('/admin/ops/migrate', { method: 'POST' })
}

