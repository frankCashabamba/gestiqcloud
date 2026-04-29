import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CalendarRange, CheckCircle2, Clock3, Filter, Plus, XCircle } from 'lucide-react'
import { GcPageHeader } from '@ui'
import { listVacaciones, aprobarVacacion, rechazarVacacion } from '../../services/api/hr'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Vacacion } from '../../types/hr'
import './hr.css'

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

function getStatusClass(status: Vacacion['estado']) {
  if (status === 'aprobada') return 'hr-badge hr-badge--success'
  if (status === 'rechazada') return 'hr-badge hr-badge--danger'
  if (status === 'cancelada') return 'hr-badge hr-badge--neutral'
  return 'hr-badge hr-badge--pending'
}

function getStatusLabel(t: (key: string) => string, status: Vacacion['estado']) {
  if (status === 'aprobada') return t('hr:vacations.approvedStatus')
  if (status === 'rechazada') return t('hr:vacations.rejectedStatus')
  if (status === 'cancelada') return t('hr:vacations.cancelled')
  return t('hr:vacations.pending')
}

function getTypeLabel(t: (key: string) => string, type: Vacacion['tipo']) {
  if (type === 'vacaciones') return t('hr:vacations.vacation')
  if (type === 'baja_medica') return t('hr:vacations.medicalLeave')
  if (type === 'permiso') return t('hr:vacations.leave')
  return t('hr:vacations.other')
}

