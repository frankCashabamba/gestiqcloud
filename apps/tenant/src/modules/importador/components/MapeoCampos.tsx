/**
 * Componente mejorado de mapeo de campos con:
 * - Auto-detección inteligente con % de confianza
 * - Preview en vivo de mapeo
 * - Drag & Drop de columnas
 * - Gestión de plantillas
 */

import React, { useState, useEffect, useMemo } from 'react'
import { getSuggestions, type ColumnSuggestion } from '../utils/levenshtein'
import { getAliasSugeridos } from '../utils/aliasCampos'
import TemplateManager from './TemplateManager'
import { saveImportTemplate, type ImportTemplate } from '../services/templates'

type Props = {
    headers: string[]
    camposObjetivo: string[]
    mapa: Partial<Record<string, string>>
    onChange: (m: Partial<Record<string, string>>) => void
    sourceType?: string
    previewData?: Record<string, any>[]
}

export default function MapeoCampos({
    headers,
    camposObjetivo,
    mapa,
    onChange,
    sourceType = 'generico',
    previewData = []
}: Props) {
    const [suggestions, setSuggestions] = useState<Record<string, ColumnSuggestion[]>>({})
    const [draggedColumn, setDraggedColumn] = useState<string | null>(null)
    const [showTemplateManager, setShowTemplateManager] = useState(false)
    const [showSaveTemplate, setShowSaveTemplate] = useState(false)
    const [templateName, setTemplateName] = useState('')
    const [saving, setSaving] = useState(false)

    const aliasMap = useMemo(() => getAliasSugeridos(), [])

    // Auto-detectar al montar o cambiar headers
    useEffect(() => {
        runAutoDetect()
    }, [headers, camposObjetivo])

    const runAutoDetect = () => {
        const newSuggestions: Record<string, ColumnSuggestion[]> = {}
        const newMapa: Record<string, string> = {}

        for (const campo of camposObjetivo) {
            const aliases = aliasMap[campo] || []
            const fieldSuggestions = getSuggestions(campo, headers, aliases)
            newSuggestions[campo] = fieldSuggestions

            // Auto-seleccionar si confianza >= 80%
            if (fieldSuggestions.length > 0 && fieldSuggestions[0].confidence >= 80) {
                newMapa[campo] = fieldSuggestions[0].sourceColumn
            }
        }

        setSuggestions(newSuggestions)
        onChange({ ...mapa, ...newMapa })
    }

    const handleDragStart = (column: string) => {
        setDraggedColumn(column)
    }

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
    }

    const handleDrop = (targetField: string) => {
        if (draggedColumn) {
            onChange({ ...mapa, [targetField]: draggedColumn })
            setDraggedColumn(null)
        }
    }

    const handleLoadTemplate = (template: ImportTemplate) => {
        onChange(template.mappings)
        alert(`✓ Plantilla "${template.name}" cargada`)
    }

    const handleSaveTemplate = async () => {
        if (!templateName.trim()) {
            alert('Ingresa un nombre para la plantilla')
            return
        }

        setSaving(true)
        try {
            await saveImportTemplate({
                name: templateName,
                source_type: sourceType,
                mappings: mapa as Record<string, string>
            })
            alert(`✓ Plantilla "${templateName}" guardada`)
            setShowSaveTemplate(false)
            setTemplateName('')
        } catch (err: any) {
            alert(err?.message || 'Error al guardar')
        } finally {
            setSaving(false)
        }
    }

    const unmappedFields = camposObjetivo.filter(c => !mapa[c])
    const previewRows = previewData.slice(0, 3)

    return (
        <div className="space-y-4">
            {/* Header con acciones */}
            <div className="flex items-center justify-between">
                <h3 className="font-semibold text-lg">📊 Mapeo de Campos</h3>
                <div className="flex gap-2">
                    <button
                        onClick={runAutoDetect}
                        className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded text-sm transition"
                    >
                        🔍 Auto-detectar
                    </button>
                    <button
                        onClick={() => setShowTemplateManager(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition"
                    >
                        📋 Cargar Plantilla
                    </button>
                    <button
                        onClick={() => setShowSaveTemplate(true)}
                        disabled={Object.keys(mapa).length === 0}
                        className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded text-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        💾 Guardar Plantilla
                    </button>
                </div>
            </div>

            {/* Alerta de campos sin mapear */}
            {unmappedFields.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded text-sm">
                    ⚠️ {unmappedFields.length} campo(s) sin mapear: <strong>{unmappedFields.join(', ')}</strong>
                </div>
            )}

            {/* Grid de mapeo */}
            <div className="grid md:grid-cols-2 gap-4">
                {camposObjetivo.map((campo) => {
                    const fieldSuggestions = suggestions[campo] || []
                    const topSuggestion = fieldSuggestions[0]
                    const isMapped = !!mapa[campo]

                    return (
                        <div
                            key={campo}
                            className={`border rounded-lg p-3 transition ${isMapped
                                    ? 'border-green-300 bg-green-50'
                                    : 'border-gray-200 bg-white'
                                }`}
                            onDragOver={handleDragOver}
                            onDrop={() => handleDrop(campo)}
                        >
                            {/* Campo objetivo */}
                            <label className="block text-sm font-medium mb-2 text-gray-700">
                                {campo}
                                {isMapped && <span className="ml-2 text-green-600">✓</span>}
                            </label>

                            {/* Selector */}
                            <select
                                className="border border-gray-300 px-3 py-2 rounded w-full text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                value={mapa[campo] || ''}
                                onChange={(e) => onChange({ ...mapa, [campo]: e.target.value })}
                            >
                                <option value="">-- Seleccionar columna --</option>
                                {headers.map((h) => {
                                    const suggestion = fieldSuggestions.find(s => s.sourceColumn === h)
                                    return (
                                        <option key={h} value={h}>
                                            {h}
                                            {suggestion && ` (${suggestion.confidence}% coincidencia)`}
                                        </option>
                                    )
                                })}
                            </select>

                            {/* Sugerencia */}
                            {!isMapped && topSuggestion && (
                                <div className="mt-2 text-xs">
                                    <button
                                        onClick={() => onChange({ ...mapa, [campo]: topSuggestion.sourceColumn })}
                                        className={`inline-flex items-center gap-1 px-2 py-1 rounded transition ${topSuggestion.confidence >= 80
                                                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                                : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                                            }`}
                                    >
                                        💡 Sugerido: {topSuggestion.sourceColumn}
                                        <span className="font-semibold">({topSuggestion.confidence}%)</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Preview en vivo */}
            {previewRows.length > 0 && (
                <div className="mt-4">
                    <h4 className="font-medium text-sm mb-2">👁️ Preview del Mapeo (3 filas)</h4>
                    <div className="overflow-x-auto border border-gray-200 rounded">
                        <table className="min-w-full text-xs">
                            <thead className="bg-gray-100">
                                <tr>
                                    {camposObjetivo.map(campo => (
                                        <th key={campo} className="px-3 py-2 text-left font-medium">
                                            {campo}
                                            {!mapa[campo] && <span className="text-red-500 ml-1">❌</span>}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {previewRows.map((row, idx) => (
                                    <tr key={idx} className="border-t">
                                        {camposObjetivo.map(campo => {
                                            const sourceCol = mapa[campo]
                                            const value = sourceCol ? row[sourceCol] : ''
                                            return (
                                                <td
                                                    key={campo}
                                                    className={`px-3 py-2 ${!value ? 'bg-red-50 text-red-500' : ''}`}
                                                >
                                                    {value || '(vacío)'}
                                                </td>
                                            )
                                        })}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Columnas disponibles (drag source) */}
            <div className="mt-4 border-t pt-4">
                <h4 className="font-medium text-sm mb-2">📋 Columnas del Archivo</h4>
                <div className="flex flex-wrap gap-2">
                    {headers.map(header => (
                        <div
                            key={header}
                            draggable
                            onDragStart={() => handleDragStart(header)}
                            className="bg-gray-100 hover:bg-gray-200 border border-gray-300 px-3 py-1.5 rounded text-sm cursor-move transition"
                        >
                            {header}
                        </div>
                    ))}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                    💡 Arrastra las columnas a los campos destino
                </p>
            </div>

            {/* Modal guardar plantilla */}
            {showSaveTemplate && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                        <h3 className="text-lg font-semibold mb-4">💾 Guardar Plantilla</h3>
                        <input
                            type="text"
                            placeholder="Nombre de la plantilla..."
                            value={templateName}
                            onChange={(e) => setTemplateName(e.target.value)}
                            className="w-full border border-gray-300 px-3 py-2 rounded mb-4 focus:ring-2 focus:ring-blue-500"
                            autoFocus
                        />
                        <div className="flex gap-2">
                            <button
                                onClick={handleSaveTemplate}
                                disabled={saving || !templateName.trim()}
                                className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded transition disabled:opacity-50"
                            >
                                {saving ? 'Guardando...' : 'Guardar'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowSaveTemplate(false)
                                    setTemplateName('')
                                }}
                                className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded transition"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal gestor de plantillas */}
            <TemplateManager
                isOpen={showTemplateManager}
                onClose={() => setShowTemplateManager(false)}
                onSelect={handleLoadTemplate}
                sourceType={sourceType}
            />
        </div>
    )
}
