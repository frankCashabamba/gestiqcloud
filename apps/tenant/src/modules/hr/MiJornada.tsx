import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CalendarRange, Clock3, LogIn, LogOut, PauseCircle, PlayCircle, UserCircle } from 'lucide-react'
import { GcPageHeader } from '@ui'
import { TENANT_HR } from '@shared/endpoints'
import api from '../../shared/api/client'
import { createVacacion, listVacaciones } from '../../services/api/rrhh'
import { registrarFichaje, actualizarFichaje } from './services/fichajes'
import { useFichajes } from './hooks/useFichajes'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { Vacacion } from '../../types/hr'
import './hr.css'

type MeEmployee = {
  id: string
  name: string
  apellidos: string
  puesto: string | null
  estado: string
  fecha_ingreso: string
  email: string | null
}

type VacationForm = {
  fecha_inicio: string
  fecha_fin: string
  tipo: string
  motivo: string
}

const VACATION_FORM_INITIAL: VacationForm = {
  fecha_inicio: '',
  fecha_fin: '',
  tipo: 'vacaciones',
  motivo: '',
}

function getNowStamp() {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return {
    fecha: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    hora: `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
  }
}

function formatDate(value: string) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: 'short', year: 'numeric' }).format(d)
}

function getStatusBadge(estado: string) {
  if (estado === 'aprobada') return 'hr-badge hr-badge--success'
  if (estado === 'rechazada') return 'hr-badge hr-badge--danger'
  return 'hr-badge hr-badge--pending'
}

export default function MiJornada() {
  const { t } = useTranslation(['hr', 'common'])
  const { success, error: toastError, warning, info } = useToast()

  const [me, setMe] = useState<MeEmployee | null>(null)
  const [meLoading, setMeLoading] = useState(true)
  const [meError, setMeError] = useState<string | null>(null)

  const [vacaciones, setVacaciones] = useState<Vacacion[]>([])
  const [vacLoading, setVacLoading] = useState(false)
  const [showVacForm, setShowVacForm] = useState(false)
  const [vacForm, setVacForm] = useState<VacationForm>(VACATION_FORM_INITIAL)
  const [vacSubmitting, setVacSubmitting] = useState(false)

  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const { fichajes, loading: fichajesLoading, reload } = useFichajes()

  // Cargar perfil del empleado autenticado
  useEffect(() => {
    let cancelled = false
    async function loadMe() {
      try {
        setMeLoading(true)
        const { data } = await api.get<MeEmployee>(TENANT_HR.me)
        if (!cancelled) setMe(data)
      } catch (e: any) {
        if (!cancelled) setMeError(e?.response?.data?.detail || 'No se encontró ficha de empleado')
      } finally {
        if (!cancelled) setMeLoading(false)
      }
    }
    void loadMe()
    return () => { cancelled = true }
  }, [])

  // Cargar vacaciones propias cuando tengamos el employee_id
  useEffect(() => {
    if (!me?.id) return
    let cancelled = false
    async function loadVac() {
      setVacLoading(true)
      try {
        const data = await listVacaciones({ empleadoId: me!.id })
        if (!cancelled) setVacaciones(Array.isArray(data) ? data : data?.items || [])
      } catch (e: any) {
        if (!cancelled) toastError(getErrorMessage(e))
      } finally {
        if (!cancelled) setVacLoading(false)
      }
    }
    void loadVac()
    return () => { cancelled = true }
  }, [me?.id])

  // Fichajes del empleado actual
  const misFichajes = useMemo(() => {
    if (!me?.id) return []
    return fichajes
      .filter((f) => f.empleadoId === me.id)
      .sort((a, b) => `${b.fecha}T${b.horaInicio}`.localeCompare(`${a.fecha}T${a.horaInicio}`))
  }, [fichajes, me?.id])

  const openEntry = useMemo(() => misFichajes.find((f) => !f.horaFin) || null, [misFichajes])

  const currentStatus = openEntry?.tipo === 'descanso'
    ? 'En descanso'
    : openEntry
      ? 'Trabajando'
      : 'Fuera de jornada'

  async function handleFichar(action: 'clockIn' | 'startBreak' | 'resumeBreak' | 'clockOut') {
    if (!me?.id) return
    const { fecha, hora } = getNowStamp()
    setActionLoading(action)
    try {
      if (action === 'clockIn') {
        if (openEntry) { info('Ya tienes una entrada abierta'); return }
        await registrarFichaje({ empleadoId: me.id, fecha, horaInicio: hora, tipo: 'trabajo' })
        success('Entrada registrada')
      } else if (action === 'startBreak') {
        if (!openEntry || openEntry.tipo !== 'trabajo') { warning('Necesitas tener una jornada abierta'); return }
        await actualizarFichaje(openEntry.id, { horaFin: hora })
        await registrarFichaje({ empleadoId: me.id, fecha, horaInicio: hora, tipo: 'descanso' })
        success('Descanso iniciado')
      } else if (action === 'resumeBreak') {
        if (!openEntry || openEntry.tipo !== 'descanso') { warning('No tienes un descanso abierto'); return }
        await actualizarFichaje(openEntry.id, { horaFin: hora })
        await registrarFichaje({ empleadoId: me.id, fecha, horaInicio: hora, tipo: 'trabajo' })
        success('Jornada retomada')
      } else if (action === 'clockOut') {
        if (!openEntry) { warning('No tienes jornada abierta'); return }
        await actualizarFichaje(openEntry.id, { horaFin: hora })
        success('Salida registrada')
      }
      await reload()
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setActionLoading(null)
    }
  }

  async function handleVacacionSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!me?.id || !vacForm.fecha_inicio || !vacForm.fecha_fin) return
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
      setVacForm(VACATION_FORM_INITIAL)
      // Refrescar
      const data = await listVacaciones({ empleadoId: me.id })
      setVacaciones(Array.isArray(data) ? data : data?.items || [])
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setVacSubmitting(false)
    }
  }

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
          <div>{meError || 'No se encontró una ficha de empleado asociada a tu cuenta.'}</div>
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--gc-muted)' }}>
            Pide a tu administrador que cree tu ficha en RRHH con el mismo email de tu usuario.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <GcPageHeader
          badge="Mi jornada"
          title={`${me.name} ${me.apellidos}`}
          subtitle={[me.puesto, me.estado === 'activo' ? 'Activo' : me.estado].filter(Boolean).join(' · ')}
        />
      </section>

      {/* FICHAJES */}
      <section className="hr-quick-grid">
        <article className="hr-status-card">
          <div className="hr-status-card__eyebrow">Estado actual</div>
          <div className="hr-status-card__value">{currentStatus}</div>
          {openEntry && (
            <div className="hr-status-card__hint">
              Desde las {openEntry.horaInicio}
            </div>
          )}
        </article>

        <article className="hr-toolbar">
          <div className="hr-table-meta">
            <div>
              <div className="hr-kpi-card__label">Registrar jornada</div>
            </div>
          </div>
          <div className="hr-actions-row">
            <button
              type="button"
              className="gc-btn gc-btn--primary"
              onClick={() => void handleFichar('clockIn')}
              disabled={actionLoading !== null || Boolean(openEntry)}
            >
              <LogIn size={16} />
              {actionLoading === 'clockIn' ? 'Registrando...' : 'Entrada'}
            </button>
            <button
              type="button"
              className="gc-btn gc-btn--ghost"
              onClick={() => void handleFichar('startBreak')}
              disabled={actionLoading !== null || openEntry?.tipo !== 'trabajo'}
            >
              <PauseCircle size={16} />
              Iniciar descanso
            </button>
            <button
              type="button"
              className="gc-btn gc-btn--ghost"
              onClick={() => void handleFichar('resumeBreak')}
              disabled={actionLoading !== null || openEntry?.tipo !== 'descanso'}
            >
              <PlayCircle size={16} />
              Retomar jornada
            </button>
            <button
              type="button"
              className="gc-btn gc-btn--danger"
              onClick={() => void handleFichar('clockOut')}
              disabled={actionLoading !== null || !openEntry}
            >
              <LogOut size={16} />
              Salida
            </button>
          </div>
        </article>
      </section>

      {/* HISTORIAL DE FICHAJES */}
      {misFichajes.length > 0 && (
        <section className="gc-table-wrap" style={{ marginTop: '1.25rem' }}>
          <div className="hr-table-meta" style={{ marginBottom: 8 }}>
            <span className="hr-kpi-card__label">Mis registros recientes</span>
          </div>
          <table className="gc-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Entrada</th>
                <th>Salida</th>
                <th>Tipo</th>
              </tr>
            </thead>
            <tbody>
              {misFichajes.slice(0, 10).map((f) => (
                <tr key={f.id}>
                  <td>{formatDate(f.fecha)}</td>
                  <td>{f.horaInicio}</td>
                  <td>{f.horaFin ?? <span className="hr-badge hr-badge--pending">Abierto</span>}</td>
                  <td>
                    <span className={f.tipo === 'trabajo' ? 'hr-badge hr-badge--success' : 'hr-badge hr-badge--info'}>
                      {f.tipo === 'trabajo' ? 'Trabajo' : f.tipo === 'descanso' ? 'Descanso' : f.tipo}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* VACACIONES */}
      <section style={{ marginTop: '2rem' }}>
        <div className="hr-table-meta" style={{ marginBottom: 12 }}>
          <div>
            <div className="hr-kpi-card__label">Mis solicitudes de ausencia</div>
          </div>
          <button
            type="button"
            className="gc-btn gc-btn--primary"
            onClick={() => setShowVacForm((v) => !v)}
          >
            <CalendarRange size={15} />
            Nueva solicitud
          </button>
        </div>

        {showVacForm && (
          <form onSubmit={(e) => void handleVacacionSubmit(e)} className="hr-toolbar" style={{ marginBottom: 16 }}>
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
                  value={vacForm.fecha_fin}
                  onChange={(e) => setVacForm((f) => ({ ...f, fecha_fin: e.target.value }))}
                />
              </label>
              <label className="hr-field hr-field--wide">
                <span className="hr-field__label">Motivo (opcional)</span>
                <input
                  className="gc-input"
                  value={vacForm.motivo}
                  onChange={(e) => setVacForm((f) => ({ ...f, motivo: e.target.value }))}
                  placeholder="Describe el motivo"
                />
              </label>
            </div>
            <div className="hr-actions-row" style={{ marginTop: 8 }}>
              <button type="submit" className="gc-btn gc-btn--primary" disabled={vacSubmitting}>
                {vacSubmitting ? 'Enviando...' : 'Enviar solicitud'}
              </button>
              <button type="button" className="gc-btn gc-btn--ghost" onClick={() => setShowVacForm(false)}>
                Cancelar
              </button>
            </div>
          </form>
        )}

        {vacLoading ? (
          <div className="hr-empty"><Clock3 size={24} /><div>Cargando solicitudes...</div></div>
        ) : vacaciones.length === 0 ? (
          <div className="hr-empty">
            <CalendarRange size={28} />
            <div className="hr-empty__title">Sin solicitudes</div>
            <div>Aún no has enviado ninguna solicitud de ausencia.</div>
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
              </tr>
            </thead>
            <tbody>
              {vacaciones.map((v) => (
                <tr key={String(v.id)}>
                  <td>{v.tipo}</td>
                  <td>{formatDate(v.fecha_inicio)}</td>
                  <td>{formatDate(v.fecha_fin)}</td>
                  <td>{v.dias}</td>
                  <td><span className={getStatusBadge(v.estado)}>{v.estado}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
