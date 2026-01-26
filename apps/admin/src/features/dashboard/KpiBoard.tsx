/**
 * KPI Board Component
 * Displays KPIs by company and trends
 */

import React from 'react';
import { DashboardKPIs } from '../../services/dashboard';
import './styles.css';

interface KpiBoardProps {
  data: DashboardKPIs | null;
  loading?: boolean;
}

export const KpiBoard: React.FC<KpiBoardProps> = ({ data, loading = false }) => {
  if (!data) return null;

  return (
    <div className="kpi-board">
      <div className="kpi-board__section">
        <h3 className="kpi-board__title">Métodos por Empresa</h3>
        {loading ? (
          <div className="kpi-board__skeleton"></div>
        ) : (
          <div className="kpi-board__table">
            <div className="kpi-board__table-head">
              <div className="kpi-board__table-cell">Empresa</div>
              <div className="kpi-board__table-cell">Métodos</div>
            </div>
            {data.metodos_por_empresa && data.metodos_por_empresa.length > 0 ? (
              data.metodos_por_empresa.map((item, idx) => (
                <div key={idx} className="kpi-board__table-row">
                  <div className="kpi-board__table-cell">{item.empresa_nombre}</div>
                  <div className="kpi-board__table-cell">{item.metodos}</div>
                </div>
              ))
            ) : (
              <div className="kpi-board__empty">Sin datos disponibles</div>
            )}
          </div>
        )}
      </div>

      <div className="kpi-board__section">
        <h3 className="kpi-board__title">Tendencias Mensuales</h3>
        {loading ? (
          <div className="kpi-board__skeleton"></div>
        ) : (
          <div className="kpi-board__table">
            <div className="kpi-board__table-head">
              <div className="kpi-board__table-cell">Mes</div>
              <div className="kpi-board__table-cell">Transacciones</div>
              <div className="kpi-board__table-cell">Ingresos</div>
            </div>
            {data.tendencias_mensuales && data.tendencias_mensuales.length > 0 ? (
              data.tendencias_mensuales.map((item, idx) => (
                <div key={idx} className="kpi-board__table-row">
                  <div className="kpi-board__table-cell">{item.mes}</div>
                  <div className="kpi-board__table-cell">{item.transacciones}</div>
                  <div className="kpi-board__table-cell">${item.ingresos.toFixed(2)}</div>
                </div>
              ))
            ) : (
              <div className="kpi-board__empty">Sin datos disponibles</div>
            )}
          </div>
        )}
      </div>

      <div className="kpi-board__section">
        <h3 className="kpi-board__title">Indicadores de Rendimiento</h3>
        {loading ? (
          <div className="kpi-board__skeleton"></div>
        ) : (
          <div className="kpi-board__metrics">
            <div className="kpi-board__metric">
              <span className="kpi-board__metric-label">Disponibilidad</span>
              <div className="kpi-board__metric-bar">
                <div
                  className="kpi-board__metric-fill"
                  style={{ width: `${data.performance_indicators?.uptime || 0}%` }}
                ></div>
              </div>
              <span className="kpi-board__metric-value">{data.performance_indicators?.uptime || 0}%</span>
            </div>
            <div className="kpi-board__metric">
              <span className="kpi-board__metric-label">Tiempo de Respuesta</span>
              <span className="kpi-board__metric-value">{data.performance_indicators?.response_time || 0}ms</span>
            </div>
            <div className="kpi-board__metric">
              <span className="kpi-board__metric-label">Tasa de Errores</span>
              <div className="kpi-board__metric-bar">
                <div
                  className="kpi-board__metric-fill kpi-board__metric-fill--danger"
                  style={{ width: `${data.performance_indicators?.error_rate || 0}%` }}
                ></div>
              </div>
              <span className="kpi-board__metric-value">{data.performance_indicators?.error_rate || 0}%</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
