import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Container } from './Container'
import type { CompanyModule, Module } from '../modulos/types'
import { getEmpresa } from '../services/empresa'
import { listEmpresaModulos, listModulosPublicos, removeEmpresaModulo, upsertEmpresaModulo } from '../services/modulos'
import { getErrorMessage, useToast } from '../shared/toast'

function fmtDate(value?: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString()
}

function classNames(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ')
}

export function EmpresaModulos() {
  const { id } = useParams()
  const empresaId = id as string
  const { success, error } = useToast()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [empresa, setEmpresa] = useState<any>(null)

  const [catalogo, setCatalogo] = useState<Module[]>([])
  const [asignados, setAsignados] = useState<CompanyModule[]>([])

  const [search, setSearch] = useState('')
  const [active, setActive] = useState(true)
  const [expirationDate, setExpirationDate] = useState<string>('')
  const [initialTemplate, setInitialTemplate] = useState<string>('')
  const [lastPicked, setLastPicked] = useState<Module | null>(null)

  const assignedIds = useMemo(() => new Set(asignados.map((a) => String(a.module_id))), [asignados])

  const candidatos = useMemo(() => {
    const q = search.trim().toLowerCase()
    return catalogo
      .filter((m) => !assignedIds.has(String(m.id)))
      .filter((m) => {
        if (!q) return true
        const hay = `${m.name ?? ''} ${m.category ?? ''} ${m.description ?? ''}`.toLowerCase()
        return hay.includes(q)
      })
      .sort((a, b) => {
        const ca = (a.category ?? '').toLowerCase()
        const cb = (b.category ?? '').toLowerCase()
        if (ca !== cb) return ca.localeCompare(cb)
        return (a.name ?? '').localeCompare(b.name ?? '')
      })
  }, [catalogo, assignedIds, search])

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        const [empresaData, mods, empMods] = await Promise.all([
          getEmpresa(empresaId),
          listModulosPublicos(),
          listEmpresaModulos(empresaId),
        ])
        const moduloLookup = new Map(mods.map((m) => [String(m.id), m]))
        const enrichedAsignados = empMods.map((registro: any) => {
          if (registro.module?.name) return registro
          const moduloInfo = moduloLookup.get(String(registro.module_id))
          return moduloInfo ? { ...registro, module: moduloInfo } : registro
        })
        setEmpresa(empresaData)
        setCatalogo(mods)
        setAsignados(enrichedAsignados)
      } catch (e: any) {
        error(getErrorMessage(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [empresaId])

  const onAgregar = async (modulo: Module) => {
    try {
      setSaving(true)
      setLastPicked(modulo)
      const moduloId = String(modulo.id)
      await upsertEmpresaModulo(empresaId, moduloId, {
        active,
        expiration_date: expirationDate || null,
        initial_template: initialTemplate || modulo.initial_template || null,
      })

      setAsignados((prev) => {
        const exists = prev.some((x) => String(x.module_id) === String(moduloId))
        const newRow: CompanyModule = {
          id: String(Date.now()),
          tenant_id: empresaId,
          active,
          module_id: String(moduloId),
          expiration_date: expirationDate || null,
          initial_template: initialTemplate || modulo.initial_template || null,
          module: modulo ?? null,
        }
        return exists ? prev.map((x) => (String(x.module_id) === String(moduloId) ? newRow : x)) : [...prev, newRow]
      })

      setSearch('')
      setActive(true)
      setExpirationDate('')
      setInitialTemplate('')
      success('Module assigned')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const onToggleActive = async (moduloId: string, nextActive: boolean) => {
    try {
      setSaving(true)
      const current = asignados.find((x) => String(x.module_id) === String(moduloId))
      await upsertEmpresaModulo(empresaId, moduloId, {
        active: nextActive,
        expiration_date: current?.expiration_date ?? null,
        initial_template: current?.initial_template ?? null,
      })
      setAsignados((prev) => prev.map((x) => (String(x.module_id) === String(moduloId) ? { ...x, active: nextActive } : x)))
      success(nextActive ? 'Module activated' : 'Module deactivated')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const onEliminar = async (moduloId: number | string) => {
    if (!confirm('Remove module from company?')) return
    try {
      setSaving(true)
      await removeEmpresaModulo(empresaId, moduloId)
      setAsignados((prev) => prev.filter((x) => String(x.module_id) !== String(moduloId)))
      success('Module removed')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const companyName = empresa?.nombre || empresa?.name || empresa?.slug || empresaId

  return (
    <Container className="empresa-page">
      <header className="empresa-header">
        <div className="modules-header-row">
          <div>
            <h1 className="empresa-title">Company modules</h1>
            <p className="empresa-subtitle">
              Assign, configure and revoke modules for <span className="badge">{companyName}</span>
            </p>
          </div>
          <Link to="/admin/companies" className="action-pill blue">
            Back
          </Link>
        </div>
      </header>

      {loading ? (
        <div className="empresa-muted">Loading…</div>
      ) : (
        <div className="modules-layout">
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <div className="text-base font-semibold">Assign settings</div>
                <div className="muted text-sm">Click a module card to assign it.</div>
              </div>
              <span className="badge">{candidatos.length} available</span>
            </div>

            <div className="module-settings">
              <div>
                <label className="block text-sm font-medium mb-1">Search</label>
                <input
                  className="input"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by name, category…"
                />
              </div>

              <div className="module-setting-row">
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 700 }}>
                  <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
                  Active
                </label>
                <span className={classNames('badge', active ? '' : 'badge-warning')}>{active ? 'Enabled' : 'Disabled'}</span>
              </div>

              <div className="module-form-grid">
                <div>
                  <label className="block text-sm font-medium mb-1">Expiration date</label>
                  <input type="date" className="input" value={expirationDate} onChange={(e) => setExpirationDate(e.target.value)} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Initial template</label>
                  <input
                    className="input"
                    value={initialTemplate}
                    onChange={(e) => setInitialTemplate(e.target.value)}
                    placeholder={lastPicked?.initial_template || 'Defaults to module template'}
                  />
                </div>
              </div>

              {lastPicked && (
                <div className="text-sm">
                  <div className="muted">Last assigned</div>
                  <div className="flex items-center gap-2">
                    <span>{lastPicked.icon || ''}</span>
                    <span className="font-semibold">{lastPicked.name}</span>
                    {lastPicked.category ? <span className="badge">{lastPicked.category}</span> : null}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <div className="text-base font-semibold">Assigned modules</div>
                <div className="muted text-sm">Modules currently available for this company.</div>
              </div>
              <span className="badge">{asignados.length} assigned</span>
            </div>

            <div className="mt-4">
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ fontSize: 13, fontWeight: 800 }}>Available modules</div>
                <div className="muted" style={{ fontSize: 12 }}>Click to assign</div>
              </div>
              <div className="module-cards">
                {candidatos.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    disabled={saving}
                    onClick={() => onAgregar(m)}
                    className="module-card"
                    title="Click to assign"
                  >
                    <div className="module-card__top">
                      <div style={{ minWidth: 0 }}>
                        <div className="module-card__title">
                          <span className="module-card__icon">{(m.icon || '').trim()}</span>
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.name}</span>
                        </div>
                        <div className="module-card__meta">
                          {m.category ? <span className="badge">{m.category}</span> : <span className="badge">General</span>}
                          <span className="module-card__cta">Assign</span>
                        </div>
                      </div>
                    </div>
                    {m.description ? <div className="module-card__desc">{m.description}</div> : null}
                  </button>
                ))}
                {candidatos.length === 0 && (
                  <div className="empresa-muted">
                    No modules available to assign.
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Module</th>
                    <th>Status</th>
                    <th>Activated</th>
                    <th>Expires</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {asignados.map((a) => {
                    const name = a.module?.name || a.module_id
                    const icon = a.module?.icon || ''
                    return (
                      <tr key={a.module_id}>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                              <span>{icon}</span>
                              <span style={{ fontWeight: 700 }}>{name}</span>
                              {a.module?.category ? <span className="badge">{a.module.category}</span> : null}
                            </div>
                            <div className="muted id">{String(a.module_id)}</div>
                          </div>
                        </td>
                        <td>
                          <span className={classNames('badge', !a.active && 'badge-warning')}>{a.active ? 'Active' : 'Inactive'}</span>
                        </td>
                        <td className="muted">{fmtDate(a.activation_date)}</td>
                        <td className="muted">{fmtDate(a.expiration_date)}</td>
                        <td style={{ textAlign: 'right' }}>
                          <div className="action-pills">
                            <button className={classNames('action-pill', a.active ? 'violet' : 'green')} disabled={saving} onClick={() => onToggleActive(String(a.module_id), !a.active)}>
                              {a.active ? 'Deactivate' : 'Activate'}
                            </button>
                            <button className="action-pill danger" disabled={saving} onClick={() => onEliminar(a.module_id)}>
                              Remove
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                  {asignados.length === 0 && (
                    <tr>
                      <td colSpan={5} className="empresa-muted">
                        No modules assigned yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Container>
  )
}