export default function VacacionesList() {
  const { t } = useTranslation(['hr', 'common'])
  const [items, setItems] = useState<Vacacion[]>([])
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  const [estadoFilter, setEstadoFilter] = useState('')
  const [empleadoSearch, setEmpleadoSearch] = useState('')
  const [per, setPer] = useState(10)
  const [rejectTarget, setRejectTarget] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await listVacaciones()
      setItems(data?.items || data || [])
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filtered = useMemo(
    () =>
      items.filter((v) => {
        if (estadoFilter && v.estado !== estadoFilter) return false
        if (empleadoSearch) {
          const s = empleadoSearch.toLowerCase()
          if (!v.empleado_id.toLowerCase().includes(s)) return false
        }
        return true
      }),
    [items, estadoFilter, empleadoSearch]
  )

  const stats = useMemo(() => {
    const pending = items.filter((item) => item.estado === 'pendiente').length
    const approved = items.filter((item) => item.estado === 'aprobada').length
    const totalDays = items.reduce((sum, item) => sum + (item.dias || 0), 0)
    return { pending, approved, totalDays }
  }, [items])

  const { page, setPage, totalPages, view, setPerPage } = usePagination(filtered, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const handleAprobar = async (id: string) => {
    try {
      await aprobarVacacion(id)
      success(t('hr:vacations.approved'))
      await loadData()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const handleRechazar = async () => {
    if (!rejectTarget) return
    try {
      await rechazarVacacion(rejectTarget, { motivo: rejectReason.trim() || undefined })
      success(t('hr:vacations.rejected'))
      setRejectTarget(null)
      setRejectReason('')
      await loadData()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <div className="hr-hero__content">
          <GcPageHeader
            badge="Ausencias"
            title={t('hr:vacations.title')}
            subtitle="Solicitudes, permisos y aprobaciones con lectura inmediata para responsables de RRHH."
            onBack={() => nav('..', { replace: true })}
            actions={
              <button className="gc-btn gc-btn--primary" onClick={() => nav('new')}>
                <Plus size={16} />
                {t('hr:vacations.newRequest')}
              </button>
            }
          />
        </div>

        <div className="hr-kpi-grid" style={{ marginTop: '1.25rem' }}>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Solicitudes</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <CalendarRange size={18} />
              </span>
              {items.length}
            </div>
            <div className="hr-kpi-card__hint">Total de registros disponibles en el modulo.</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Pendientes</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <Clock3 size={18} />
              </span>
              {stats.pending}
            </div>
            <div className="hr-kpi-card__hint">Solicitudes que requieren decision del responsable.</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Aprobadas</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <CheckCircle2 size={18} />
              </span>
              {stats.approved}
            </div>
            <div className="hr-kpi-card__hint">{stats.totalDays} dias planificados entre todos los registros.</div>
          </div>
        </div>
      </section>

      <section className="hr-toolbar">
        <div className="hr-table-meta">
          <div className="hr-record-cell">
            <span className="hr-record-cell__title">Filtros operativos</span>
            <span className="hr-record-cell__meta">
              Refina por estado, empleado y volumen para revisar el backlog real.
            </span>
          </div>
          <span className="hr-badge hr-badge--info">
            <Filter size={13} />
            {filtered.length} visibles
          </span>
        </div>

        <div className="hr-toolbar-grid">
          <label className="hr-field">
            <span className="hr-field__label">{t('hr:vacations.status')}</span>
            <select
              value={estadoFilter}
              onChange={(e) => setEstadoFilter(e.target.value)}
              className="gc-input gc-select"
            >
              <option value="">{t('hr:employees.all')}</option>
              <option value="pendiente">{t('hr:vacations.pending')}</option>
              <option value="aprobada">{t('hr:vacations.approvedStatus')}</option>
              <option value="rechazada">{t('hr:vacations.rejectedStatus')}</option>
              <option value="cancelada">{t('hr:vacations.cancelled')}</option>
            </select>
          </label>

          <label className="hr-field">
            <span className="hr-field__label">{t('hr:vacations.searchEmployee')}</span>
            <input
              type="text"
              placeholder={t('hr:vacations.searchPlaceholder')}
              value={empleadoSearch}
              onChange={(e) => setEmpleadoSearch(e.target.value)}
              className="gc-input"
            />
          </label>

          <label className="hr-field">
            <span className="hr-field__label">{t('hr:vacations.perPage')}</span>
            <select
              value={per}
              onChange={(e) => setPer(Number(e.target.value))}
              className="gc-input gc-select"
            >
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </label>
        </div>
      </section>

      <section className="gc-table-wrap">
        <table className="gc-table">
          <thead>
            <tr>
              <th>{t('hr:vacations.employee')}</th>
              <th>{t('hr:vacations.type')}</th>
              <th>Periodo</th>
              <th>{t('hr:vacations.days')}</th>
              <th>{t('hr:vacations.status')}</th>
              <th>{t('hr:vacations.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6}>
                  <div className="hr-empty">
                    <div className="hr-empty__title">{t('hr:vacations.loading')}</div>
                  </div>
                </td>
              </tr>
            ) : view.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="hr-empty">
                    <XCircle size={30} />
                    <div className="hr-empty__title">{t('hr:vacations.empty')}</div>
                    <div>No hay coincidencias con los filtros actuales.</div>
                  </div>
                </td>
              </tr>
            ) : (
              view.map((v) => (
                <tr key={v.id}>
                  <td>
                    <div className="hr-record-cell">
                      <Link to={`../empleados/${v.empleado_id}`} className="hr-link-inline">
                        <span className="hr-record-cell__title">{v.empleado_id}</span>
                      </Link>
                      <span className="hr-record-cell__meta">Solicitud {v.id.slice(0, 8)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="hr-record-cell">
                      <span className="hr-record-cell__title">{getTypeLabel(t, v.tipo)}</span>
                      <span className="hr-record-cell__meta">{v.motivo || 'Sin motivo detallado'}</span>
                    </div>
                  </td>
                  <td>
                    <div className="hr-record-cell">
                      <span className="hr-record-cell__title">{formatDate(v.fecha_inicio)}</span>
                      <span className="hr-record-cell__meta">Hasta {formatDate(v.fecha_fin)}</span>
                    </div>
                  </td>
                  <td>{v.dias}</td>
                  <td>
                    <span className={getStatusClass(v.estado)}>{getStatusLabel(t, v.estado)}</span>
                  </td>
                  <td>
                    {v.estado === 'pendiente' ? (
                      <div className="hr-actions-row">
                        <button
                          onClick={() => handleAprobar(v.id)}
                          className="gc-btn gc-btn--primary gc-btn--sm"
                        >
                          {t('hr:vacations.approve')}
                        </button>
                        <button
                          onClick={() => {
                            setRejectTarget(v.id)
                            setRejectReason('')
                          }}
                          className="gc-btn gc-btn--danger gc-btn--sm"
                        >
                          {t('hr:vacations.reject')}
                        </button>
                      </div>
                    ) : (
                      <span className="hr-table-note">Sin acciones pendientes</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      <div className="hr-table-meta">
        <p className="hr-table-note">
          {t('hr:vacations.showing', { current: view.length, total: filtered.length })}
        </p>
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h3 className="font-semibold text-lg mb-2">{t('hr:vacations.reject')}</h3>
            <label className="hr-field">
              <span className="hr-field__label">{t('hr:vacations.rejectionReason')}</span>
              <textarea
                value={rejectReason}
                onChange={(event) => setRejectReason(event.target.value)}
                className="gc-input min-h-24"
                autoFocus
              />
            </label>
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => {
                  setRejectTarget(null)
                  setRejectReason('')
                }}
                className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm"
              >
                {t('common:cancel')}
              </button>
              <button
                type="button"
                onClick={handleRechazar}
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm"
              >
                {t('hr:vacations.reject')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
