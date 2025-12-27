/**
 * Field mapping component with:
 * - Auto-detection with confidence
 * - Live preview
 * - Drag & drop
 * - Template management
 */

import React, { useState, useEffect, useMemo } from 'react'
import { getSuggestions, type ColumnSuggestion } from '../utils/levenshtein'
import { getAliasSugeridos } from '../utils/aliasCampos'
import type { EntityTypeConfig } from '../config/entityTypes'
import TemplateManager from './TemplateManager'
import { saveImportTemplate, type ImportTemplate } from '../services/templates'

type Props = {
  headers: string[]
  camposObjetivo: string[]
  mapa: Partial<Record<string, string>>
  onChange: (m: Partial<Record<string, string>>) => void
  sourceType?: string
  previewData?: Record<string, any>[]
  fieldConfig?: EntityTypeConfig
}

export default function MapeoCampos({
  headers,
  camposObjetivo,
  mapa,
  onChange,
  sourceType = 'generic',
  previewData = [],
  fieldConfig,
}: Props) {
  const [suggestions, setSuggestions] = useState<Record<string, ColumnSuggestion[]>>({})
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null)
  const [showTemplateManager, setShowTemplateManager] = useState(false)
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [saving, setSaving] = useState(false)

  const aliasMap = useMemo(() => getAliasSugeridos(fieldConfig), [fieldConfig])

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
    alert(`Template "${template.name}" loaded`)
  }

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      alert('Enter a template name')
      return
    }

    setSaving(true)
    try {
      await saveImportTemplate({
        name: templateName,
        source_type: sourceType,
        mappings: mapa as Record<string, string>,
      })
      alert(`Template "${templateName}" saved`)
      setShowSaveTemplate(false)
      setTemplateName('')
    } catch (err: any) {
      alert(err?.message || 'Error saving template')
    } finally {
      setSaving(false)
    }
  }

  const unmappedFields = camposObjetivo.filter((c) => !mapa[c])
  const previewRows = previewData.slice(0, 3)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Field mapping</h3>
        <div className="flex gap-2">
          <button
            onClick={runAutoDetect}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded text-sm transition"
          >
            Auto-detect
          </button>
          <button
            onClick={() => setShowTemplateManager(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition"
          >
            Load template
          </button>
          <button
            onClick={() => setShowSaveTemplate(true)}
            disabled={Object.keys(mapa).length === 0}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded text-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Save template
          </button>
        </div>
      </div>

      {unmappedFields.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded text-sm">
          {unmappedFields.length} field(s) unmapped: <strong>{unmappedFields.join(', ')}</strong>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {camposObjetivo.map((campo) => {
          const fieldSuggestions = suggestions[campo] || []
          const topSuggestion = fieldSuggestions[0]
          const isMapped = !!mapa[campo]

          return (
            <div
              key={campo}
              className={`border rounded-lg p-3 transition ${
                isMapped ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200 bg-white'
              }`}
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(campo)}
            >
              <label className="block text-sm font-medium mb-2 text-gray-700">
                {campo}
                {isMapped && <span className="ml-2 text-emerald-600">OK</span>}
              </label>

              <select
                className="border border-gray-300 px-3 py-2 rounded w-full text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={mapa[campo] || ''}
                onChange={(e) => onChange({ ...mapa, [campo]: e.target.value })}
              >
                <option value="">-- Select column --</option>
                {headers.map((h) => {
                  const suggestion = fieldSuggestions.find((s) => s.sourceColumn === h)
                  return (
                    <option key={h} value={h}>
                      {h}
                      {suggestion && ` (${suggestion.confidence}% match)`}
                    </option>
                  )
                })}
              </select>

              {!isMapped && topSuggestion && (
                <div className="mt-2 text-xs">
                  <button
                    onClick={() => onChange({ ...mapa, [campo]: topSuggestion.sourceColumn })}
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded transition ${
                      topSuggestion.confidence >= 80
                        ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                        : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                    }`}
                  >
                    Suggested: {topSuggestion.sourceColumn}
                    <span className="font-semibold">({topSuggestion.confidence}%)</span>
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {previewRows.length > 0 && (
        <div className="mt-4">
          <h4 className="font-medium text-sm mb-2">Mapping preview (first 3 rows)</h4>
          <div className="overflow-x-auto border border-gray-200 rounded">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-100">
                <tr>
                  {camposObjetivo.map((campo) => (
                    <th key={campo} className="px-3 py-2 text-left font-medium">
                      {campo}
                      {!mapa[campo] && <span className="text-red-500 ml-1">!</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, idx) => (
                  <tr key={idx} className="border-t">
                    {camposObjetivo.map((campo) => {
                      const sourceCol = mapa[campo]
                      const value = sourceCol ? row[sourceCol] : ''
                      return (
                        <td key={campo} className={`px-3 py-2 ${!value ? 'bg-red-50 text-red-500' : ''}`}>
                          {value || '(empty)'}
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

      <div className="mt-4 border-t pt-4">
        <h4 className="font-medium text-sm mb-2">File columns</h4>
        <div className="flex flex-wrap gap-2">
          {headers.map((header) => (
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
        <p className="text-xs text-gray-500 mt-2">Drag columns to target fields</p>
      </div>

      {showSaveTemplate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">Save template</h3>
            <input
              type="text"
              placeholder="Template name..."
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="w-full border border-gray-300 px-3 py-2 rounded mb-4 focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveTemplate}
                disabled={saving || !templateName.trim()}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded transition disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => {
                  setShowSaveTemplate(false)
                  setTemplateName('')
                }}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <TemplateManager
        isOpen={showTemplateManager}
        onClose={() => setShowTemplateManager(false)}
        onSelect={handleLoadTemplate}
        sourceType={sourceType}
      />
    </div>
  )
}
