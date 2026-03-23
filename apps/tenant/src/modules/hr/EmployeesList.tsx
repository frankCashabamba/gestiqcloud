import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Plus, Search, UserCheck } from 'lucide-react'
import { BackButton } from '@ui'
import { listEmpleados } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Empleado } from '../../types/hr'
import { PAGINATION_DEFAULTS } from '../../constants/defaults'
import './hr.css'

const estadoLabel: Record<string, string> = {
  activo: 'Activo',
  baja: 'Baja',
  suspendido: 'Suspendido',
}
const estadoBadge: Record<string, string> = {
  activo: 'hr-badge--success',
  baja: 'hr-badge--danger',
  suspendido: 'hr-badge--pending',
}

export default function EmpleadosList() {
    const { t } = useTranslation(['hr', 'common'])
    const [items, setItems] = useState<Empleado[]>([])
    const [loading, setLoading] = useState(false)
    const nav = useNavigate()
    const { error: toastError } = useToast()

    const [search, setSearch] = useState('')
    const [departamento, setDepartamento] = useState('')
    const [estadoFilter, setEstadoFilter] = useState('')
    const [per, setPer] = useState(PAGINATION_DEFAULTS.RRHH_PER_PAGE)

    useEffect(() => {
        (async () => {
            try {
                setLoading(true)
                const data = await listEmpleados()
                setItems(data?.items || data || [])
            } catch (e: any) {
                toastError(getErrorMessage(e))
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    const filtered = useMemo(() => items.filter(v => {
        if (departamento && v.departamento_id !== departamento) return false
        if (estadoFilter && v.estado !== estadoFilter) return false
        if (search) {
            const s = search.toLowerCase()
            const matches =
                (v.sku || '').toLowerCase().includes(s) ||
                v.name.toLowerCase().includes(s) ||
                v.apellidos.toLowerCase().includes(s) ||
                v.numero_documento.toLowerCase().includes(s) ||
                (v.puesto || '').toLowerCase().includes(s)
            if (!matches) return false
        }
        return true
    }), [items, departamento, estadoFilter, search])

    const { page, setPage, totalPages, view, setPerPage } = usePagination(filtered, per)
    useEffect(() => setPerPage(per), [per, setPerPage])

    const departamentos = Array.from(new Set(items.map(e => e.departamento_id).filter(Boolean)))

    return (
        <div className="hr-shell">
            <BackButton onClick={() => nav(-1)} />
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                <div>
                    <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--gc-muted)', marginBottom: '0.2rem' }}>Equipo</div>
                    <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--gc-foreground)' }}>{t('hr:employees.title')}</h1>
                </div>
                <button className="gc-btn gc-btn--primary" onClick={() => nav('nuevo')} style={{ gap: '0.4rem' }}>
                    <Plus size={18} />
                    {t('hr:employees.new')}
                </button>
            </div>

            {/* Filtros */}
            <div className="hr-toolbar">
                <div className="hr-toolbar-grid">
                    <div className="hr-field">
                        <label className="hr-field__label">{t('hr:employees.search')}</label>
                        <div style={{ position: 'relative' }}>
                            <Search size={15} style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--gc-muted)', pointerEvents: 'none' }} />
                            <input
                                type="text"
                                placeholder={t('hr:employees.searchPlaceholder')}
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="gc-input"
                                style={{ paddingLeft: '2rem' }}
                            />
                        </div>
                    </div>
                    <div className="hr-field">
                        <label className="hr-field__label">{t('hr:employees.department')}</label>
                        <select value={departamento} onChange={(e) => setDepartamento(e.target.value)} className="gc-input">
                            <option value="">{t('hr:employees.all')}</option>
                            {departamentos.map((d) => (
                                <option key={d} value={d}>{d}</option>
                            ))}
                        </select>
                    </div>
                    <div className="hr-field">
                        <label className="hr-field__label">{t('hr:employees.status')}</label>
                        <select value={estadoFilter} onChange={(e) => setEstadoFilter(e.target.value)} className="gc-input">
                            <option value="">{t('hr:employees.all')}</option>
                            <option value="activo">{t('hr:employees.active')}</option>
                            <option value="baja">{t('hr:employees.terminatedStatus')}</option>
                            <option value="suspendido">{t('hr:employees.suspended')}</option>
                        </select>
                    </div>
                    <div className="hr-field">
                        <label className="hr-field__label">{t('hr:employees.perPage')}</label>
                        <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="gc-input">
                            <option value="10">10</option>
                            <option value="25">25</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Tabla */}
            <div style={{ border: '1px solid var(--gc-border)', borderRadius: 20, overflow: 'hidden', background: 'var(--gc-surface)', boxShadow: 'var(--gc-shadow-sm)' }}>
                {loading ? (
                    <div className="hr-empty">
                        <div className="hr-empty__title">Cargando empleados…</div>
                    </div>
                ) : view.length === 0 ? (
                    <div className="hr-empty">
                        <UserCheck size={36} style={{ opacity: 0.35 }} />
                        <div className="hr-empty__title">{t('hr:employees.empty')}</div>
                    </div>
                ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--gc-border)', background: 'color-mix(in srgb, var(--gc-bg) 60%, white)' }}>
                                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--gc-muted)' }}>{t('hr:employees.name')}</th>
                                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--gc-muted)' }}>{t('hr:employees.position')}</th>
                                <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--gc-muted)' }}>{t('hr:employees.department')}</th>
                                <th style={{ padding: '0.75rem 1rem', textAlign: 'center', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--gc-muted)' }}>{t('hr:employees.status')}</th>
                                <th style={{ padding: '0.75rem 1rem', textAlign: 'right', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--gc-muted)' }}>{t('hr:employees.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {view.map((e) => (
                                <tr key={e.id} style={{ borderBottom: '1px solid var(--gc-border)' }}
                                    onMouseEnter={ev => (ev.currentTarget.style.background = 'color-mix(in srgb, var(--gc-primary) 4%, transparent)')}
                                    onMouseLeave={ev => (ev.currentTarget.style.background = 'transparent')}
                                >
                                    <td style={{ padding: '0.85rem 1rem' }}>
                                        <div className="hr-record-cell">
                                            <Link to={e.id} className="hr-record-cell__title" style={{ textDecoration: 'none', color: 'inherit' }}>
                                                {e.name} {e.apellidos}
                                            </Link>
                                            {e.sku && <div className="hr-record-cell__meta">#{e.sku}</div>}
                                        </div>
                                    </td>
                                    <td style={{ padding: '0.85rem 1rem', color: 'var(--gc-foreground)' }}>{e.puesto || <span style={{ color: 'var(--gc-muted)' }}>—</span>}</td>
                                    <td style={{ padding: '0.85rem 1rem', color: 'var(--gc-foreground)' }}>{e.departamento_id || <span style={{ color: 'var(--gc-muted)' }}>—</span>}</td>
                                    <td style={{ padding: '0.85rem 1rem', textAlign: 'center' }}>
                                        <span className={`hr-badge ${estadoBadge[e.estado] || 'hr-badge--neutral'}`}>
                                            {estadoLabel[e.estado] || e.estado}
                                        </span>
                                    </td>
                                    <td style={{ padding: '0.85rem 1rem' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                            <Link to={e.id} className="gc-btn gc-btn--ghost gc-btn--sm">
                                                Ver
                                            </Link>
                                            <Link to={`${e.id}/editar`} className="gc-btn gc-btn--secondary gc-btn--sm">
                                                Editar
                                            </Link>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--gc-muted)' }}>
                    {t('hr:employees.showing', { current: view.length, total: filtered.length })}
                </p>
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </div>
        </div>
    )
}
