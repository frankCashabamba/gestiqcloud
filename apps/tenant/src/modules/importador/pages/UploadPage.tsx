import React from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ImportUploader from '../components/ImportUploader'

export default function UploadPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const reimportMode = searchParams.get('reimport')
  const forceRequested = reimportMode === 'clean' || reimportMode === 'force'

  return (
    <div style={{ padding: '1.5rem', maxWidth: 860 }}>
      <button
        onClick={() => navigate(-1)}
        style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#6366F1' }}
      >
        {'<-'} Volver
      </button>
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ margin: 0 }}>Importar Documentos Contables</h2>
      </div>

      {forceRequested && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: 8, color: '#1d4ed8', fontSize: 13 }}>
          Reimportacion limpia activada. Vuelve a subir el archivo original; si no eliges una plantilla manual, se reprocesara con prompt generico y sin reutilizar auto-plantillas previas para sesgar la clasificacion.
        </div>
      )}

      <ImportUploader
        initialForceReprocess={forceRequested}
        documentPathBuilder={(docId) => `../documents/${docId}`}
      />
    </div>
  )
}
