/**
 * Versión refactorizada usando GenericList y useCRUD
 * Elimina toda la duplicación de estado y lógica CRUD
 */
import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GenericList, type ColumnConfig, type ActionConfig } from '@crud-components'
import { z } from '@gestiq/mini-zod'
import { useToast } from '../../../shared/toast'

// Schema para validación
const CategoriaGastoSchema = z.object({
  id: z.number(),
  code: z.string(),
  name: z.string(),
  parent_code: z.string().nullable().optional(),
  active: z.boolean()
})

// Manual type definition since infer is causing parsing issues
export interface CategoriaGasto {
  id: number
  code: string
  name: string
  parent_code?: string | null
  active: boolean
}

export default function CategoriaGastoListRefactored() {
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  // Configuración de columnas
  const columns: ColumnConfig<CategoriaGasto>[] = [
    {
      key: 'code',
      label: 'Código',
      sortable: true,
      filterable: true,
      width: '120px'
    },
    {
      key: 'name',
      label: 'Nombre',
      sortable: true,
      filterable: true
    },
    {
      key: 'parent_code',
      label: 'Categoría padre',
      sortable: true,
      filterable: true,
      render: (value) => value || '-'
    },
    {
      key: 'active',
      label: 'Estado',
      sortable: true,
      filterable: true,
      render: (value) => (
        <span className={`px-2 py-1 rounded text-xs ${value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {value ? 'Activo' : 'Inactivo'}
        </span>
      )
    }
  ]

  // Configuración de acciones
  const actions: ActionConfig<CategoriaGasto>[] = [
    {
      key: 'edit',
      label: 'Editar',
      variant: 'primary',
      href: (item) => `${item.id}/editar`
    },
    {
      key: 'delete',
      label: 'Eliminar',
      variant: 'danger',
      onClick: async (item) => {
        if (!confirm('¿Eliminar categoría de gasto?')) return

        try {
          // Usar el método delete del hook CRUD
          await fetch(`/api/v1/admin/categorias-gasto/${item.id}`, {
            method: 'DELETE'
          })
          success('Categoría de gasto eliminada')
        } catch (error) {
          toastError(error instanceof Error ? error.message : 'Error al eliminar')
        }
      }
    }
  ]

  // Callbacks
  const handleSuccess = (action: string, data: any) => {
    if (action === 'delete') {
      success('Categoría de gasto eliminada')
    }
  }

  const handleError = (error: string) => {
    toastError(error)
  }

  const handleNewItem = () => {
    nav('nuevo')
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Categorías de gasto</h2>
        <button
          onClick={handleNewItem}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          Nueva categoría
        </button>
      </div>

      <GenericList<CategoriaGasto>
        endpoint="/api/v1/admin/categorias-gasto"
        schema={CategoriaGastoSchema}
        columns={columns}
        actions={actions}
        title="Categorías de gasto"
        subtitle="Gestiona las categorías de gastos del sistema"
        emptyMessage="No hay categorías de gasto configuradas"
        loadingMessage="Cargando categorías de gasto..."
        errorMessage="Error al cargar las categorías de gasto"
        searchable={true}
        filterable={true}
        sortable={true}
        showPagination={true}
        defaultPerPage={20}
        perPageOptions={[10, 20, 50, 100]}
        onSuccess={handleSuccess}
        onError={handleError}
        className="bg-white rounded-lg shadow"
        headerClassName="border-b border-gray-200 pb-4"
        rowClassName={(item, index) =>
          index % 2 === 0 ? 'bg-gray-50' : 'bg-white'
        }
      />
    </div>
  )
}
