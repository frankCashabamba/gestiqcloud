import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarRange, Clock, Clock3, Download, LogIn, LogOut, PauseCircle, PlayCircle, UserCircle, Wallet } from 'lucide-react'
import { GcPageHeader } from '@ui'
import { TENANT_HR } from '@shared/endpoints'
import api from '../../shared/api/client'
import { createVacacion, listVacaciones } from '../../services/api/rrhh'
import { registrarFichaje, actualizarFichaje } from './services/fichajes'
import { useFichajes } from './hooks/useFichajes'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCurrency } from '../../hooks/useCurrency'
import type { Vacacion } from '../../types/hr'
import './hr.css'

// ─── Types ────────────────────────────────────────────────────────────────────

type MeEmployee = {
  id: string
  name: string
  apellidos: string
  puesto: string | null
  estado: string
  fecha_ingreso: string
  email: string | null
  salario_base: number | null
  modalidad_pago: string | null
  tipo_contrato: string | null
}

type PayrollEntry = {
  payroll_detail_id: string
  payroll_id: string
  payroll_month: string
  payroll_date: string
  status: string
  gross_salary: number
  irpf: number
  social_security: number
  total_deductions: number
  net_salary: number
  currency: string
}

type VacForm = {
  fecha_inicio: string
  fecha_fin: string
  tipo: string
  motivo: string
}

type Tab = 'jornada' | 'ausencias' | 'nominas'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getNowStamp() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return {
    fecha: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    hora: `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
  }
}

function getMonthRange(monthStr: string) {
  const [year, month] = monthStr.split('-').map(Number)
  const from = `${year}-${String(month).padStart(2, '0')}-01`
  const lastDay = new Date(year, month, 0).getDate()
  const to = `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
  return { from, to }
}

function currentMonthStr() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function formatDate(value: string) {
  const d = new Date(value + (value.length === 10 ? 'T00:00:00' : ''))
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: 'short', year: 'numeric' }).format(d)
}

function formatMonth(value: string) {
  const [year, month] = value.split('-').map(Number)
  return new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric' }).format(new Date(year, month - 1, 1))
}

function formatCurrencyValue(value: number, currency?: string) {
  const normalizedCurrency = (currency || '').trim().toUpperCase()
  if (!normalizedCurrency) {
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }
  try {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: normalizedCurrency }).format(value)
  } catch {
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }
}

function calcDuration(start?: string, end?: string) {
  if (!start || !end) return null
  const toMin = (t: string) => {
    const [h, m] = t.split(':').map(Number)
    return h * 60 + (m || 0)
  }
  const diff = toMin(end) - toMin(start)
  if (diff <= 0) return null
  return `${Math.floor(diff / 60)}h ${String(diff % 60).padStart(2, '0')}m`
}

function calcTotalHours(fichajes: { horaInicio: string; horaFin?: string; tipo: string }[]) {
  let mins = 0
  for (const f of fichajes) {
    if (f.tipo !== 'trabajo' || !f.horaFin) continue
    const toMin = (t: string) => { const [h, m] = t.split(':').map(Number); return h * 60 + (m || 0) }
    const diff = toMin(f.horaFin) - toMin(f.horaInicio)
    if (diff > 0) mins += diff
  }
  return mins > 0 ? `${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, '0')}m` : '0h 00m'
}

function statusBadge(estado: string) {
  if (estado === 'aprobada') return 'hr-badge hr-badge--success'
  if (estado === 'rechazada') return 'hr-badge hr-badge--danger'
  if (estado === 'cancelada') return 'hr-badge hr-badge--neutral'
  return 'hr-badge hr-badge--pending'
}

function payrollStatusBadge(status: string) {
  if (status === 'PAID') return 'hr-badge hr-badge--success'
  if (status === 'CONFIRMED') return 'hr-badge hr-badge--info'
  return 'hr-badge hr-badge--neutral'
}

function payrollStatusLabel(status: string) {
  const map: Record<string, string> = { PAID: 'Pagada', CONFIRMED: 'Confirmada', DRAFT: 'Borrador', CANCELLED: 'Cancelada' }
  return map[status] ?? status
}

const VAC_FORM_INIT: VacForm = { fecha_inicio: '', fecha_fin: '', tipo: 'vacaciones', motivo: '' }

// ─── Component ────────────────────────────────────────────────────────────────

