/**
 * Admin page for editing sector configurations without deploy
 * FASE 6: Admin UI
 */

import React, { useState, useEffect } from "react"
import { sectorAdminConfigService, type SectorConfig, type UpdateSectorConfigRequest } from "../services/sectorAdminConfig"

export function SectorConfigAdmin() {
  const [sectors, setSectors] = useState<Array<{ code: string; name: string }>>([])
  const [selectedSector, setSelectedSector] = useState<string>("")
  const [config, setConfig] = useState<SectorConfig | null>(null)
  const [editedConfig, setEditedConfig] = useState<SectorConfig["config"] | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const [hasChanges, setHasChanges] = useState(false)

  // Cargar lista de sectores al montar
  useEffect(() => {
    loadSectors()
  }, [])

  const loadSectors = async () => {
    try {
      setLoading(true)
      const data = await sectorAdminConfigService.listSectors()
      setSectors(data)
    } catch (err) {
      showMessage("error", `Error loading sectors: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  const handleSectorChange = async (code: string) => {
    if (hasChanges) {
      if (!window.confirm("You have unsaved changes. Continue anyway?")) {
        return
      }
    }

    setSelectedSector(code)
    setLoading(true)
    setHasChanges(false)

    try {
      const data = await sectorAdminConfigService.getSectorConfig(code)
      setConfig(data)
      setEditedConfig(JSON.parse(JSON.stringify(data.config))) // Deep copy
    } catch (err) {
      showMessage("error", `Error loading config: ${err instanceof Error ? err.message : String(err)}`)
      setConfig(null)
      setEditedConfig(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!editedConfig || !selectedSector) return

    const errors = sectorAdminConfigService.validateConfig(editedConfig)
    if (errors.length > 0) {
      showMessage("error", `Validation errors:\n${errors.join("\n")}`)
      return
    }

    setLoading(true)
    try {
      const result = await sectorAdminConfigService.updateSectorConfig(selectedSector, editedConfig)
      showMessage("success", `✅ Config updated successfully (v${result.version})`)
      setHasChanges(false)

      // Recargar config desde BD
      await handleSectorChange(selectedSector)
    } catch (err) {
      showMessage("error", `Error saving: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    if (!config) return
    setEditedConfig(JSON.parse(JSON.stringify(config.config)))
    setHasChanges(false)
  }

  const handleConfigChange = (newConfig: SectorConfig["config"]) => {
    setEditedConfig(newConfig)
    setHasChanges(true)
  }

  const showMessage = (type: "success" | "error", text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Sector Configuration Editor</h1>
          <p className="text-gray-600">
            Edit sector configurations and see changes instantly without redeploy
          </p>
        </div>

        {/* Messages */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg ${
              message.type === "success"
                ? "bg-green-50 text-green-800 border border-green-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Selector */}
        <div className="mb-6 flex gap-3">
          <select
            value={selectedSector}
            onChange={(e) => handleSectorChange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 font-medium hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a sector...</option>
            {sectors.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>

          <button
            onClick={loadSectors}
            className="px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 font-medium transition"
          >
            Reload Sectors
          </button>
        </div>

        {/* Main editor area */}
        {config && editedConfig && (
          <div className="bg-white rounded-lg shadow-lg">
            {/* Info section */}
            <div className="p-6 border-b border-gray-200 bg-blue-50">
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Sector Code</p>
                  <p className="font-bold text-gray-900">{config.code}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Name</p>
                  <p className="font-bold text-gray-900">{config.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Version</p>
                  <p className="font-bold text-gray-900">v{config.config_version}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Last Updated</p>
                  <p className="font-bold text-gray-900">
                    {config.last_modified
                      ? new Date(config.last_modified).toLocaleString()
                      : "Never"}
                  </p>
                </div>
              </div>
              {config.modified_by && (
                <p className="text-xs text-gray-500 mt-2">Modified by: {config.modified_by}</p>
              )}
            </div>

            {/* JSON Editor */}
            <div className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-bold text-gray-900 mb-2">Configuration JSON</label>
                <textarea
                  value={JSON.stringify(editedConfig, null, 2)}
                  onChange={(e) => {
                    try {
                      const newConfig = JSON.parse(e.target.value)
                      handleConfigChange(newConfig)
                    } catch {
                      // Invalid JSON, just update the display
                      setEditedConfig(JSON.parse(e.target.value))
                    }
                  }}
                  className="w-full h-96 p-4 border border-gray-300 rounded-lg font-mono text-sm bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Changes indicator */}
              {hasChanges && (
                <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm text-amber-800">⚠️ You have unsaved changes</p>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleSave}
                  disabled={!hasChanges || loading}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
                >
                  {loading ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={handleReset}
                  disabled={!hasChanges || loading}
                  className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
                >
                  Discard
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && !config && <div className="text-center text-gray-500">Loading...</div>}

        {/* Empty state */}
        {!selectedSector && !config && (
          <div className="text-center text-gray-500 py-12">Select a sector to get started</div>
        )}
      </div>
    </div>
  )
}
