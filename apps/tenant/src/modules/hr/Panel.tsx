import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, CalendarRange, Clock3, Users, Wallet } from 'lucide-react'
import { GcPageHeader } from '@ui'
import './hr.css'

const modules = [
  {
    to: 'empleados',
    eyebrow: 'Equipo',
    title: 'Empleados',
    description: 'Directorio del equipo, contratos, altas y bajas.',
    icon: Users,
    color: '#6366f1',
  },
  {
    to: 'vacations',
    eyebrow: 'Ausencias',
    title: 'Vacaciones y permisos',
    description: 'Solicitudes, aprobaciones y disponibilidad del equipo.',
    icon: CalendarRange,
    color: '#0ea5e9',
  },
  {
    to: 'timekeeping',
    eyebrow: 'Jornada',
    title: 'Control horario',
    description: 'Entradas, salidas y registros abiertos del día.',
    icon: Clock3,
    color: '#f59e0b',
  },
  {
    to: 'payroll',
    eyebrow: 'Nómina',
    title: 'Nóminas',
    description: 'Cierre mensual, confirmación y pago de nóminas.',
    icon: Wallet,
    color: '#10b981',
  },
]

export default function HRPanel() {
  const { t } = useTranslation(['hr', 'common'])

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <div className="hr-hero__content">
          <GcPageHeader
            badge="RRHH"
            title={t('hr:title')}
            subtitle="Ausencias, control horario y cierre de nómina."
          />
        </div>
      </section>

      <section className="hr-panel-grid">
        {modules.map((mod) => {
          const Icon = mod.icon
          return (
            <Link key={mod.to} to={mod.to} className="hr-module-card" style={{ textDecoration: 'none', display: 'grid' }}>
              <div className="hr-module-card__top">
                <div>
                  <div className="hr-module-card__eyebrow">{mod.eyebrow}</div>
                  <h2 className="hr-module-card__title">{mod.title}</h2>
                </div>
                <span className="hr-module-card__icon" style={{ color: mod.color, background: `${mod.color}18` }}>
                  <Icon size={24} />
                </span>
              </div>
              <p className="hr-module-card__description">{mod.description}</p>
              <div className="hr-module-card__actions" style={{ justifyContent: 'flex-end' }}>
                <span className="gc-btn gc-btn--primary" style={{ pointerEvents: 'none' }}>
                  Abrir
                  <ArrowRight size={16} />
                </span>
              </div>
            </Link>
          )
        })}
      </section>
    </div>
  )
}
