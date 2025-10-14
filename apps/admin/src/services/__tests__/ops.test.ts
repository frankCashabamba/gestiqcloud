import { afterEach, describe, expect, it, vi } from 'vitest'

describe('admin ops service routes', () => {
  afterEach(() => {
    vi.resetModules()
    vi.unmock('../lib/http')
    vi.clearAllMocks()
  })

  it('posts migrations to the worker-friendly endpoint', async () => {
    const apiFetch = vi.fn().mockResolvedValue({ ok: true })
    vi.doMock('../lib/http', () => ({ apiFetch }))

    const { runMigrations } = await import('../ops')

    await runMigrations()

    expect(apiFetch).toHaveBeenCalledWith('/v1/admin/ops/migrate', { method: 'POST' })
  })

  it('reads migration status via GET', async () => {
    const apiFetch = vi.fn().mockResolvedValue({ running: false })
    vi.doMock('../lib/http', () => ({ apiFetch }))

    const { getMigrationStatus } = await import('../ops')

    await getMigrationStatus()

    expect(apiFetch).toHaveBeenCalledWith('/v1/admin/ops/migrate/status', { method: 'GET' })
  })
})