export default function MiJornada() {
  const navigate = useNavigate()
  const { success, error: toastError, warning, info } = useToast()
  const { currency: companyCurrency, formatCurrency: formatCompanyCurrency } = useCurrency()

  // Perfil
  const [me, setMe] = useState<MeEmployee | null>(null)
  const [meLoading, setMeLoading] = useState(true)
  const [meError, setMeError] = useState<string | null>(null)

  // Tab activa
  const [tab, setTab] = useState<Tab>('jornada')

  // Fichajes
  const [selectedMonth, setSelectedMonth] = useState(currentMonthStr())
  const monthRange = useMemo(() => getMonthRange(selectedMonth), [selectedMonth])
  const fichajesParams = useMemo(
    () => me ? { empleadoId: me.id, fromDate: monthRange.from, toDate: monthRange.to } : undefined,
    [me?.id, monthRange.from, monthRange.to]
  )
  const { fichajes, loading: fichajesLoading, reload: reloadFichajes } = useFichajes(fichajesParams)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Para estado actual (hoy) necesitamos el open entry independiente del mes seleccionado
  const todayStr = useMemo(() => getNowStamp().fecha, [])
  const todayRange = useMemo(() => ({ from: todayStr, to: todayStr }), [todayStr])
  const todayParams = useMemo(
    () => me ? { empleadoId: me.id, fromDate: todayStr, toDate: todayStr } : undefined,
    [me?.id, todayStr]
  )
  const { fichajes: todayFichajes, reload: reloadToday } = useFichajes(todayParams)
  const openEntry = useMemo(() => todayFichajes.find((f) => !f.horaFin) || null, [todayFichajes])

  // Vacaciones
  const [vacaciones, setVacaciones] = useState<Vacacion[]>([])
  const [vacLoading, setVacLoading] = useState(false)
  const [showVacForm, setShowVacForm] = useState(false)
  const [vacForm, setVacForm] = useState<VacForm>(VAC_FORM_INIT)
  const [vacSubmitting, setVacSubmitting] = useState(false)
  const vacDays = useMemo(() => {
    if (!vacForm.fecha_inicio || !vacForm.fecha_fin) return 0
    const ms = new Date(vacForm.fecha_fin).getTime() - new Date(vacForm.fecha_inicio).getTime()
    return Math.max(0, Math.round(ms / 86400000) + 1)
  }, [vacForm.fecha_inicio, vacForm.fecha_fin])

  // Nóminas
  const [nominas, setNominas] = useState<PayrollEntry[]>([])
  const [nominasLoading, setNominasLoading] = useState(false)
  const nominasLoaded = useRef(false)

  // ── Carga del perfil ─────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setMeLoading(true)
        const { data } = await api.get<MeEmployee>(TENANT_HR.me)
        if (!cancelled) setMe(data)
      } catch (e: any) {
        if (!cancelled) setMeError(e?.response?.data?.detail || 'employee_not_found')
      } finally {
        if (!cancelled) setMeLoading(false)
      }
    }
    void load()
    return () => { cancelled = true }
  }, [])

  // ── Carga de vacaciones ──────────────────────────────────────────────────────

  async function loadVacaciones(employeeId: string) {
    setVacLoading(true)
    try {
      const data = await listVacaciones({ empleadoId: employeeId })
      setVacaciones(Array.isArray(data) ? data : data?.items ?? [])
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setVacLoading(false)
    }
  }

  useEffect(() => {
    if (me?.id && tab === 'ausencias') void loadVacaciones(me.id)
  }, [me?.id, tab])

  // ── Carga de nóminas ─────────────────────────────────────────────────────────

  useEffect(() => {
    if (tab !== 'nominas' || nominasLoaded.current) return
    nominasLoaded.current = true
    setNominasLoading(true)
    api.get<{ items: PayrollEntry[] }>(TENANT_HR.mePayroll)
      .then(({ data }) => setNominas(data.items ?? []))
      .catch((e) => toastError(getErrorMessage(e)))
      .finally(() => setNominasLoading(false))
  }, [tab])

  // ── Acciones de fichaje ──────────────────────────────────────────────────────

  async function handleFichar(action: 'clockIn' | 'startBreak' | 'resumeBreak' | 'clockOut') {
    if (!me?.id) return
    const { fecha, hora } = getNowStamp()
    setActionLoading(action)
    try {
      switch (action) {
        case 'clockIn':
          if (openEntry) { info('Ya tienes una entrada abierta'); return }
          await registrarFichaje({ empleadoId: me.id, fecha, horaInicio: hora, tipo: 'trabajo' })
          success('Entrada registrada')
          break
        case 'startBreak':
          if (!openEntry || openEntry.tipo !== 'trabajo') { warning('Necesitas una jornada abierta'); return }
          await actualizarFichaje(openEntry.id, { horaFin: hora })
          await registrarFichaje({ empleadoId: me.id, fecha, horaInicio: hora, tipo: 'descanso' })
          success('Descanso iniciado')
          break
        case 'resumeBreak':
          if (!openEntry || openEntry.tipo !== 'descanso') { warning('No hay descanso abierto'); return }
          await actualizarFichaje(openEntry.id, { horaFin: hora })
          await registrarFichaje({ empleadoId: me.id, fecha, horaInicio: hora, tipo: 'trabajo' })
          success('Jornada retomada')
          break
        case 'clockOut':
          if (!openEntry) { warning('No tienes jornada abierta'); return }
          await actualizarFichaje(openEntry.id, { horaFin: hora })
          success('Salida registrada')
          break
      }
      await Promise.all([reloadFichajes(), reloadToday()])
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setActionLoading(null)
    }
  }

  // ── Solicitud de ausencia ────────────────────────────────────────────────────

  async function handleVacSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!me?.id) return
    setVacSubmitting(true)
    try {
      await createVacacion({
        empleado_id: me.id,
        fecha_inicio: vacForm.fecha_inicio,
        fecha_fin: vacForm.fecha_fin,
        tipo: vacForm.tipo,
        motivo: vacForm.motivo || undefined,
      })
      success('Solicitud enviada')
      setShowVacForm(false)
      setVacForm(VAC_FORM_INIT)
      await loadVacaciones(me.id)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setVacSubmitting(false)
    }
  }

  // ── Estado actual ────────────────────────────────────────────────────────────

  const currentStatus = openEntry?.tipo === 'descanso' ? 'En descanso'
    : openEntry ? 'Trabajando'
      : 'Fuera de jornada'

  const statusColor = openEntry?.tipo === 'descanso' ? 'var(--gc-warning)'
    : openEntry ? 'var(--gc-success)'
      : 'var(--gc-muted)'

  const totalHorasHoy = useMemo(() => calcTotalHours(todayFichajes), [todayFichajes])
  const totalHorasMes = useMemo(() => calcTotalHours(fichajes), [fichajes])

  // ── Render: loading / error ───────────────────────────────────────────────────

  if (meLoading) {
    return (
      <div className="hr-shell">
        <div className="hr-empty"><Clock3 size={30} /><div className="hr-empty__title">Cargando perfil...</div></div>
      </div>
    )
  }

  if (meError || !me) {
    return (
      <div className="hr-shell">
        <div className="hr-empty">
          <UserCircle size={40} />
          <div className="hr-empty__title">Sin ficha de empleado</div>
          <div>No se encontró una ficha en RRHH asociada a tu cuenta.</div>
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--gc-muted)' }}>
            Pide a tu administrador que cree tu ficha con el mismo email de tu usuario.
          </div>
        </div>
      </div>
    )
  }

  // ── Render principal ─────────────────────────────────────────────────────────

  return (
    <div className="hr-shell">

      {/* Header */}
      <section className="hr-hero">
        <GcPageHeader
          badge="Mi espacio"
          title={`${me.name} ${me.apellidos}`}
          subtitle={[me.puesto, me.tipo_contrato].filter(Boolean).join(' · ')}
          onBack={() => navigate('..', { replace: true })}
        />
        <div className="hr-kpi-grid" style={{ marginTop: '1rem' }}>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Estado hoy</div>
            <div className="hr-kpi-card__value" style={{ color: statusColor }}>{currentStatus}</div>
            {openEntry && <div className="hr-kpi-card__hint">Desde {openEntry.horaInicio}</div>}
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Horas hoy</div>
            <div className="hr-kpi-card__value">{totalHorasHoy}</div>
            <div className="hr-kpi-card__hint">Trabajo efectivo</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Horas en {formatMonth(selectedMonth).split(' ')[0]}</div>
            <div className="hr-kpi-card__value">{totalHorasMes}</div>
            <div className="hr-kpi-card__hint">Mes seleccionado</div>
          </div>
          {me.salario_base != null && (
            <div className="hr-kpi-card">
              <div className="hr-kpi-card__label">Salario base</div>
              <div className="hr-kpi-card__value">{formatCompanyCurrency(me.salario_base)}</div>
              <div className="hr-kpi-card__hint">{me.modalidad_pago ?? ''}</div>
            </div>
          )}
        </div>
      </section>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, margin: '1.25rem 0 1rem', borderBottom: '1px solid var(--gc-border)' }}>
        {([
          { key: 'jornada', label: 'Jornada', icon: Clock },
          { key: 'ausencias', label: 'Ausencias', icon: CalendarRange },
          { key: 'nominas', label: 'Mis nóminas', icon: Wallet },
        ] as const).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
              border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 14, fontWeight: tab === key ? 600 : 400,
              color: tab === key ? 'var(--gc-primary)' : 'var(--gc-muted)',
              borderBottom: tab === key ? '2px solid var(--gc-primary)' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            <Icon size={15} />{label}
          </button>
        ))}
      </div>

      {/* ── TAB: JORNADA ─────────────────────────────────────────────────── */}
      {tab === 'jornada' && (
        <>
          {/* Botones de fichaje */}
          <section className="hr-toolbar" style={{ marginBottom: '1.25rem' }}>
            <div className="hr-table-meta" style={{ marginBottom: 10 }}>
              <div className="hr-kpi-card__label">Registrar jornada</div>
            </div>
            <div className="hr-actions-row">
              <button
                type="button"
                className="gc-btn gc-btn--primary"
                onClick={() => void handleFichar('clockIn')}
                disabled={actionLoading !== null || Boolean(openEntry)}
              >
                <LogIn size={15} />
                {actionLoading === 'clockIn' ? 'Registrando...' : 'Entrada'}
              </button>
              <button
                type="button"
                className="gc-btn gc-btn--ghost"
                onClick={() => void handleFichar('startBreak')}
                disabled={actionLoading !== null || openEntry?.tipo !== 'trabajo'}
              >
                <PauseCircle size={15} />
                Descanso
              </button>
              <button
                type="button"
                className="gc-btn gc-btn--ghost"
                onClick={() => void handleFichar('resumeBreak')}
                disabled={actionLoading !== null || openEntry?.tipo !== 'descanso'}
              >
                <PlayCircle size={15} />
                Retomar
              </button>
              <button
                type="button"
                className="gc-btn gc-btn--danger"
                onClick={() => void handleFichar('clockOut')}
                disabled={actionLoading !== null || !openEntry}
              >
                <LogOut size={15} />
                {actionLoading === 'clockOut' ? 'Registrando...' : 'Salida'}
              </button>
            </div>
          </section>

          {/* Selector de mes + tabla */}
          <section className="gc-table-wrap">
            <div className="hr-table-meta" style={{ marginBottom: 10 }}>
              <span className="hr-kpi-card__label">Historial de fichajes</span>
              <input
                type="month"
                className="gc-input"
                style={{ width: 160 }}
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
              />
            </div>

            {fichajesLoading ? (
              <div className="hr-empty"><Clock3 size={24} /><div>Cargando...</div></div>
            ) : fichajes.length === 0 ? (
              <div className="hr-empty">
                <Clock size={28} />
                <div className="hr-empty__title">Sin registros en {formatMonth(selectedMonth)}</div>
              </div>
            ) : (
              <table className="gc-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Entrada</th>
                    <th>Salida</th>
                    <th>Duración</th>
                    <th>Tipo</th>
                  </tr>
                </thead>
                <tbody>
                  {fichajes.map((f) => (
                    <tr key={f.id}>
                      <td>{formatDate(f.fecha)}</td>
                      <td>{f.horaInicio}</td>
                      <td>
                        {f.horaFin ?? <span className="hr-badge hr-badge--pending">Abierto</span>}
                      </td>
                      <td>{calcDuration(f.horaInicio, f.horaFin) ?? '—'}</td>
                      <td>
                        <span className={f.tipo === 'trabajo' ? 'hr-badge hr-badge--success' : 'hr-badge hr-badge--info'}>
                          {f.tipo === 'trabajo' ? 'Trabajo' : f.tipo === 'descanso' ? 'Descanso' : f.tipo}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}

      {/* ── TAB: AUSENCIAS ───────────────────────────────────────────────── */}
      {tab === 'ausencias' && (
        <section>
          <div className="hr-table-meta" style={{ marginBottom: 12 }}>
            <span className="hr-kpi-card__label">Mis solicitudes de ausencia</span>
            <button
              type="button"
              className="gc-btn gc-btn--primary"
              onClick={() => setShowVacForm((v) => !v)}
            >
              <CalendarRange size={14} />
              {showVacForm ? 'Cancelar' : 'Nueva solicitud'}
            </button>
          </div>

          {showVacForm && (
            <form onSubmit={(e) => void handleVacSubmit(e)} className="hr-toolbar" style={{ marginBottom: 16 }}>
              <div className="hr-toolbar-grid">
                <label className="hr-field">
                  <span className="hr-field__label">Tipo</span>
                  <select
                    className="gc-input gc-select"
                    value={vacForm.tipo}
                    onChange={(e) => setVacForm((f) => ({ ...f, tipo: e.target.value }))}
                  >
                    <option value="vacaciones">Vacaciones</option>
                    <option value="baja_medica">Baja médica</option>
                    <option value="permiso">Permiso</option>
                    <option value="otro">Otro</option>
                  </select>
                </label>
                <label className="hr-field">
                  <span className="hr-field__label">Fecha inicio</span>
                  <input
                    type="date"
                    className="gc-input"
                    required
                    value={vacForm.fecha_inicio}
                    onChange={(e) => setVacForm((f) => ({ ...f, fecha_inicio: e.target.value }))}
                  />
                </label>
                <label className="hr-field">
                  <span className="hr-field__label">Fecha fin</span>
                  <input
                    type="date"
                    className="gc-input"
                    required
                    min={vacForm.fecha_inicio}
                    value={vacForm.fecha_fin}
                    onChange={(e) => setVacForm((f) => ({ ...f, fecha_fin: e.target.value }))}
                  />
                </label>
                <label className="hr-field hr-field--wide">
                  <span className="hr-field__label">
                    Motivo
                    {vacDays > 0 && <span style={{ fontWeight: 400, color: 'var(--gc-muted)', marginLeft: 8 }}>{vacDays} día{vacDays !== 1 ? 's' : ''}</span>}
                  </span>
                  <input
                    className="gc-input"
                    value={vacForm.motivo}
                    onChange={(e) => setVacForm((f) => ({ ...f, motivo: e.target.value }))}
                    placeholder="Opcional — asunto personal, médico, etc."
                  />
                </label>
              </div>
              <div className="hr-actions-row" style={{ marginTop: 10 }}>
                <button type="submit" className="gc-btn gc-btn--primary" disabled={vacSubmitting}>
                  {vacSubmitting ? 'Enviando...' : 'Enviar solicitud'}
                </button>
              </div>
            </form>
          )}

          {vacLoading ? (
            <div className="hr-empty"><Clock3 size={24} /><div>Cargando...</div></div>
          ) : vacaciones.length === 0 ? (
            <div className="hr-empty">
              <CalendarRange size={28} />
              <div className="hr-empty__title">Sin solicitudes registradas</div>
              <div>Cuando envíes una solicitud aparecerá aquí con su estado.</div>
            </div>
          ) : (
            <table className="gc-table">
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Desde</th>
                  <th>Hasta</th>
                  <th>Días</th>
                  <th>Estado</th>
                  <th>Motivo</th>
                </tr>
              </thead>
              <tbody>
                {vacaciones.map((v) => (
                  <tr key={String(v.id)}>
                    <td>{v.tipo}</td>
                    <td>{formatDate(v.fecha_inicio)}</td>
                    <td>{formatDate(v.fecha_fin)}</td>
                    <td>{v.dias}</td>
                    <td><span className={statusBadge(v.estado)}>{v.estado}</span></td>
                    <td style={{ color: 'var(--gc-muted)', fontSize: 13 }}>{v.motivo ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {/* ── TAB: NÓMINAS ─────────────────────────────────────────────────── */}
      {tab === 'nominas' && (
        <section>
          <div className="hr-table-meta" style={{ marginBottom: 12 }}>
            <span className="hr-kpi-card__label">Mis nóminas</span>
          </div>

          {nominasLoading ? (
            <div className="hr-empty"><Clock3 size={24} /><div>Cargando nóminas...</div></div>
          ) : nominas.length === 0 ? (
            <div className="hr-empty">
              <Wallet size={28} />
              <div className="hr-empty__title">Sin nóminas disponibles</div>
              <div>Las nóminas confirmadas o pagadas aparecerán aquí.</div>
            </div>
          ) : (
            <table className="gc-table">
              <thead>
                <tr>
                  <th>Período</th>
                  <th>Bruto</th>
                  <th>Deducciones</th>
                  <th>Neto</th>
                  <th>Estado</th>
                  <th>Fecha pago</th>
                </tr>
              </thead>
              <tbody>
                {nominas.map((n) => (
                  <tr key={n.payroll_detail_id}>
                    <td style={{ fontWeight: 500 }}>{formatMonth(n.payroll_month)}</td>
                    <td>{formatCurrencyValue(n.gross_salary, companyCurrency || n.currency)}</td>
                    <td style={{ color: 'var(--gc-danger)' }}>−{formatCurrencyValue(n.total_deductions, companyCurrency || n.currency)}</td>
                    <td style={{ fontWeight: 600, color: 'var(--gc-success)' }}>{formatCurrencyValue(n.net_salary, companyCurrency || n.currency)}</td>
                    <td><span className={payrollStatusBadge(n.status)}>{payrollStatusLabel(n.status)}</span></td>
                    <td>{formatDate(n.payroll_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

    </div>
  )
}
