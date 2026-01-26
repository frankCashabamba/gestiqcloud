/**
 * StatCard Component
 * Displays a single statistic with icon and optional trend
 */

import React from 'react';
import './styles.css';

interface StatCardProps {
  label: string;
  value: number | string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
  color?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  loading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  trend,
  color = 'primary',
  loading = false,
}) => {
  return (
    <div className={`stat-card stat-card--${color}`}>
      {icon && <div className="stat-card__icon">{icon}</div>}
      <div className="stat-card__content">
        <p className="stat-card__label">{label}</p>
        {loading ? (
          <div className="stat-card__skeleton"></div>
        ) : (
          <>
            <p className="stat-card__value">{value}</p>
            {trend && (
              <p className={`stat-card__trend stat-card__trend--${trend.direction}`}>
                {trend.direction === 'up' && '↑'}
                {trend.direction === 'down' && '↓'}
                {trend.direction === 'neutral' && '→'}
                {' '}{Math.abs(trend.value)}%
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
};
