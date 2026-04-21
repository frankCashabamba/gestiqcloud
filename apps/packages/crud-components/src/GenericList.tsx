/**
 * Componente GenericList - Lista configurable para cualquier tipo de datos
 */
import React from 'react'
import { Link } from 'react-router-dom'
import { useCRUD, usePagination, useFilters } from '@gestiq/ui-hooks'

export interface ColumnConfig<T> {
  key: keyof T
  label: string
  sortable?: boolean
  filterable?: boolean
  render?: (value: any, item: T, index: number) => React.ReactNode
  width?: string
  align?: 'left' | 'center' | 'right'
}

export interface ActionConfig<T> {
  key: string
  label: string
  icon?: React.ReactNode
  onClick: (item: T, index: number) => void
  disabled?: (item: T) => boolean
  variant?: 'primary' | 'secondary' | 'danger'
  href?: (item: T) => string
}

export interface SortConfig {
  sortBy?: string
  order?: 'asc' | 'desc'
}

export interface GenericListProps<T> {
  // Configuración de datos
  endpoint: string
  schema: any // ZodSchema<T>

  // Configuración de columnas
  columns: ColumnConfig<T>[]

  // Configuración de acciones
  actions?: ActionConfig<T>[]
  bulkActions?: ActionConfig<T>[]

  // Configuración de visualización
  title?: string
  subtitle?: string
  emptyMessage?: string
  loadingMessage?: string
  errorMessage?: string

  // Configuración de comportamiento
  searchable?: boolean
  filterable?: boolean
  sortable?: boolean
  showPagination?: boolean
  selectable?: boolean

  // Configuración de paginación
  defaultPerPage?: number
  perPageOptions?: number[]

  // Callbacks
  onItemClick?: (item: T, index: number) => void
  onSelectionChange?: (selectedItems: T[]) => void
  onSuccess?: (action: string, data: any) => void
  onError?: (error: string) => void

  // Estilos personalizados
  className?: string
  headerClassName?: string
  rowClassName?: (item: T, index: number) => string

  // Estado inicial
  initialFilters?: Record<string, any>
  initialSort?: SortConfig
}

