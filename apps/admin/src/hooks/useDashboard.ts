/**
 * Dashboard Hook
 * Manages dashboard data fetching and state
 */

import { useState, useEffect } from 'react';
import {
  getDashboardStats,
  getDashboardKpis,
  DashboardStats,
  DashboardKPIs,
} from '../services/dashboard';

interface UseDashboardReturn {
  stats: DashboardStats | null;
  kpis: DashboardKPIs | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useDashboard(autoRefresh = true, refreshInterval = 30000): UseDashboardReturn {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsData, kpisData] = await Promise.all([
        getDashboardStats(),
        getDashboardKpis(),
      ]);
      setStats(statsData);
      setKpis(kpisData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch dashboard data'));
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    if (!autoRefresh) return;

    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  return {
    stats,
    kpis,
    loading,
    error,
    refetch: fetchData,
  };
}
