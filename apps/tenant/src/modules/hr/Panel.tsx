import React from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarRange,
  CheckCircle2,
  Clock3,
  ShieldCheck,
  Wallet,
} from 'lucide-react'
import { GcPageHeader } from '@ui'
import './hr.css'

export default function HRPanel() {
  const { t } = useTranslation(['hr', 'common'])
  const modules = [
    {
      to: 'vacations',
      eyebrow: 'Ausencias',
      title: t('hr:panel.vacations'),
      description:
        'Gestiona solicitudes, aprobaciones y seguimiento de permisos con una vista operativa clara.',
      footnote: 'Control semanal de disponibilidad del equipo.',
      icon: CalendarRange,
      bullets: [
        'Solicitudes pendientes y aprobadas en un solo flujo',
        'Decision rapida para responsables de area',
      ],
    },
    {
      to: 'timekeeping',
      eyebrow: 'Jornada',
      title: t('hr:panel.timekeeping'),
      description:
        'Supervisa entradas, salidas y registros abiertos para detectar incidencias de manera inmediata.',
      footnote: 'Seguimiento diario de presencia y cierres.',
      icon: Clock3,
      bullets: [
        'Vista de fichajes abiertos y cerrados',
        'Lectura rapida por fecha, empleado y tipo de registro',
      ],
    },
    {
      to: 'payroll',
      eyebrow: 'Cierre mensual',
      title: t('hr:panel.payroll'),
      description:
        'Centraliza la generacion, confirmacion y pago de nominas con indicadores listos para revision.',
      footnote: 'Proceso mensual con trazabilidad de estado.',
      icon: Wallet,
      bullets: [
        'Resumen economico por corrida de nomina',
        'Acciones directas para confirmar y pagar',
      ],
    },
  ]

  return (
    <div className="hr-shell">
      <section className="hr-hero">
        <div className="hr-hero__content">
          <GcPageHeader
            badge="RRHH"
            title={t('hr:title')}
            subtitle="Centro operativo para ausencias, control horario y cierre de nomina."
          />
        </div>

        <div className="hr-kpi-grid" style={{ marginTop: '1.25rem' }}>
          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Cobertura</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <BriefcaseBusiness size={18} />
              </span>
              3 flujos clave
            </div>
            <div className="hr-kpi-card__hint">Vacaciones, fichajes y nomina en el mismo espacio.</div>
          </div>

          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Supervision</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <ShieldCheck size={18} />
              </span>
              Vista ejecutiva
            </div>
            <div className="hr-kpi-card__hint">Jerarquia visual, acciones visibles y lectura rapida.</div>
          </div>

          <div className="hr-kpi-card">
            <div className="hr-kpi-card__label">Operacion</div>
            <div className="hr-kpi-card__value">
              <span className="hr-kpi-card__icon">
                <CheckCircle2 size={18} />
              </span>
              Modo profesional
            </div>
            <div className="hr-kpi-card__hint">Cada entrada tiene resumen, tabla y acciones prioritarias.</div>
          </div>
        </div>
      </section>

      <section className="hr-panel-grid">
        {modules.map((module) => {
          const Icon = module.icon
          return (
            <article key={module.to} className="hr-module-card">
              <div className="hr-module-card__top">
                <div>
                  <div className="hr-module-card__eyebrow">{module.eyebrow}</div>
                  <h2 className="hr-module-card__title">{module.title}</h2>
                </div>
                <span className="hr-module-card__icon">
                  <Icon size={22} />
                </span>
              </div>

              <p className="hr-module-card__description">{module.description}</p>

              <ul className="hr-module-card__list">
                {module.bullets.map((bullet) => (
                  <li key={bullet}>
                    <CheckCircle2 size={15} />
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>

              <div className="hr-module-card__actions">
                <span className="hr-module-card__footnote">{module.footnote}</span>
                <Link to={module.to} className="gc-btn gc-btn--primary">
                  Entrar
                  <ArrowRight size={16} />
                </Link>
              </div>
            </article>
          )
        })}
      </section>

      <section className="hr-summary-grid">
        <article className="hr-info-card">
          <h3 className="hr-info-card__title">Revision de las 3 entradas</h3>
          <p className="hr-info-card__text">
            Vacaciones queda enfocada en aprobacion, Fichajes en control de jornada y Nominas en cierre
            mensual. La portada ahora separa responsabilidades y evita el aspecto de listado basico.
          </p>
        </article>

        <article className="hr-info-card">
          <h3 className="hr-info-card__title">Criterio aplicado</h3>
          <p className="hr-info-card__text">
            Se priorizo claridad operativa, jerarquia visual y accesos directos, sin romper las rutas ni el
            flujo existente del modulo.
          </p>
        </article>
      </section>
    </div>
  )
}
