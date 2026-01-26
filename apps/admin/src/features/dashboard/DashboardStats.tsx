/**
 * Dashboard Stats Section
 * Displays KPI cards
 */

import React from 'react';
import { StatCard } from './StatCard';
import { DashboardKPIs } from '../../services/dashboard';
import './styles.css';

interface DashboardStatsProps {
  data: DashboardKPIs | null;
  loading?: boolean;
}

export const DashboardStats: React.FC<DashboardStatsProps> = ({ data, loading = false }) => {
  return (
    <div className="dashboard-stats">
      <h2 className="dashboard-stats__title">Indicadores Clave</h2>
      <div className="dashboard-stats__grid">
        <StatCard
          label="Total de Empresas"
          value={data?.total_empresas ?? 0}
          color="primary"
          loading={loading}
          icon={
            <svg className="stat-card__svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m5 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1" />
            </svg>
          }
        />
        <StatCard
          label="Usuarios Activos"
          value={data?.usuarios_activos ?? 0}
          color="success"
          loading={loading}
          icon={
            <svg className="stat-card__svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 12H9m6 0a8 8 0 11-16 0 8 8 0 0116 0z" />
            </svg>
          }
        />
        <StatCard
          label="Transacciones Hoy"
          value={data?.transacciones_hoy ?? 0}
          color="info"
          loading={loading}
          icon={
            <svg className="stat-card__svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          }
        />
        <StatCard
          label="Incidentes Pendientes"
          value={data?.incidentes_sin_resolver ?? 0}
          color="warning"
          loading={loading}
          icon={
            <svg className="stat-card__svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          label="Pagos Pendientes"
          value={data?.pagos_pendientes ?? 0}
          color="danger"
          loading={loading}
          icon={
            <svg className="stat-card__svg" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>
    </div>
  );
};
