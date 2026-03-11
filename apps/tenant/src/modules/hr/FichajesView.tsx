import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Activity, Clock3, LogIn, LogOut, PauseCircle } from 'lucide-react'
import { GcPageHeader } from '@ui'
import { useFichajes } from './hooks/useFichajes'
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

function toMinutes(value?: string) {
  if (!value) return null
  const [hours, minutes] = value.split(':').map(Number)
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null
  return hours * 60 + minutes
}

function formatDuration(start?: string, end?: string) {
  const startMinutes = toMinutes(start)
  const endMinutes = toMinutes(end)
  if (startMinutes === null || endMinutes === null || endMinutes < startMinutes) return 'Abierto'
  const total = endMinutes - startMinutes
  const hours = Math.floor(total / 60)
  const minutes = total % 60
  return `${hours} h ${minutes.toString().padStart(2, '0')} min`
}

function getTypeTone(type: string) {
  if (type === 'trabajo') return 'hr-badge hr-badge--success'
  if (type === 'descanso') return 'hr-badge hr-badge--info'
  return 'hr-badge hr-badge--neutral'
}

function getTypeLabel(type: string) {
  if (type === 'trabajo') return 'Trabajo'
  if (type === 'descanso') return 'Descanso'
  return 'Otro'
}

export default function FichajesView() {
  const { t } = useTranslation(['hr', 'common'])
  const { fichajes, loading } = useFichajes()
  const stats = useMemo(() => {
    const open = fichajes.filter((item) => !item.horaFin).length
    const breaks = fichajes.filter((item) => item.tipo === 'descanso').length
    const closed = fichajes.length - open
    return { open, breaks, closed }
  }, [fichajes])

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <div className="hr-hero__content">
          <GcPageHeader
            badge="Jornada"
            title={t('hr:timekeeping.title')}
            subtitle="Seguimiento de entradas y salidas con foco en registros abiertos, descansos y cierres del dia."
          />
        </div>

        <div className="hr-kpi-grid" style={{ marginTop: '1.25rem' }}>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Registros</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <Activity size={18} />
              </span>
              {fichajes.length}
            </div>
            <div className="hr-kpi-card__hint">Total de fichajes cargados en la vista actual.</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Abiertos</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <LogIn size={18} />
              </span>
              {stats.open}
            </div>
            <div className="hr-kpi-card__hint">Entradas sin salida registrada que conviene revisar.</div>
          </div>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Cerrados</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <LogOut size={18} />
              </span>
              {stats.closed}
            </div>
            <div className="hr-kpi-card__hint">{stats.breaks} movimientos corresponden a descansos.</div>
          </div>
        </div>
      </section>

      <section className="gc-table-wrap">
        <table className="gc-table">
          <thead>
            <tr>
              <th>Empleado</th>
              <th>{t('hr:timekeeping.date')}</th>
              <th>{t('hr:timekeeping.clockIn')}</th>
              <th>{t('hr:timekeeping.clockOut')}</th>
              <th>Duracion</th>
              <th>{t('hr:timekeeping.type')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6}>
                  <div className="hr-empty">
                    <Clock3 size={30} />
                    <div className="hr-empty__title">{t('hr:timekeeping.loading')}</div>
                  </div>
                </td>
              </tr>
            ) : fichajes.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="hr-empty">
                    <PauseCircle size={30} />
                    <div className="hr-empty__title">No hay fichajes disponibles</div>
                    <div>Cuando el equipo registre jornada, aparecera el detalle aqui.</div>
                  </div>
                </td>
              </tr>
            ) : (
              fichajes.map((f) => (
                <tr key={f.id}>
                  <td>
                    <div className="hr-record-cell">
                      <span className="hr-record-cell__title">{f.empleadoId}</span>
                      <span className="hr-record-cell__meta">Registro {f.id.slice(0, 8)}</span>
                    </div>
                  </td>
                  <td>{formatDate(f.fecha)}</td>
                  <td>{f.horaInicio}</td>
                  <td>{f.horaFin ?? 'Pendiente'}</td>
                  <td>{formatDuration(f.horaInicio, f.horaFin)}</td>
                  <td>
                    <span className={getTypeTone(f.tipo)}>{getTypeLabel(f.tipo)}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}
