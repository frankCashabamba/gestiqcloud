import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ImportUploader from '../components/ImportUploader'

const VIDEO_URL = 'https://www.youtube.com/embed/REEMPLAZA_ESTE_ID?autoplay=1&rel=0&modestbranding=1'
const STORAGE_KEY = 'importador_intro_dismissed'

export default function UploadPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const reimportMode = searchParams.get('reimport')
  const sourceDocumentId = searchParams.get('documentId')
  const forceRequested = reimportMode === 'clean' || reimportMode === 'force'

  const [showVideo, setShowVideo] = useState(
    () => localStorage.getItem(STORAGE_KEY) !== 'true'
  )

  function dismissVideo() {
    localStorage.setItem(STORAGE_KEY, 'true')
    setShowVideo(false)
  }

  return (
    <div style={{ padding: '1.5rem', maxWidth: 1080, display: 'grid', gap: '1rem' }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          width: 'fit-content',
          cursor: 'pointer',
          border: '1px solid #dbe4f0',
          background: '#fff',
          fontSize: 14,
          color: '#0f172a',
          padding: '0.5rem 0.8rem',
          borderRadius: 12,
          boxShadow: '0 8px 18px rgba(15, 23, 42, 0.04)',
        }}
      >
        {'<-'} Volver
      </button>

      <section
        style={{
          borderRadius: 28,
          padding: '1.35rem',
          background: 'linear-gradient(135deg, #fffdf8 0%, #eef6ff 52%, #ffffff 100%)',
          border: '1px solid #e2e8f0',
          boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#0f766e', marginBottom: 6 }}>
          Entrada de documentos
        </div>
        <h1 style={{ margin: 0, fontSize: 30, lineHeight: 1.05, color: '#0f172a' }}>Subir archivos al importador</h1>
        <p style={{ margin: '0.55rem 0 0', fontSize: 15, color: '#475569', maxWidth: 780 }}>
          Carga facturas, imagenes, hojas de calculo y otros documentos compatibles. El sistema los prepara para revision y luego podras guardarlos en su destino.
        </p>
      </section>

      {showVideo && (
        <section
          style={{
            borderRadius: 20,
            overflow: 'hidden',
            border: '1px solid #e2e8f0',
            boxShadow: '0 8px 24px rgba(15, 23, 42, 0.07)',
            background: '#000',
            position: 'relative',
          }}
        >
          <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0 }}>
            <iframe
              src={VIDEO_URL}
              title="Cómo usar el importador"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{
                position: 'absolute',
                top: 0, left: 0,
                width: '100%', height: '100%',
                border: 'none',
              }}
            />
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              alignItems: 'center',
              padding: '0.6rem 1rem',
              background: '#f8fafc',
              borderTop: '1px solid #e2e8f0',
              gap: '0.5rem',
            }}
          >
            <span style={{ fontSize: 13, color: '#64748b' }}>
              ¿Ya entendiste cómo funciona?
            </span>
            <button
              onClick={dismissVideo}
              style={{
                cursor: 'pointer',
                border: '1px solid #cbd5e1',
                background: '#fff',
                fontSize: 13,
                color: '#0f172a',
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                fontWeight: 600,
              }}
            >
              No volver a mostrar
            </button>
          </div>
        </section>
      )}

      {forceRequested && (
        <div
          style={{
            padding: '0.95rem 1rem',
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: 18,
            color: '#1d4ed8',
            fontSize: 14,
          }}
        >
          <div style={{ fontWeight: 800 }}>Modo volver a procesar</div>
          <div style={{ marginTop: 4 }}>
            Vuelve a subir el archivo original para revisar de nuevo ese documento sin crear duplicados
            {sourceDocumentId ? ` (${sourceDocumentId}).` : '.'}
          </div>
        </div>
      )}

      <ImportUploader
        initialForceReprocess={forceRequested}
        documentPathBuilder={(docId) => `../documents/${docId}`}
      />
    </div>
  )
}
