/**
 * Generic Widget Component
 * Dynamically renders widgets based on type from config
 * Supported types: stat_card, chart, table, form
 */

import { useEffect, useState } from "react";
import { apiClient } from "../services/api";

interface WidgetConfig {
  id: string;
  widget_type: "stat_card" | "chart" | "table" | "form";
  title?: string;
  description?: string;
  config: Record<string, any>;
  api_endpoint?: string;
  refresh_interval?: number;
  active: boolean;
}

interface GenericWidgetProps {
  widget: WidgetConfig;
}

export function GenericWidget({ widget }: GenericWidgetProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWidgetData();

    // Set up auto-refresh if interval is specified
    let interval: ReturnType<typeof setInterval> | null = null;
    if (widget.refresh_interval && widget.refresh_interval > 0) {
      interval = setInterval(loadWidgetData, widget.refresh_interval * 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [widget.api_endpoint, widget.refresh_interval]);

  const loadWidgetData = async () => {
    if (!widget.api_endpoint) {
      setData(widget.config);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}${widget.api_endpoint}`
      );
      if (!response.ok) throw new Error("Failed to load widget data");
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error loading data");
      console.error(`Error loading widget ${widget.id}:`, err);
    } finally {
      setLoading(false);
    }
  };

  if (!widget.active) {
    return <div className="widget-inactive">Widget is inactive</div>;
  }

  if (error) {
    return (
      <div className="widget widget-error">
        <h3>{widget.title}</h3>
        <div className="error">{error}</div>
        <button onClick={loadWidgetData}>Retry</button>
      </div>
    );
  }

  // Render based on widget type
  switch (widget.widget_type) {
    case "stat_card":
      return renderStatCard(widget, data, loading);
    case "chart":
      return renderChart(widget, data, loading);
    case "table":
      return renderTable(widget, data, loading);
    case "form":
      return renderForm(widget, data, loading);
    default:
      return (
        <div className="widget widget-unknown">
          Unknown widget type: {widget.widget_type}
        </div>
      );
  }
}

function renderStatCard(widget: WidgetConfig, data: any, loading: boolean) {
  const { metric, icon = "📊", color = "blue" } = widget.config;

  return (
    <div className={`widget stat-card stat-card-${color}`}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-content">
        {widget.title && <h3>{widget.title}</h3>}
        {loading ? (
          <div className="stat-value skeleton">-</div>
        ) : (
          <div className="stat-value">{data?.[metric] ?? "-"}</div>
        )}
        {widget.description && (
          <p className="stat-description">{widget.description}</p>
        )}
      </div>
    </div>
  );
}

function renderChart(widget: WidgetConfig, data: any, loading: boolean) {
  return (
    <div className="widget chart-widget">
      {widget.title && <h3>{widget.title}</h3>}
      {loading ? (
        <div className="skeleton chart-skeleton" style={{ height: "250px" }} />
      ) : data ? (
        <div className="chart-content">
          {/* Chart implementation would go here */}
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      ) : (
        <p>No data available</p>
      )}
    </div>
  );
}

function renderTable(widget: WidgetConfig, data: any, loading: boolean) {
  return (
    <div className="widget table-widget">
      {widget.title && <h3>{widget.title}</h3>}
      {loading ? (
        <div className="skeleton table-skeleton" style={{ height: "300px" }} />
      ) : data && Array.isArray(data) && data.length > 0 ? (
        <table className="data-table">
          <thead>
            <tr>
              {Object.keys(data[0]).map((key) => (
                <th key={key}>{key}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row: any, idx: number) => (
              <tr key={idx}>
                {Object.values(row).map((val: any, i: number) => (
                  <td key={i}>{String(val)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No data available</p>
      )}
    </div>
  );
}

function renderForm(widget: WidgetConfig, data: any, loading: boolean) {
  return (
    <div className="widget form-widget">
      {widget.title && <h3>{widget.title}</h3>}
      {loading ? (
        <div className="skeleton form-skeleton" style={{ height: "200px" }} />
      ) : (
        <div className="form-content">
          {/* Form implementation would go here */}
          <p>Form widget - configure via form schema</p>
        </div>
      )}
    </div>
  );
}

export default GenericWidget;
