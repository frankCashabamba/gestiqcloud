// apps/tenant/src/modules/productos/CategoriasModal.tsx
import React, { useEffect, useState } from 'react'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type Categoria = {
  id: string
  name: string
  description?: string
  parent_id?: string | null
}

type CategoriasModalProps = {
  onClose: () => void
  onCategoryCreated?: () => void
}

export default function CategoriasModal({ onClose, onCategoryCreated }: CategoriasModalProps) {
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [loading, setLoading] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newCategoryDesc, setNewCategoryDesc] = useState('')
  const { success, error } = useToast()

  useEffect(() => {
    loadCategorias()
  }, [])

  const loadCategorias = async () => {
    try {
      setLoading(true)
      const data = await apiFetch<Categoria[]>('/api/v1/tenant/products/product-categories')
      console.log('Categorías recibidas:', data)
      setCategorias(Array.isArray(data) ? data : [])
    } catch (e: any) {
      console.error('Error cargando categorías:', e)
      error(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCategoryName.trim()) {
      error('El nombre es obligatorio')
      return
    }

    try {
      await apiFetch('/api/v1/tenant/products/product-categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newCategoryName.trim(),
          description: newCategoryDesc.trim() || null,
        }),
      })
      success('Categoría creada')
      setNewCategoryName('')
      setNewCategoryDesc('')
      loadCategorias()
      onCategoryCreated?.()
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`¿Eliminar categoría "${name}"?`)) return

    try {
      await apiFetch(`/api/v1/tenant/products/product-categories/${id}`, { method: 'DELETE' })
      success('Categoría eliminada')
      loadCategorias()
      onCategoryCreated?.()
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-900">🏷️ Gestión de Categorías</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(80vh-140px)]">
          {/* Formulario Nueva Categoría */}
          <form onSubmit={handleCreate} className="bg-gray-50 rounded-lg p-4 space-y-3">
            <h3 className="font-semibold text-gray-900">Nueva Categoría</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block mb-1 text-sm font-medium text-gray-700">
                  Nombre <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="Ej: Pan, Bollería, Ropa..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block mb-1 text-sm font-medium text-gray-700">Descripción</label>
                <input
                  type="text"
                  value={newCategoryDesc}
                  onChange={(e) => setNewCategoryDesc(e.target.value)}
                  placeholder="Opcional"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
            <button
              type="submit"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              ➕ Crear categoría
            </button>
          </form>

          {/* Lista de Categorías */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">
              Categorías existentes ({categorias.length})
            </h3>

            {loading && (
              <div className="text-center py-8 text-gray-500">Cargando categorías...</div>
            )}

            {!loading && categorias.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No hay categorías. Crea la primera arriba.
              </div>
            )}

            {!loading && categorias.length > 0 && (
              <div className="space-y-2">
                {categorias.map((cat) => (
                  <div
                    key={cat.id}
                    className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div>
                      <div className="font-medium text-gray-900">{cat.name}</div>
                      {cat.description && (
                        <div className="text-xs text-gray-500">{cat.description}</div>
                      )}
                    </div>
                    <button
                      onClick={() => handleDelete(cat.id, cat.name)}
                      className="text-red-600 hover:text-red-800 px-3 py-1 text-sm"
                    >
                      Eliminar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
