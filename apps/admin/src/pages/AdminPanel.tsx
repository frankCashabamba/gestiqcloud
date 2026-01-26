// src/pages/AdminPanel.tsx
import React from 'react'
import { useAuthGuard } from '../hooks/useAuthGuard'
import { AdminCard } from '../components/AdminCard'
import { MetricCard } from '../components/MetricCard'
import { SimpleLineChart } from '../components/SimpleLineChart'
import { GenericDashboard } from '../components/GenericDashboard'
import { useAdminStats } from '../hooks/useAdminStats'
import './admin-panel.css'

type Card = {
  nombre: string
  descripcion: string
  icono?: string
  emoji?: string
  url: string
}

const saasCards: Card[] = [
  {
    nombre: 'Empresas',
    descripcion: 'Gestión de empresas registradas',
    icono: '/icons/empresas.png',
    url: 'companies',
  },
  {
    nombre: 'Usuarios Principales',
    descripcion: 'Control de cuentas del sistema',
    icono: '/icons/usuario.png',
    url: 'usuarios',
  },
  {
    nombre: 'Configuración del sistema',
    descripcion: 'Campos, formularios y defaults',
    icono: '/icons/configuracion.jpeg',
    url: 'config',
  },
  {
    nombre: 'Módulos por empresa',
    descripcion: 'Activar o desactivar módulos',
    emoji: '🧩',
    url: 'modulos',
  },
  {
    nombre: 'Migraciones',
    descripcion: 'Ejecutar Render Job de migraciones',
    icono: '/icons/configuracion.jpeg',
    url: 'ops/migraciones',
  },
]

const observabilityCards: Card[] = [
  {
    nombre: 'Logs del Sistema',
    descripcion: 'Auditoría centralizada y exportable',
    emoji: '📋',
    url: 'logs',
  },
  {
    nombre: 'Incidencias',
    descripcion: 'Alertas con IA y auto-resolución',
    emoji: '🚨',
    url: 'incidencias',
  },
]

const operationsCards: Card[] = [
  {
    nombre: 'Importar Empresas',
    descripcion: 'Carga masiva mediante plantillas',
    emoji: '📥',
    url: 'companies/import',
  },
  {
    nombre: 'Create Company',
    descripcion: 'Guided onboarding in minutes',
    emoji: '✨',
    url: 'companies/create',
  },
]

export default function AdminPanel() {
  useAuthGuard('superadmin')
  const { stats, loading: statsLoading, error: statsError, refresh } = useAdminStats()

  const metrics = React.useMemo(() => ([
    {
      title: 'Active companies',
      value: stats?.tenants_activos ?? '—',
      subtitle: stats ? `${stats.tenants_total} total` : '—',
      icon: '🏢',
      color: 'blue' as const,
    },
    {
      title: 'Users',
      value: stats?.usuarios_total ?? '—',
      subtitle: stats ? `${stats.usuarios_activos} active` : '—',
      icon: '👤',
      color: 'green' as const,
    },
    {
      title: 'Módulos',
      value: stats?.modulos_activos ?? '—',
      subtitle: stats ? `${stats.modulos_total} disponibles` : '—',
      icon: '🧩',
      color: 'purple' as const,
    },
    {
      title: 'Migraciones',
      value: stats?.migraciones_aplicadas ?? '—',
      subtitle: stats ? `${stats.migraciones_pendientes} pendientes` : '—',
      icon: '⚙️',
      color: 'orange' as const,
    },
  ]), [stats])

  const latestCompanies = stats?.ultimos_tenants ?? []
  const latestCount = stats?.tenants_por_dia && stats.tenants_por_dia.length
    ? stats.tenants_por_dia[stats.tenants_por_dia.length - 1].count
    : null

  const formatDate = (iso?: string) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  }

  const renderCards = (items: Card[]) => (
    <div className="admin-grid">
      {items.map((item) => (
        <AdminCard
          key={item.url}
          href={item.url.startsWith('/') ? item.url : `/admin/${item.url}`}
          iconSrc={item.icono}
          iconEmoji={item.emoji}
          iconSize="sm"
          title={item.nombre}
          description={item.descripcion}
        />
      ))}
    </div>
  )

  return (
    <div className="admin-container">
      <header className="admin-header-bar">
        <div>
          <h1 className="admin-title">🛠️ Panel de Administración</h1>
          <p className="admin-subtitle">Todo lo necesario para operar, observar y resolver incidencias</p>
        </div>
        <button
          type="button"
          className="admin-refresh"
          onClick={refresh}
          disabled={statsLoading}
        >
          {statsLoading ? 'Actualizando…' : '🔄 Actualizar métricas'}
        </button>
      </header>

      {statsError && (
        <div className="admin-alert" role="alert">
          ⚠️ {statsError}
        </div>
      )}

      <section className="admin-section">
        <h2>📊 Salud del SaaS</h2>
        <div className="metrics-grid">
          {metrics.map((metric) => (
            <MetricCard
              key={metric.title}
              title={metric.title}
              value={metric.value}
              subtitle={metric.subtitle}
              icon={metric.icon}
              color={metric.color}
            />
          ))}
        </div>

        <div className="insights-grid">
          <div className="insight-card">
            <div className="insight-header">
              <div>
                <h3>New tenants (30 days)</h3>
                <p className="insight-helper">
                  Latest record: {latestCount ?? '—'} / day
                </p>
              </div>
            </div>
            {stats?.tenants_por_dia?.length ? (
              <SimpleLineChart data={stats.tenants_por_dia} />
            ) : (
              <div className="insight-empty">Not enough data to show trend.</div>
            )}
          </div>

          <div className="insight-card">
            <div className="insight-header">
              <div>
                <h3>Latest tenants created</h3>
                <p className="insight-helper">Quick on-boarding validation</p>
              </div>
            </div>
            {latestCompanies.length ? (
              <table className="tenants-table">
                <thead>
                  <tr>
                    <th>Empresa</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {latestCompanies.map((tenant) => (
                    <tr key={tenant.id}>
                      <td>{tenant.name}</td>
                      <td>{formatDate(tenant.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="insight-empty">Aún no hay registros recientes.</div>
            )}
          </div>
        </div>
      </section>

      <section className="admin-section">
        <h2>⚙️ Administración del SaaS</h2>
        {renderCards(saasCards)}
      </section>

      <section className="admin-section">
        <h2>🧭 Observabilidad & Incidencias</h2>
        {renderCards(observabilityCards)}
      </section>

      <section className="admin-section">
        <h2>🚀 Operaciones de Soporte</h2>
        {renderCards(operationsCards)}
      </section>

      <section className="admin-section">
        <h2>📱 Dashboard Configurable (Sistema Sin Hardcodes)</h2>
        <GenericDashboard dashboardSlug="default" />
      </section>
    </div>
  )
}
