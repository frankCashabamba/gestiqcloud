/**
 * Dashboard Page
 * Main admin dashboard with KPIs and analytics
 */

import React, { useState } from 'react';
import { useDashboard } from '../hooks/useDashboard';
import { DashboardStats } from '../features/dashboard/DashboardStats';
import { KpiBoard } from '../features/dashboard/KpiBoard';
import '../features/dashboard/styles.css';
import '../features/dashboard/dashboard-page.css';

export const Dashboard: React.FC = () => {
  const { stats, kpis, loading, error, refetch } = useDashboard(true, 30000);
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refetch();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-page__header">
        <div>
          <h1 className="dashboard-page__title">Dashboard</h1>
          <p className="dashboard-page__subtitle">
            Bienvenido. Aquí tienes una visión general de tu plataforma.
          </p>
        </div>
        <button
          className={`dashboard-page__refresh-btn ${refreshing ? 'is-loading' : ''}`}
          onClick={handleRefresh}
          disabled={refreshing || loading}
          title="Actualizar datos"
        >
          <svg className="dashboard-page__refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Actualizar
        </button>
      </div>

      {error && (
        <div className="dashboard-page__error">
          <p>Error al cargar el dashboard: {error.message}</p>
          <button onClick={handleRefresh} className="dashboard-page__error-retry">
            Reintentar
          </button>
        </div>
      )}

      <DashboardStats data={kpis} loading={loading} />
      <KpiBoard data={kpis} loading={loading} />

      {stats && (
        <div className="dashboard-page__recent">
          <h2 className="dashboard-page__section-title">Últimas Empresas</h2>
          <div className="dashboard-page__companies-grid">
            {stats.ultimos_tenants && stats.ultimos_tenants.length > 0 ? (
              stats.ultimos_tenants.map((tenant) => (
                <div key={tenant.id} className="dashboard-page__company-card">
                  <h3 className="dashboard-page__company-name">{tenant.name}</h3>
                  <p className="dashboard-page__company-date">
                    {new Date(tenant.created_at).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </p>
                </div>
              ))
            ) : (
              <p className="dashboard-page__empty">Sin empresas registradas</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
