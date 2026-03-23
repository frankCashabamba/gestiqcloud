import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Activity, Clock3, LogIn, LogOut, PauseCircle, PlayCircle } from 'lucide-react'
import { GcPageHeader } from '@ui'
import { usePermission } from '../../hooks/usePermission'
import { listEmpleados } from '../../services/api/hr'
import { getErrorMessage, useToast } from '../../shared/toast'
import { useFichajes } from './hooks/useFichajes'
import { actualizarFichaje, registrarFichaje } from './services/fichajes'
import type { Fichaje } from './types/fichaje'
import './hr.css'

type EmployeeSummary = {
  id: string
  name: string
  apellidos?: string
  puesto?: string
  estado?: string
}

type QuickAction = 'clockIn' | 'startBreak' | 'resumeBreak' | 'clockOut'

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

function formatDateTime(dateValue: string, timeValue?: string) {
  if (!timeValue) return formatDate(dateValue)
  const date = new Date(`${dateValue}T${timeValue}`)
  if (Number.isNaN(date.getTime())) return `${formatDate(dateValue)} ${timeValue}`
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
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

function getTypeLabel(t: (key: string) => string, type: string) {
  if (type === 'trabajo') return t('hr:timekeeping.typeWork')
  if (type === 'descanso') return t('hr:timekeeping.typeBreak')
  return t('hr:timekeeping.typeOther')
}

function compareEntriesDesc(left: Fichaje, right: Fichaje) {
  const leftStamp = `${left.fecha}T${left.horaInicio}`
  const rightStamp = `${right.fecha}T${right.horaInicio}`
  return rightStamp.localeCompare(leftStamp)
}

function getNowStamp() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  return {
    fecha: `${year}-${month}-${day}`,
    hora: `${hours}:${minutes}:${seconds}`,
  }
}

