import React, { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadFile, type HistImport } from '../services'
import PageContainer from '../../../components/PageContainer'

const IMPORT_TYPES = [
  { value: 'sales', label: 'Ventas' },
  { value: 'purchases', label: 'Compras' },
  { value: 'stock', label: 'Stock' },
  { value: 'daily_sales', label: 'Ventas diarias' },
]

const ACCEPTED = '.csv,.xlsx,.xls'

export default function UploadPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [importType, setImportType] = useState('sales')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<HistImport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  const handleFile = (f: File | undefined) => {
    if (f) {
      setFile(f)
      setResult(null)
      setError(null)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    handleFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      const res = await uploadFile(file, importType)
      setResult(res)
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Error al subir el archivo')
    } finally {
      setUploading(false)
    }
  }

  return (
    <PageContainer>
      <div style={{ display: 'grid', gap: '1rem' }}>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <button
          onClick={() => navigate('../imports')}
          style={{
            cursor: 'pointer',
            border: '1px solid #dbe4f0',
            background: '#fff',
            fontSize: 14,
            color: '#0f172a',
            padding: '0.5rem 0.8rem',
            borderRadius: 12,
          }}
        >
          ← Importaciones
        </button>
      </div>

      <section
        style={{
          borderRadius: 28,
          padding: '1.35rem',
          background: 'linear-gradient(135deg, #fffdf8 0%, #f0ecff 52%, #ffffff 100%)',
          border: '1px solid #e2e8f0',
          boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 28, lineHeight: 1.05, color: '#0f172a' }}>
          Subir archivo histórico
        </h1>
        <p style={{ margin: '0.55rem 0 0', fontSize: 15, color: '#475569', maxWidth: 600 }}>
          Carga archivos CSV o Excel con datos de ventas, compras o stock históricos.
        </p>
      </section>

      <div style={{ display: 'grid', gap: '0.8rem' }}>
        <label style={{ fontSize: 14, fontWeight: 700, color: '#334155' }}>
          Tipo de importación
        </label>
        <select
          value={importType}
          onChange={(e) => setImportType(e.target.value)}
          style={{
            padding: '0.6rem 0.8rem',
            border: '1px solid #cbd5e1',
            borderRadius: 10,
            fontSize: 14,
            color: '#0f172a',
            background: '#fff',
          }}
        >
          {IMPORT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? '#8B5CF6' : '#cbd5e1'}`,
          borderRadius: 18,
          padding: '2.5rem 1.5rem',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragging ? '#f5f3ff' : '#fafafa',
          transition: 'all 0.15s',
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 8 }}>📁</div>
        <div style={{ fontSize: 15, color: '#475569', fontWeight: 600 }}>
          {file ? file.name : 'Arrastra un archivo aquí o haz clic para seleccionar'}
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
          Formatos aceptados: CSV, XLSX, XLS
        </div>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED}
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        style={{
          padding: '0.8rem 1.5rem',
          border: 'none',
          borderRadius: 14,
          cursor: file && !uploading ? 'pointer' : 'not-allowed',
          background: file && !uploading
            ? 'linear-gradient(135deg, #7c3aed 0%, #8B5CF6 100%)'
            : '#cbd5e1',
          color: '#fff',
          fontSize: 15,
          fontWeight: 800,
          opacity: file && !uploading ? 1 : 0.6,
        }}
      >
        {uploading ? 'Subiendo...' : 'Subir archivo'}
      </button>

      {result && (
        <div style={{ padding: '1rem', borderRadius: 14, background: '#dcfce7', border: '1px solid #bbf7d0', color: '#166534' }}>
          <strong>Importación creada:</strong> {result.filename} — {result.imported_rows}/{result.total_rows} filas importadas
        </div>
      )}

      {error && (
        <div style={{ padding: '1rem', borderRadius: 14, background: '#fee2e2', border: '1px solid #fca5a5', color: '#991b1b' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      </div>
    </PageContainer>
  )
}