export function GenericList<T = any>({
  endpoint,
  schema,
  columns,
  actions = [],
  bulkActions = [],
  title,
  subtitle,
  emptyMessage = 'No hay datos disponibles',
  loadingMessage = 'Cargando...',
  errorMessage = 'Error al cargar los datos',
  searchable = true,
  filterable = true,
  sortable = true,
  showPagination = true,
  selectable = false,
  defaultPerPage = 20,
  perPageOptions = [10, 20, 50, 100],
  onItemClick,
  onSelectionChange,
  onSuccess,
  onError,
  className = '',
  headerClassName = '',
  rowClassName,
  initialFilters = {},
  initialSort = {}
}: GenericListProps<T>) {

  // Hooks para gestión de estado
  const crud = useCRUD<T>({ endpoint, schema, onSuccess, onError })
  const pagination = usePagination({ initialPerPage: defaultPerPage })
  const filters = useFilters({ initialFilters })

  // Estado local
  const [selectedItems, setSelectedItems] = React.useState<T[]>([])
  const [sortConfig, setSortConfig] = React.useState<SortConfig>(initialSort)
  const [searchTerm, setSearchTerm] = React.useState('')

  // Debounce implementation con cleanup proper para evitar memory leaks
  React.useEffect(() => {
    const timer = setTimeout(() => {
      filters.setSearch(searchTerm)
    }, 300)

    // Cleanup function para cancelar el timer si el componente se unmount
    // o si searchTerm cambia antes de que el timer se ejecute
    return () => clearTimeout(timer)
  }, [searchTerm, filters.setSearch])

  // Cargar datos cuando cambian filtros, paginación u ordenamiento
  React.useEffect(() => {
    const params = {
      page: pagination.page,
      perPage: pagination.perPage,
      sortBy: sortConfig.sortBy,
      order: sortConfig.order,
      filters: {
        ...filters.getFilterParams()
      }
    }

    crud.fetchItems(params)
  }, [pagination.page, pagination.perPage, sortConfig.sortBy, sortConfig.order, filters.filters, filters.search])

  // Manejadores
  const handleSort = (columnKey: keyof T) => {
    const column = columns.find(col => col.key === columnKey)
    if (!column?.sortable) return

    setSortConfig(prev => ({
      sortBy: String(columnKey),
      order: prev.sortBy === String(columnKey) && prev.order === 'asc' ? 'desc' : 'asc'
    }))
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedItems(crud.items)
      onSelectionChange?.(crud.items)
    } else {
      setSelectedItems([])
      onSelectionChange?.([])
    }
  }

  const handleSelectItem = (item: T, checked: boolean) => {
    if (checked) {
      const newSelected = [...selectedItems, item]
      setSelectedItems(newSelected)
      onSelectionChange?.(newSelected)
    } else {
      const newSelected = selectedItems.filter(i => i !== item)
      setSelectedItems(newSelected)
      onSelectionChange?.(newSelected)
    }
  }

  const handleAction = (action: ActionConfig<T>, item: T, index: number) => {
    if (action.href) {
      // Navegación via Link
      return
    }
    action.onClick(item, index)
  }

  const handleBulkAction = (action: ActionConfig<T>) => {
    action.onClick(selectedItems, 0)
  }

  // Render functions
  const renderCell = (item: T, column: ColumnConfig<T>, index: number) => {
    const value = item[column.key]

    if (column.render) {
      return column.render(value, item, index)
    }

    // Renderizado por defecto
    if (value === null || value === undefined) {
      return <span className="text-gray-400">-</span>
    }

    return <span>{String(value)}</span>
  }

  const renderActions = (item: T, index: number) => {
    if (actions.length === 0) return null

    return (
      <div className="flex gap-2">
        {actions.map(action => {
          const isDisabled = action.disabled?.(item) ?? false

          if (action.href) {
            return (
              <Link
                key={action.key}
                to={action.href(item)}
                className={`btn btn-sm ${isDisabled ? 'btn-disabled' : `btn-${action.variant || 'secondary'}`}`}
                onClick={() => !isDisabled && handleAction(action, item, index)}
              >
                {action.icon}
                {action.label}
              </Link>
            )
          }

          return (
            <button
              key={action.key}
              className={`btn btn-sm ${isDisabled ? 'btn-disabled' : `btn-${action.variant || 'secondary'}`}`}
              onClick={() => !isDisabled && handleAction(action, item, index)}
              disabled={isDisabled}
            >
              {action.icon}
              {action.label}
            </button>
          )
        })}
      </div>
    )
  }

  // Loading state
  if (crud.loading) {
    return (
      <div className={`generic-list loading ${className}`}>
        <div className="text-center p-8">
          <div className="spinner"></div>
          <p className="mt-2">{loadingMessage}</p>
        </div>
      </div>
    )
  }

  // Error state
  if (crud.error) {
    return (
      <div className={`generic-list error ${className}`}>
        <div className="text-center p-8">
          <div className="error-icon">⚠️</div>
          <p className="mt-2 text-red-600">{errorMessage}</p>
          <button
            className="btn btn-primary mt-4"
            onClick={() => crud.refreshItems()}
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  // Empty state
  if (crud.items.length === 0) {
    return (
      <div className={`generic-list empty ${className}`}>
        <div className="text-center p-8">
          <div className="empty-icon">📋</div>
          <p className="mt-2 text-gray-500">{emptyMessage}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`generic-list ${className}`}>
      {/* Header */}
      {(title || subtitle) && (
        <div className={`generic-list-header ${headerClassName}`}>
          {title && <h2 className="text-xl font-semibold">{title}</h2>}
          {subtitle && <p className="text-gray-600 mt-1">{subtitle}</p>}
        </div>
      )}

      {/* Search and Filters */}
      {(searchable || filterable) && (
        <div className="generic-list-controls mb-4">
          {searchable && (
            <input
              type="text"
              placeholder="Buscar..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          )}

          {filterable && filters.activeFilters.length > 0 && (
            <div className="active-filters">
              {filters.activeFilters.map(key => (
                <span key={key} className="filter-tag">
                  {key}: {filters.filters[key]}
                  <button onClick={() => filters.removeFilter(key)}>×</button>
                </span>
              ))}
              <button onClick={filters.clearFilters} className="clear-filters">
                Limpiar filtros
              </button>
            </div>
          )}
        </div>
      )}

      {/* Bulk Actions */}
      {selectable && bulkActions.length > 0 && selectedItems.length > 0 && (
        <div className="bulk-actions mb-4">
          <span className="selected-count">
            {selectedItems.length} seleccionados
          </span>
          {bulkActions.map(action => (
            <button
              key={action.key}
              className={`btn btn-sm btn-${action.variant || 'secondary'}`}
              onClick={() => handleBulkAction(action)}
            >
              {action.icon}
              {action.label}
            </button>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="generic-list-table">
        <table className="w-full">
          <thead>
            <tr>
              {selectable && (
                <th className="w-12">
                  <input
                    type="checkbox"
                    checked={selectedItems.length === crud.items.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  />
                </th>
              )}

              {columns.map(column => (
                <th
                  key={String(column.key)}
                  className={`
                    ${column.sortable ? 'sortable' : ''}
                    ${column.align || 'left'}
                  `}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  {column.label}
                  {sortable && sortConfig.sortBy === String(column.key) && (
                    <span className="sort-indicator">
                      {sortConfig.order === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </th>
              ))}

              {actions.length > 0 && <th className="w-32">Acciones</th>}
            </tr>
          </thead>

          <tbody>
            {crud.items.map((item, index) => {
              const isSelected = selectedItems.includes(item)
              const rowClass = rowClassName?.(item, index) || ''

              return (
                <tr
                  key={(item as any).id || index}
                  className={`
                    ${isSelected ? 'selected' : ''}
                    ${rowClass}
                    ${onItemClick ? 'clickable' : ''}
                  `}
                  onClick={() => onItemClick?.(item, index)}
                >
                  {selectable && (
                    <td>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => handleSelectItem(item, e.target.checked)}
                      />
                    </td>
                  )}

                  {columns.map(column => (
                    <td
                      key={String(column.key)}
                      className={column.align || 'left'}
                    >
                      {renderCell(item, column, index)}
                    </td>
                  ))}

                  {actions.length > 0 && (
                    <td>
                      {renderActions(item, index)}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {showPagination && crud.pagination.pages > 1 && (
        <div className="generic-list-pagination mt-4">
          <div className="pagination-info">
            Mostrando {crud.items.length} de {crud.pagination.total} resultados
          </div>

          <div className="pagination-controls">
            <button
              onClick={pagination.firstPage}
              disabled={pagination.page === 1}
              className="btn btn-sm"
            >
              Primera
            </button>

            <button
              onClick={pagination.prevPage}
              disabled={pagination.page === 1}
              className="btn btn-sm"
            >
              Anterior
            </button>

            <span className="page-info">
              Página {pagination.page} de {pagination.pages}
            </span>

            <button
              onClick={pagination.nextPage}
              disabled={pagination.page === pagination.pages}
              className="btn btn-sm"
            >
              Siguiente
            </button>

            <button
              onClick={pagination.lastPage}
              disabled={pagination.page === pagination.pages}
              className="btn btn-sm"
            >
              Última
            </button>
          </div>

          <select
            value={pagination.perPage}
            onChange={(e) => pagination.setPerPage(Number(e.target.value))}
            className="per-page-select"
          >
            {perPageOptions.map(option => (
              <option key={option} value={option}>
                {option} por página
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}
