import React, { useMemo } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import ImportIntake from '../components/ImportIntake'

export default function ImportPage() {
  const navigate = useNavigate()
  const { t } = useTranslation('importer')
  const [searchParams] = useSearchParams()
  const reimportMode = searchParams.get('reimport')
  const sourceRecipeSnapshotId = searchParams.get('recipeSnapshotId') || ''

  const forceRequested = reimportMode === 'force' || reimportMode === 'fast' || reimportMode === 'deep'
  const initialReprocessMode = useMemo(() => (reimportMode === 'deep' ? 'deep' : 'fast'), [reimportMode])

  if (!forceRequested) {
    return <Navigate to="../documents" replace />
  }

  return (
    <div
      style={{
        padding: '1.5rem',
        width: '100%',
        maxWidth: 1080,
        margin: '0 auto',
        display: 'grid',
        gap: '1rem',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        <button
          onClick={() => navigate('../documents')}
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
          Back to documents
        </button>
      </div>

      <section
        style={{
          borderRadius: 28,
          padding: '1.35rem',
          background: 'linear-gradient(135deg, #fffdf8 0%, #eef6ff 52%, #ffffff 100%)',
          border: '1px solid #e2e8f0',
          boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 30, lineHeight: 1.05, color: '#0f172a' }}>
          {initialReprocessMode === 'deep' ? t('reprocessPage.deepTitle') : t('reprocessPage.fastTitle')}
        </h1>
        <p style={{ margin: '0.55rem 0 0', fontSize: 15, color: '#475569', maxWidth: 780 }}>
          {initialReprocessMode === 'deep' ? t('reprocessPage.deepDescription') : t('reprocessPage.fastDescription')}
        </p>
      </section>

      <div
        style={{
          padding: '0.9rem 1rem',
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 18,
          color: '#1d4ed8',
          fontSize: 14,
        }}
      >
        {initialReprocessMode === 'deep' ? t('reprocessPage.deepNotice') : t('reprocessPage.fastNotice')}
      </div>

      <ImportIntake
        initialForceReprocess={forceRequested}
        initialReprocessMode={initialReprocessMode}
        initialRecipeSnapshotId={sourceRecipeSnapshotId}
        restoreSession={false}
        documentPathBuilder={(docId) => `../documents/${docId}`}
        compact
      />
    </div>
  )
}
