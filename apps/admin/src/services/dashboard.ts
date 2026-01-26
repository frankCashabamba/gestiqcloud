/**
 * Dashboard Service
 * Handles all dashboard-related API calls
 */

import apiClient from './api';

export interface DashboardStats {
  tenants_activos: number;
  tenants_total: number;
  usuarios_total: number;
  usuarios_activos: number;
  modulos_activos: number;
  modulos_total: number;
  migraciones_aplicadas: number;
  migraciones_pendientes: number;
  tenants_por_dia: Array<{ fecha: string; count: number }>;
  ultimos_tenants: Array<{
    id: string;
    name: string;
    created_at: string;
  }>;
}

export interface DashboardKPIs {
  total_empresas: number;
  usuarios_activos: number;
  transacciones_hoy: number;
  incidentes_sin_resolver: number;
  pagos_pendientes: number;
  metodos_por_empresa: Array<{
    empresa_id: string;
    empresa_nombre: string;
    metodos: number;
  }>;
  tendencias_mensuales: Array<{
    mes: string;
    transacciones: number;
    ingresos: number;
  }>;
  performance_indicators: {
    uptime: number;
    response_time: number;
    error_rate: number;
  };
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiClient.dashboard.getStats();
}

export async function getDashboardKpis(): Promise<DashboardKPIs> {
  return apiClient.dashboard.getKpis();
}

export async function refreshDashboardData() {
  const [stats, kpis] = await Promise.all([
    getDashboardStats(),
    getDashboardKpis(),
  ]);
  return { stats, kpis };
}