export default function FichajesView() {
  const { t } = useTranslation(['hr', 'common'])
  const navigate = useNavigate()
  const { fichajes, loading, reload } = useFichajes()
  const can = usePermission()
  const canManage = can('hr:manage')
  const { success, error: toastError, warning, info } = useToast()

  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [employeesLoading, setEmployeesLoading] = useState(true)
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('')
  const [actionLoading, setActionLoading] = useState<QuickAction | null>(null)
  const [notes, setNotes] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadEmployees() {
      try {
        setEmployeesLoading(true)
        const data = await listEmpleados()
        const items = Array.isArray(data) ? data : data?.items || []
        if (cancelled) return
        setEmployees(items)
        if (!selectedEmployeeId) {
          const activeEmployee = items.find((item: EmployeeSummary) => item.estado === 'activo') || items[0]
          if (activeEmployee?.id) {
            setSelectedEmployeeId(activeEmployee.id)
          }
        }
      } catch (error) {
        if (!cancelled) {
          setEmployees([])
          toastError(getErrorMessage(error))
        }
      } finally {
        if (!cancelled) {
          setEmployeesLoading(false)
        }
      }
    }

    void loadEmployees()

    return () => {
      cancelled = true
    }
  }, [toastError])

  const stats = useMemo(() => {
    const open = fichajes.filter((item) => !item.horaFin).length
    const breaks = fichajes.filter((item) => item.tipo === 'descanso').length
    const closed = fichajes.length - open
    return { open, breaks, closed }
  }, [fichajes])

  const employeeMap = useMemo(() => {
    return employees.reduce<Record<string, EmployeeSummary>>((acc, employee) => {
      acc[employee.id] = employee
      return acc
    }, {})
  }, [employees])

  const activeEmployees = useMemo(
    () => employees.filter((employee) => !employee.estado || employee.estado === 'activo'),
    [employees]
  )

  const selectedEmployee = selectedEmployeeId ? employeeMap[selectedEmployeeId] : undefined

  const selectedEntries = useMemo(() => {
    return fichajes
      .filter((item) => item.empleadoId === selectedEmployeeId)
      .sort(compareEntriesDesc)
  }, [fichajes, selectedEmployeeId])

  const openEntry = useMemo(() => {
    return selectedEntries.find((item) => !item.horaFin) || null
  }, [selectedEntries])

  const lastEntry = selectedEntries[0] || null

  const currentStatus = openEntry?.tipo === 'descanso'
    ? t('hr:timekeeping.statusOnBreak')
    : openEntry
      ? t('hr:timekeeping.statusWorking')
      : t('hr:timekeeping.statusOff')

  async function executeQuickAction(action: QuickAction) {
    if (!selectedEmployeeId) {
      warning(t('hr:timekeeping.employeeRequired'))
      return
    }

    const { fecha, hora } = getNowStamp()
    setActionLoading(action)

    try {
      if (action === 'clockIn') {
        if (openEntry) {
          info(t('hr:timekeeping.alreadyOpen'))
          return
        }
        await registrarFichaje({
          empleadoId: selectedEmployeeId,
          fecha,
          horaInicio: hora,
          tipo: 'trabajo',
          notas: notes || undefined,
        })
        success(t('hr:timekeeping.successClockIn'))
      }

      if (action === 'startBreak') {
        if (!openEntry || openEntry.tipo !== 'trabajo') {
          warning(t('hr:timekeeping.openWorkRequired'))
          return
        }
        await actualizarFichaje(openEntry.id, {
          horaFin: hora,
          notas: notes || undefined,
        })
        await registrarFichaje({
          empleadoId: selectedEmployeeId,
          fecha,
          horaInicio: hora,
          tipo: 'descanso',
          notas: notes || undefined,
        })
        success(t('hr:timekeeping.successStartBreak'))
      }

      if (action === 'resumeBreak') {
        if (!openEntry || openEntry.tipo !== 'descanso') {
          warning(t('hr:timekeeping.openBreakRequired'))
          return
        }
        await actualizarFichaje(openEntry.id, {
          horaFin: hora,
          notas: notes || undefined,
        })
        await registrarFichaje({
          empleadoId: selectedEmployeeId,
          fecha,
          horaInicio: hora,
          tipo: 'trabajo',
          notas: notes || undefined,
        })
        success(t('hr:timekeeping.successResume'))
      }

      if (action === 'clockOut') {
        if (!openEntry) {
          warning(t('hr:timekeeping.noOpenEntry'))
          return
        }
        await actualizarFichaje(openEntry.id, {
          horaFin: hora,
          notas: notes || undefined,
        })
        success(t('hr:timekeeping.successClockOut'))
      }

      setNotes('')
      await reload()
    } catch (error) {
      toastError(getErrorMessage(error))
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <div className="hr-hero__content">
          <GcPageHeader
            badge="Jornada"
            title={t('hr:timekeeping.title')}
            subtitle={t('hr:timekeeping.subtitle')}
            onBack={() => navigate(-1)}
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

      <section className="hr-quick-grid">
        <article className="hr-status-card">
          <div className="hr-status-card__eyebrow">{t('hr:timekeeping.currentStatus')}</div>
          <div className="hr-status-card__value">{currentStatus}</div>
          <div className="hr-status-card__meta">
            {selectedEmployee ? `${selectedEmployee.name} ${selectedEmployee.apellidos || ''}`.trim() : t('hr:timekeeping.noEmployees')}
          </div>
          {openEntry ? (
            <div className="hr-status-card__hint">
              {t('hr:timekeeping.openSince')}: {formatDateTime(openEntry.fecha, openEntry.horaInicio)}
            </div>
          ) : lastEntry ? (
            <div className="hr-status-card__hint">
              {t('hr:timekeeping.lastMovement')}: {getTypeLabel(t, lastEntry.tipo)} · {formatDateTime(lastEntry.fecha, lastEntry.horaInicio)}
            </div>
          ) : (
            <div className="hr-status-card__hint">{t('hr:timekeeping.noOpenEntry')}</div>
          )}
        </article>

        <article className="hr-toolbar">
          <div className="hr-table-meta">
            <div>
              <div className="hr-kpi-card__label">{t('hr:timekeeping.quickTitle')}</div>
              <div className="hr-table-note">{t('hr:timekeeping.quickHint')}</div>
            </div>
            {!canManage && <span className="hr-badge hr-badge--neutral">{t('hr:timekeeping.manageHint')}</span>}
          </div>

          <div className="hr-toolbar-grid">
            <label className="hr-field">
              <span className="hr-field__label">{t('hr:timekeeping.employee')}</span>
              <select
                value={selectedEmployeeId}
                onChange={(event) => setSelectedEmployeeId(event.target.value)}
                className="gc-input gc-select"
                disabled={employeesLoading}
              >
                <option value="">{employeesLoading ? t('hr:timekeeping.loadingEmployees') : t('hr:timekeeping.employeePlaceholder')}</option>
                {activeEmployees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {[employee.name, employee.apellidos].filter(Boolean).join(' ')}
                  </option>
                ))}
              </select>
            </label>

            <label className="hr-field hr-field--wide">
              <span className="hr-field__label">{t('hr:timekeeping.notes')}</span>
              <input
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                className="gc-input"
                placeholder={t('hr:timekeeping.notesPlaceholder')}
                maxLength={255}
              />
            </label>
          </div>

          <div className="hr-actions-row">
            <button
              type="button"
              className="gc-btn gc-btn--primary"
              onClick={() => void executeQuickAction('clockIn')}
              disabled={!canManage || actionLoading !== null || !selectedEmployeeId || Boolean(openEntry)}
            >
              <LogIn size={16} />
              {actionLoading === 'clockIn' ? t('hr:timekeeping.actionRunning') : t('hr:timekeeping.actionClockIn')}
            </button>
            <button
              type="button"
              className="gc-btn gc-btn--ghost"
              onClick={() => void executeQuickAction('startBreak')}
              disabled={!canManage || actionLoading !== null || openEntry?.tipo !== 'trabajo'}
            >
              <PauseCircle size={16} />
              {actionLoading === 'startBreak' ? t('hr:timekeeping.actionRunning') : t('hr:timekeeping.actionStartBreak')}
            </button>
            <button
              type="button"
              className="gc-btn gc-btn--ghost"
              onClick={() => void executeQuickAction('resumeBreak')}
              disabled={!canManage || actionLoading !== null || openEntry?.tipo !== 'descanso'}
            >
              <PlayCircle size={16} />
              {actionLoading === 'resumeBreak' ? t('hr:timekeeping.actionRunning') : t('hr:timekeeping.actionResume')}
            </button>
            <button
              type="button"
              className="gc-btn gc-btn--danger"
              onClick={() => void executeQuickAction('clockOut')}
              disabled={!canManage || actionLoading !== null || !openEntry}
            >
              <LogOut size={16} />
              {actionLoading === 'clockOut' ? t('hr:timekeeping.actionRunning') : t('hr:timekeeping.actionClockOut')}
            </button>
          </div>
        </article>
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
              fichajes.map((f) => {
                const employee = employeeMap[f.empleadoId]
                const employeeName = employee
                  ? [employee.name, employee.apellidos].filter(Boolean).join(' ')
                  : f.empleadoId

                return (
                  <tr key={f.id}>
                    <td>
                      <div className="hr-record-cell">
                        <span className="hr-record-cell__title">{employeeName}</span>
                        <span className="hr-record-cell__meta">Registro {f.id.slice(0, 8)}</span>
                      </div>
                    </td>
                    <td>{formatDate(f.fecha)}</td>
                    <td>{f.horaInicio}</td>
                    <td>{f.horaFin ?? 'Pendiente'}</td>
                    <td>{formatDuration(f.horaInicio, f.horaFin)}</td>
                    <td>
                      <span className={getTypeTone(f.tipo)}>{getTypeLabel(t, f.tipo)}</span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}
