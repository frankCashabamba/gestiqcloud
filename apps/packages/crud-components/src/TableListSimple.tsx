/**
 * TableListSimple - Componente específico para listas en formato tabla
 * Simplificado y sin los problemas de GenericList
 */
import React from 'react'
import { Link } from 'react-router-dom'

export interface ColumnConfig<T> {
  key: keyof T
  label: string
  sortable?: boolean
  render?: (value: any, item: T, index: number) => React.ReactNode
  width?: string
  align?: 'left' | 'center' | 'right'
}

export interface ActionConfig<T> {
  key: string
  label: string
  onClick: (item: T, index: number) => void
  disabled?: (item: T) => boolean
  variant?: 'primary' | 'secondary' | 'danger'
  href?: (item: T) => string
}

export interface TableListSimpleProps<T> {
  // Configuración de datos
  items: T[]
  loading?: boolean
  error?: string | null

  // Configuración de columnas
  columns: ColumnConfig<T>[]

  // Configuración de acciones
  actions?: ActionConfig<T>[]

  // Configuración de visualización
  title?: string
  emptyMessage?: string
  loadingMessage?: string
  errorMessage?: string

  // Estilos personalizados
  className?: string
  headerClassName?: string
  rowClassName?: (item: T, index: number) => string
}

export function TableListSimple<T = any>({
  items,
  loading = false,
  error = null,
  columns,
  actions = [],
  title,
  emptyMessage = 'No hay datos disponibles',
  loadingMessage = 'Cargando...',
  errorMessage = 'Error al cargar los datos',
  className = '',
  headerClassName = '',
  rowClassName,
}: TableListSimpleProps<T>) {

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
                className={`text-blue-600 hover:text-blue-900 ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {action.label}
              </Link>
            )
          }

          return (
            <button
              key={action.key}
              className={`text-sm ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''} ${
                action.variant === 'danger' ? 'text-red-600 hover:text-red-900' :
                action.variant === 'primary' ? 'text-blue-600 hover:text-blue-900' :
                'text-gray-600 hover:text-gray-900'
              }`}
              onClick={() => !isDisabled && action.onClick(item, index)}
              disabled={isDisabled}
            >
              {action.label}
            </button>
          )
        })}
      </div>
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className={`table-list-simple loading ${className}`}>
        <div className="text-center p-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">{loadingMessage}</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className={`table-list-simple error ${className}`}>
        <div className="text-center p-8">
          <div className="text-red-600 text-lg mb-4">Error</div>
          <p className="mt-2 text-red-600">{errorMessage}</p>
        </div>
      </div>
    )
  }

  // Empty state
  if (items.length === 0) {
    return (
      <div className={`table-list-simple empty ${className}`}>
        <div className="text-center p-8">
          <div className="text-gray-400 text-6xl mb-4">List</div>
          <p className="mt-2 text-gray-500">{emptyMessage}</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`table-list-simple ${className}`}>
      {/* Header */}
      {title && (
        <div className={`table-list-simple-header ${headerClassName}`}>
          <h2 className="text-xl font-semibold">{title}</h2>
        </div>
      )}

      {/* Table */}
      <div className="table-list-simple-table bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map(column => (
                <th
                  key={String(column.key)}
                  className={`
                    px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider
                    ${column.align === 'center' ? 'text-center' : ''}
                    ${column.align === 'right' ? 'text-right' : ''}
                  `}
                  style={{ width: column.width }}
                >
                  {column.label}
                </th>
              ))}

              {actions.length > 0 && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                  Acciones
                </th>
              )}
            </tr>
          </thead>

          <tbody className="bg-white divide-y divide-gray-200">
            {items.map((item, index) => {
              const rowClass = rowClassName?.(item, index) || ''

              return (
                <tr
                  key={(item as any).id || index}
                  className={`${rowClass} hover:bg-gray-50`}
                >
                  {columns.map(column => (
                    <td
                      key={String(column.key)}
                      className={`
                        px-6 py-4 whitespace-nowrap text-sm
                        ${column.align === 'center' ? 'text-center' : ''}
                        ${column.align === 'right' ? 'text-right' : ''}
                      `}
                    >
                      {renderCell(item, column, index)}
                    </td>
                  ))}

                  {actions.length > 0 && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
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
