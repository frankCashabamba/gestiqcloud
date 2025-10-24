/**
 * Excel Importer - Importador de archivos Excel SPEC-1
 */
import React, { useState, useRef } from 'react'
import { importExcel, getImportTemplate, type ImportResult } from './services'

export default function ExcelImporter() {
  const [file, setFile] = useState<File | null>(null)
  const [fechaManual, setFechaManual] = useState('')
  const [simulateSales, setSimulateSales] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls')) {
        setError('Solo se aceptan archivos Excel (.xlsx, .xls)')
        return
      }
      setFile(selectedFile)
      setError(null)
      setResult(null)
    }
  }

  const handleImport = async () => {
    if (!file) {
      setError('Por favor selecciona un archivo')
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      const importResult = await importExcel(file, fechaManual || undefined, simulateSales)
      setResult(importResult)
      
      // Limpiar formulario si fue exitoso
      if (importResult.success) {
        setFile(null)
        setFechaManual('')
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }
    } catch (err: any) {
      setError(err.message || 'Error al importar archivo')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const template = await getImportTemplate()
      // Mostrar info del template
      alert(JSON.stringify(template, null, 2))
    } catch (err: any) {
      setError(err.message || 'Error al obtener plantilla')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Importador Excel</h1>
        <p className="mt-1 text-sm text-slate-500">
          Importa registros de producción y ventas desde archivos Excel
        </p>
      </div>

      {/* Info Card */}
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
        <div className="flex gap-3">
          <svg className="h-5 w-5 flex-shrink-0 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm text-blue-800">
            <p className="font-medium">Formato esperado:</p>
            <ul className="mt-2 list-inside list-disc space-y-1">
              <li>Hoja "REGISTRO" con columnas: PRODUCTO, CANTIDAD, VENTA DIARIA, SOBRANTE DIARIO, PRECIO UNITARIO VENTA</li>
              <li>Nombre de archivo con fecha: dd-mm-aaaa.xlsx (ej: 22-10-2025.xlsx)</li>
              <li>Si no incluye fecha en el nombre, usar el campo "Fecha Manual" abajo</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Upload Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="space-y-4">
          {/* File Input */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Archivo Excel
            </label>
            <div className="mt-2 flex items-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-500
                  file:mr-4 file:rounded-lg file:border-0
                  file:bg-blue-50 file:px-4 file:py-2
                  file:text-sm file:font-medium
                  file:text-blue-700 hover:file:bg-blue-100"
              />
              <button
                onClick={handleDownloadTemplate}
                className="flex-shrink-0 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Info Formato
              </button>
            </div>
            {file && (
              <p className="mt-2 text-sm text-slate-600">
                Archivo seleccionado: <span className="font-medium">{file.name}</span> ({(file.size / 1024).toFixed(2)} KB)
              </p>
            )}
          </div>

          {/* Fecha Manual */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Fecha Manual (opcional)
            </label>
            <input
              type="date"
              value={fechaManual}
              onChange={(e) => setFechaManual(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-slate-500">
              Solo usar si el nombre del archivo no incluye la fecha
            </p>
          </div>

          {/* Simulate Sales */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="simulate_sales"
              checked={simulateSales}
              onChange={(e) => setSimulateSales(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="simulate_sales" className="ml-2 text-sm text-slate-700">
              Simular ventas (crea documentos de venta para POS/Reportes)
            </label>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleImport}
              disabled={!file || loading}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {loading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Importando...
                </>
              ) : (
                <>
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Importar Archivo
                </>
              )}
            </button>
            
            {result && (
              <button
                onClick={() => {
                  setResult(null)
                  setError(null)
                }}
                className="rounded-lg border border-slate-300 px-6 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Nuevo
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <div className="flex gap-3">
            <svg className="h-5 w-5 flex-shrink-0 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm text-red-800">
              <p className="font-medium">Error</p>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className={`rounded-xl border p-6 ${result.success ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
          <div className="flex items-start gap-3">
            {result.success ? (
              <svg className="h-6 w-6 flex-shrink-0 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="h-6 w-6 flex-shrink-0 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            )}
            
            <div className="flex-1">
              <h3 className={`text-lg font-semibold ${result.success ? 'text-green-900' : 'text-amber-900'}`}>
                {result.success ? 'Importación Exitosa' : 'Importación con Advertencias'}
              </h3>
              <p className={`mt-1 text-sm ${result.success ? 'text-green-700' : 'text-amber-700'}`}>
                Archivo: {result.filename}
              </p>

              {/* Stats Grid */}
              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg bg-white p-3 shadow-sm">
                  <p className="text-xs font-medium text-slate-500">Productos</p>
                  <p className="mt-1 text-2xl font-bold text-slate-900">
                    {result.stats.products_created + result.stats.products_updated}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {result.stats.products_created} nuevos
                  </p>
                </div>

                <div className="rounded-lg bg-white p-3 shadow-sm">
                  <p className="text-xs font-medium text-slate-500">Compras</p>
                  <p className="mt-1 text-2xl font-bold text-blue-600">
                    {result.stats.purchases_created || 0}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Registros de compra
                  </p>
                </div>

                <div className="rounded-lg bg-white p-3 shadow-sm">
                  <p className="text-xs font-medium text-slate-500">Registros Leche</p>
                  <p className="mt-1 text-2xl font-bold text-purple-600">
                    {result.stats.milk_records_created || 0}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Entradas de leche
                  </p>
                </div>

                <div className="rounded-lg bg-white p-3 shadow-sm">
                  <p className="text-xs font-medium text-slate-500">Inventario Diario</p>
                  <p className="mt-1 text-2xl font-bold text-green-600">
                    {result.stats.daily_inventory_created}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Registros históricos
                  </p>
                </div>
              </div>

              {/* Errors */}
              {result.stats.errors.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-red-700">Errores ({result.stats.errors.length}):</p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-red-600">
                    {result.stats.errors.slice(0, 5).map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                    {result.stats.errors.length > 5 && (
                      <li className="font-medium">... y {result.stats.errors.length - 5} más</li>
                    )}
                  </ul>
                </div>
              )}

              {/* Warnings */}
              {result.stats.warnings.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-amber-700">Advertencias ({result.stats.warnings.length}):</p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-amber-600">
                    {result.stats.warnings.slice(0, 5).map((warn, idx) => (
                      <li key={idx}>{warn}</li>
                    ))}
                    {result.stats.warnings.length > 5 && (
                      <li className="font-medium">... y {result.stats.warnings.length - 5} más</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
