/**
 * Generic Table Component
 * Renders tables dynamically based on configuration
 * Supports: filtering, sorting, pagination, export
 */

import { useEffect, useState } from "react";
import "./generic-components.css";

interface TableColumn {
  field_name: string;
  label: string;
  data_type: string;
  format?: string;
  sortable: boolean;
  filterable: boolean;
  visible: boolean;
  position: number;
  width?: number;
  align: string;
}

interface TableFilter {
  field_name: string;
  label: string;
  filter_type: string;
  options?: Array<{ label: string; value: string }>;
  default_value?: string;
  placeholder?: string;
}

interface TableAction {
  type: "view" | "edit" | "delete";
  label: string;
  confirmation?: boolean;
  confirmation_message?: string;
}

interface TableConfig {
  id: string;
  slug: string;
  title: string;
  description?: string;
  api_endpoint: string;
  columns: TableColumn[];
  filters?: TableFilter[];
  actions?: TableAction[];
  pagination_size: number;
  sortable: boolean;
  searchable: boolean;
  exportable: boolean;
}

interface GenericTableProps {
  config: TableConfig;
  onAction?: (action: TableAction, row: any) => void;
}

export function GenericTable({ config, onAction }: GenericTableProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [searchTerm, setSearchTerm] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});

  const visibleColumns = config.columns.filter((col) => col.visible);

  useEffect(() => {
    loadTableData();
  }, [page, sortBy, sortOrder, searchTerm, filters, config.api_endpoint]);

  const loadTableData = async () => {
    try {
      setLoading(true);

      const params = new URLSearchParams();
      params.append("skip", ((page - 1) * config.pagination_size).toString());
      params.append("limit", config.pagination_size.toString());

      if (sortBy && config.sortable) {
        params.append("sort_by", sortBy);
        params.append("sort_order", sortOrder);
      }

      if (searchTerm && config.searchable) {
        params.append("search", searchTerm);
      }

      // Add filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(`filter_${key}`, value);
      });

      const url = `${import.meta.env.VITE_API_URL}${config.api_endpoint}?${params}`;
      const response = await fetch(url);

      if (!response.ok) throw new Error("Failed to load table data");

      const result = await response.json();
      setData(Array.isArray(result) ? result : result.items || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error loading table data");
      console.error("Error loading table:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (columnName: string) => {
    if (!config.sortable) return;

    if (sortBy === columnName) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(columnName);
      setSortOrder("asc");
    }
  };

  const handleFilterChange = (fieldName: string, value: string) => {
    setFilters({ ...filters, [fieldName]: value });
    setPage(1);
  };

  const formatCellValue = (col: TableColumn, value: any): string => {
    if (value === null || value === undefined) return "-";

    switch (col.format) {
      case "currency":
        return new Intl.NumberFormat("es-EC", {
          style: "currency",
          currency: "USD",
        }).format(value);
      case "date":
      case "dd/MM/yyyy":
        return new Date(value).toLocaleDateString("es-EC");
      case "percentage":
        return `${(value * 100).toFixed(2)}%`;
      case "badge":
        return `<span class="badge badge-${value}">${value}</span>`;
      default:
        return String(value);
    }
  };

  if (error) {
    return (
      <div className="generic-table error">
        <div className="error-message">{error}</div>
        <button onClick={loadTableData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="generic-table">
      {/* Header */}
      <div className="table-header">
        <div className="table-title">
          <h2>{config.title}</h2>
          {config.description && <p>{config.description}</p>}
        </div>

        <div className="table-controls">
          {/* Search */}
          {config.searchable && (
            <input
              type="text"
              placeholder="Buscar..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              className="search-input"
            />
          )}

          {/* Export */}
          {config.exportable && (
            <button className="btn btn-secondary" onClick={() => exportData()}>
              Exportar
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      {config.filters && config.filters.length > 0 && (
        <div className="table-filters">
          {config.filters.map((filter) => (
            <div key={filter.field_name} className="filter-item">
              <label>{filter.label}</label>
              {filter.filter_type === "select" ? (
                <select
                  value={filters[filter.field_name] || ""}
                  onChange={(e) =>
                    handleFilterChange(filter.field_name, e.target.value)
                  }
                >
                  <option value="">Todos</option>
                  {filter.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={filter.filter_type === "date" ? "date" : "text"}
                  placeholder={filter.placeholder}
                  value={filters[filter.field_name] || ""}
                  onChange={(e) =>
                    handleFilterChange(filter.field_name, e.target.value)
                  }
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="table-wrapper">
        {loading ? (
          <div className="skeleton table-skeleton" style={{ height: "400px" }} />
        ) : data.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                {visibleColumns.map((col) => (
                  <th
                    key={col.field_name}
                    style={{
                      textAlign: col.align as any,
                      width: col.width ? `${col.width}px` : undefined,
                    }}
                    onClick={() => handleSort(col.field_name)}
                    className={col.sortable ? "sortable" : ""}
                  >
                    {col.label}
                    {sortBy === col.field_name && (
                      <span className={`sort-indicator ${sortOrder}`}>
                        {sortOrder === "asc" ? " ↑" : " ↓"}
                      </span>
                    )}
                  </th>
                ))}
                {config.actions && config.actions.length > 0 && (
                  <th>Acciones</th>
                )}
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={row.id || idx}>
                  {visibleColumns.map((col) => (
                    <td
                      key={col.field_name}
                      style={{ textAlign: col.align as any }}
                      dangerouslySetInnerHTML={{
                        __html: formatCellValue(col, row[col.field_name]),
                      }}
                    />
                  ))}
                  {config.actions && config.actions.length > 0 && (
                    <td className="actions-cell">
                      {config.actions.map((action) => (
                        <button
                          key={action.type}
                          className={`btn-action btn-${action.type}`}
                          onClick={() => {
                            if (
                              action.confirmation &&
                              !confirm(
                                action.confirmation_message ||
                                  "¿Estás seguro?"
                              )
                            ) {
                              return;
                            }
                            onAction?.(action, row);
                          }}
                        >
                          {action.label}
                        </button>
                      ))}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="no-data">No hay datos disponibles</div>
        )}
      </div>

      {/* Pagination */}
      {data.length > 0 && (
        <div className="table-pagination">
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="btn btn-sm"
          >
            ← Anterior
          </button>
          <span className="page-info">
            Página {page} | {config.pagination_size} por página
          </span>
          <button onClick={() => setPage(page + 1)} className="btn btn-sm">
            Siguiente →
          </button>
        </div>
      )}
    </div>
  );
}

function exportData() {
  // Implementation for export functionality
  console.log("Export functionality not yet implemented");
}

export default GenericTable;
