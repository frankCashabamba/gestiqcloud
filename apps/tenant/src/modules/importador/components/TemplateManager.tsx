/**
 * Modal de gestión de plantillas de mapeo
 */

import React, { useEffect, useState } from 'react'
import {
    listImportTemplates,
    deleteImportTemplate,
    type ImportTemplate
} from '../services/templates'

interface Props {
    isOpen: boolean
    onClose: () => void
    onSelect: (template: ImportTemplate) => void
    sourceType: string
}

export default function TemplateManager({ isOpen, onClose, onSelect, sourceType }: Props) {
    const [templates, setTemplates] = useState<ImportTemplate[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [deletingId, setDeletingId] = useState<string | null>(null)

    useEffect(() => {
        if (isOpen) {
            loadTemplates()
        }
    }, [isOpen, sourceType])

    const loadTemplates = async () => {
        setLoading(true)
        setError(null)
        try {
            const data = await listImportTemplates(sourceType)
            setTemplates(data)
        } catch (err: any) {
            setError(err?.message || 'Error al cargar plantillas')
        } finally {
            setLoading(false)
        }
    }

    const handleDelete = async (id: string, isSystem: boolean) => {
        if (isSystem) {
            alert('No se pueden eliminar plantillas del sistema')
            return
        }

        if (!confirm('¿Eliminar esta plantilla?')) return

        setDeletingId(id)
        try {
            await deleteImportTemplate(id)
            await loadTemplates() // Recargar lista
        } catch (err: any) {
            alert(err?.message || 'Error al eliminar')
        } finally {
            setDeletingId(null)
        }
    }

    const handleSelect = (template: ImportTemplate) => {
        onSelect(template)
        onClose()
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">
                        📋 Plantillas de Mapeo
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition"
                    >
                        ✕
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading && (
                        <div className="text-center py-8 text-gray-600">
                            Cargando plantillas...
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                            {error}
                        </div>
                    )}

                    {!loading && !error && templates.length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                            No hay plantillas disponibles para este tipo de importación.
                            <br />
                            <span className="text-sm">Crea una nueva desde el mapeo de campos.</span>
                        </div>
                    )}

                    {!loading && !error && templates.length > 0 && (
                        <div className="grid md:grid-cols-2 gap-4">
                            {templates.map((template) => (
                                <div
                                    key={template.id}
                                    className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition"
                                >
                                    {/* Nombre */}
                                    <div className="flex items-start justify-between mb-2">
                                        <h4 className="font-semibold text-gray-900">
                                            {template.name}
                                        </h4>
                                        {template.is_system && (
                                            <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded">
                                                Sistema
                                            </span>
                                        )}
                                    </div>

                                    {/* Preview del mapeo */}
                                    <div className="bg-gray-50 rounded p-2 mb-3 text-xs space-y-1 max-h-32 overflow-y-auto">
                                        {Object.entries(template.mappings).map(([target, source]) => (
                                            <div key={target} className="flex items-center gap-2">
                                                <span className="text-gray-600 font-mono">{target}</span>
                                                <span className="text-gray-400">←</span>
                                                <span className="text-gray-900">{source}</span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Acciones */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleSelect(template)}
                                            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition"
                                        >
                                            ✓ Usar Plantilla
                                        </button>

                                        {!template.is_system && (
                                            <button
                                                onClick={() => handleDelete(template.id, template.is_system)}
                                                disabled={deletingId === template.id}
                                                className="bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded text-sm transition disabled:opacity-50"
                                            >
                                                {deletingId === template.id ? '...' : '🗑️'}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <button
                        onClick={onClose}
                        className="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded transition"
                    >
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    )
}
