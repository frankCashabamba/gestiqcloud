import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchFileSupportConfig, runImportAsync, type FileSupportConfig } from '../services'

type Props = {
  onUploaded?: () => void
}

type UploadFile = {
  file: File
  key: string
}

function prettySize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`
}

export default function QuickUploadPanel({ onUploaded }: Props) {
  const { t } = useTranslation('importer')
  const [support, setSupport] = useState<FileSupportConfig | null>(null)
  const [files, setFiles] = useState<UploadFile[]>([])
  const [dragging, setDragging] = useState(false)
  const [loadingSupport, setLoadingSupport] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let mounted = true
    void fetchFileSupportConfig()
      .then((data) => {
        if (!mounted) return
        setSupport(data)
      })
      .catch(() => {
        if (!mounted) return
        setError(t('uploadWorkspace.errorMissingSupport'))
      })
      .finally(() => {
        if (mounted) setLoadingSupport(false)
      })
    return () => {
      mounted = false
    }
  }, [t])

  const acceptedAttr = useMemo(
    () => (support?.accepted_extensions?.length ? support.accepted_extensions.join(',') : undefined),
    [support],
  )

  const acceptedExtensions = useMemo(
    () => new Set((support?.accepted_extensions ?? []).map((value) => value.toLowerCase())),
    [support],
  )

  const addFiles = (list: FileList | File[]) => {
    if (loadingSupport) {
      setError(t('uploadWorkspace.errorMissingSupport'))
      return
    }
    const incoming = Array.from(list || []).filter((file) => {
      const ext = `.${file.name.split('.').pop()?.toLowerCase()}`
      return acceptedExtensions.size === 0 || acceptedExtensions.has(ext)
    })
    if (!incoming.length) {
      setError(t('uploadWorkspace.errorUnsupported'))
      return
    }
    setError('')
    setMessage('')
    setFiles((prev) => {
      const existing = new Set(prev.map((entry) => entry.key))
      const merged = [...prev]
      incoming.forEach((file) => {
        const key = fileKey(file)
        if (!existing.has(key)) merged.push({ file, key })
      })
      return merged
    })
  }

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    addFiles(event.dataTransfer.files)
  }

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files?.length) addFiles(event.target.files)
    event.target.value = ''
  }

  const removeFile = (key: string) => {
    setFiles((prev) => prev.filter((entry) => entry.key !== key))
  }

  const clearAll = () => {
    if (uploading) return
    setFiles([])
    setError('')
    setMessage('')
  }

  const handleUpload = async () => {
    if (uploading) return
    if (!files.length) {
      setError(t('uploadWorkspace.errorEmpty'))
      return
    }
    setUploading(true)
    setError('')
    setMessage('')
    try {
      await runImportAsync(files.map((entry) => entry.file), { force: false })
      setFiles([])
      setMessage(t('workspace.backgroundIdle'))
      onUploaded?.()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not upload files.')
    } finally {
      setUploading(false)
    }
  }

  const queuedLabel = files.length === 1
    ? t('uploadWorkspace.queued_one', { count: 1 })
    : t('uploadWorkspace.queued_other', { count: files.length })

  return (
    <section
      onDragOver={(event) => {
        event.preventDefault()
        if (!uploading) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      style={{
        borderRadius: 24,
        border: `1px solid ${dragging ? '#0f766e' : '#dbe4f0'}`,
        background: dragging
          ? 'linear-gradient(180deg, rgba(236,253,245,0.95) 0%, #ffffff 100%)'
          : 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
        boxShadow: '0 18px 34px rgba(15, 23, 42, 0.06)',
        padding: '1rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ maxWidth: 720 }}>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#0f766e' }}>
            {t('workspace.eyebrow')}
          </div>
          <h2 style={{ margin: '0.3rem 0 0', fontSize: 22, lineHeight: 1.1, color: '#0f172a' }}>
            {t('uploadWorkspace.title')}
          </h2>
          <p style={{ margin: '0.45rem 0 0', fontSize: 14, color: '#475569' }}>
            {t('uploadWorkspace.subtitle')}
          </p>
        </div>
        <div style={{ fontSize: 12, color: '#64748b', textAlign: 'right' }}>
          <div>{queuedLabel}</div>
          <div style={{ marginTop: 4 }}>{loadingSupport ? t('uploadWorkspace.supportLoading') : t('uploadWorkspace.supportReady')}</div>
        </div>
      </div>

      <div
        style={{
          marginTop: '1rem',
          border: `2px dashed ${dragging ? '#0f766e' : '#cbd5e1'}`,
          borderRadius: 22,
          padding: '1.6rem 1.2rem',
          textAlign: 'center',
          background: dragging ? '#ecfdf5' : '#fff',
          cursor: uploading || loadingSupport ? 'default' : 'pointer',
        }}
        onClick={() => {
          if (!uploading && !loadingSupport) {
            const input = document.getElementById('importador-quick-upload-input') as HTMLInputElement | null
            input?.click()
          }
        }}
      >
        <div style={{ width: 54, height: 54, margin: '0 auto 0.8rem', borderRadius: 18, background: '#0f766e', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 800 }}>
          +
        </div>
        <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>{t('uploadWorkspace.dropHint')}</div>
        <div style={{ marginTop: 6, fontSize: 13, color: '#64748b' }}>Files added here will stay visible in this workspace.</div>
        <input
          id="importador-quick-upload-input"
          type="file"
          multiple
          accept={acceptedAttr}
          onChange={onFileChange}
          style={{ position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', border: 0 }}
        />
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: '1rem', display: 'grid', gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: '#334155' }}>{queuedLabel}</div>
          <div style={{ display: 'grid', gap: 8, maxHeight: 220, overflowY: 'auto', paddingRight: 2 }}>
            {files.map((entry) => (
              <div key={entry.key} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', padding: '0.7rem 0.85rem', border: '1px solid #e2e8f0', borderRadius: 14, background: '#fff' }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.file.name}
                  </div>
                  <div style={{ marginTop: 3, fontSize: 12, color: '#64748b' }}>{prettySize(entry.file.size)}</div>
                </div>
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => removeFile(entry.key)}
                  style={{ border: '1px solid #d1d5db', borderRadius: 10, background: '#fff', padding: '0.35rem 0.7rem', cursor: uploading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 700, color: '#475569' }}
                >
                  {t('uploadWorkspace.clear')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ fontSize: 12, color: '#64748b' }}>
          {message || t('uploadWorkspace.supportReady')}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={clearAll}
            disabled={uploading || files.length === 0}
            style={{
              padding: '0.55rem 0.85rem',
              borderRadius: 12,
              border: '1px solid #d1d5db',
              background: '#fff',
              color: '#475569',
              fontSize: 13,
              fontWeight: 700,
              cursor: uploading || files.length === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            {t('uploadWorkspace.clear')}
          </button>
          <button
            type="button"
            onClick={() => { void handleUpload() }}
            disabled={uploading || loadingSupport || files.length === 0}
            style={{
              padding: '0.55rem 0.95rem',
              borderRadius: 12,
              border: 'none',
              background: uploading || loadingSupport || files.length === 0 ? '#94a3b8' : '#0f766e',
              color: '#fff',
              fontSize: 13,
              fontWeight: 800,
              cursor: uploading || loadingSupport || files.length === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            {uploading ? t('uploadWorkspace.uploading') : t('uploadWorkspace.upload')}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ marginTop: '0.85rem', padding: '0.75rem 0.85rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, color: '#991b1b', fontSize: 13 }}>
          {error}
        </div>
      )}
    </section>
  )
}
