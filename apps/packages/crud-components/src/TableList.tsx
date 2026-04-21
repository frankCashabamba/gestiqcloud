/**
 * TableList - Componente específico para listas en formato tabla
 * Simplificado y sin los problemas de GenericList
 */
import React from 'react'
import { Link } from 'react-router-dom'
import { useCRUD } from '@gestiq/ui-hooks'

// Tipo SchemaValidator local para evitar errores de importación
export interface SchemaValidator<T> {
  parse(data: any): T
}

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

export interface TableListProps<T> {
  // Configuración de datos
  endpoint: string
  schema: SchemaValidator<T>
  
  // Configuración de columnas
  columns: ColumnConfig<T>[]
  
  // Configuración de acciones
  actions?: ActionConfig<T>[]
  
  // Configuración de visualización
  title?: string
  emptyMessage?: string
  loadingMessage?: string
  errorMessage?: string
  
  // Configuración de comportamiento
  searchable?: boolean
  sortable?: boolean
  
  // Callbacks
  onSuccess?: (action: string, data: any) => void
  onError?: (error: string) => void
  
  // Estilos personalizados
  className?: string
  headerClassName?: string
  rowClassName?: (item: T, index: number) => string
}

export function TableList<T = any>({
  endpoint,
  schema,
  columns,
  actions = [],
  title,
  emptyMessage = 'No hay datos disponibles',
  loadingMessage = 'Cargando...',
  errorMessage = 'Error al cargar los datos',
  searchable = true,
  sortable = true,
  onSuccess,
  onError,
  className = '',
  headerClassName = '',
  rowClassName,
}: TableListProps<T>) {
  
  // Hook CRUD para gestión de estado
  const crud = useCRUD<T>({ endpoint, schema, onSuccess, onError })
  
  // Estado local
  const [searchTerm, setSearchTerm] = React.useState('')
  const [sortConfig, setSortConfig] = React.useState<{ sortBy?: string; order?: 'asc' | 'desc' }>({})
  
  // Debounce para search
  React.useEffect(() => {
    const timer = setTimeout(() => {
      // Aquí iría la lógica de búsqueda filtrada
      // Por ahora solo usamos el fetchItems básico
    }, 300)
    
    return () => clearTimeout(timer)
  }, [searchTerm])
  
  // Cargar datos iniciales
  React.useEffect(() => {
    crud.fetchItems()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  
  // Manejadores
  const handleSort = (columnKey: keyof T) => {
    const column = columns.find(col => col.key === columnKey)
    if (!column?.sortable) return
    
    setSortConfig(prev => ({
      sortBy: String(columnKey),
      order: prev.sortBy === String(columnKey) && prev.order === 'asc' ? 'desc' : 'asc'
    }))
  }
  
  const handleAction = (action: ActionConfig<T>, item: T, index: number) => {
    if (action.href) {
      // Navegación via Link - manejada por el render
      return
    }
    action.onClick(item, index)
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
                className={`btn btn-sm ${isDisabled ? 'btn-disabled' : `btn-${action.variant || 'secondary'}`}
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
              className={`btn btn-sm ${isDisabled ? 'btn-disabled' : `btn-${action.variant || 'secondary'}`}
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
      <div className={`table-list loading ${className}`}>
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
      <div className={`table-list error ${className}`}>
        <div className="text-center p-8">
          <div className="error-icon">â ï¸</div>
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
      <div className={`table-list empty ${className}`}>
        <div className="text-center p-8">
          <div className="empty-icon">ð </div>
          <p className="mt-2 text-gray-500">{emptyMessage}</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className={`table-list ${className}`}>
      {/* Header */}
      {title && (
        <div className={`table-list-header ${headerClassName}`}>
          <h2 className="text-xl font-semibold">{title}</h2>
        </div>
      )}
      
      {/* Search */}
      {searchable && (
        <div className="table-list-controls mb-4">
          <input
            type="text"
            placeholder="Buscar..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
      )}
      
      {/* Table */}
      <div className="table-list-table">
        <table className="w-full">
          <thead>
            <tr>
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
                      {sortConfig.order === 'asc' ? 'â ' : 'â¼'}
                    </span>
                  )}
                </th>
              ))}
              
              {actions.length > 0 && <th className="w-32">Acciones</th>}
            </tr>
          </thead>
          
          <tbody>
            {crud.items.map((item, index) => {
              const rowClass = rowClassName?.(item, index) || ''
              
              return (
                <tr
                  key={(item as any).id || index}
                  className={rowClass}
                >
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
    </div>
  )
}
