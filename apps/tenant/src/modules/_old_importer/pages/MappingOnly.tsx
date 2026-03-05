import React, { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import ImportadorLayout from '../components/ImportadorLayout'
import MapeoCampos from '../components/MapeoCampos'
import { useImportQueue } from '../context/ImportQueueContext'
import { useEntityConfig } from '../hooks/useEntityConfig'
import { autoMapeoColumnas } from '../services/autoMapeoColumnas'
import { getAliasSugeridos } from '../utils/aliasCampos'
import { useToast } from '../../../shared/toast'
import { useNavigate, useParams } from 'react-router-dom'
import { listItems, listProductItems } from '../services/importsApi'
import { useAuth } from '../../../auth/AuthContext'

export default function MappingOnly() {
  const { t } = useTranslation('importer')
  const { queue, removeFromQueue } = useImportQueue()
  const { config: entityConfig } = useEntityConfig({ module: 'products' })
  const toast = useToast()
  const navigate = useNavigate()
  const { empresa } = useParams()
  const { token } = useAuth() as { token: string | null }

  const readyItem = useMemo(() => queue.find((q) => q.headers && q.rows), [queue])
  const [fetchedHeaders, setFetchedHeaders] = useState<string[]>([])
  const [fetchedRows, setFetchedRows] = useState<Record<string, any>[]>([])

  // Si el item no tiene headers/rows pero sí batchId (porque se subió por chunks), intenta cargarlos desde el backend.
  React.useEffect(() => {
    let cancelled = false
    async function loadFromBatch() {
      const item = queue.find((q) => q && q.batchId && (!q.headers || q.headers.length === 0))
      if (!item || !item.batchId) {
        setFetchedHeaders([])
        setFetchedRows([])
        return
      }
      try {
        const sourceType = (item as any)?.docType || 'products'
        if (sourceType === 'products') {
          const data = await listProductItems(item.batchId, { limit: 50, offset: 0, authToken: token || undefined })
          const items = (data as any)?.items || []
          const rows = items.map((p: any) => p.raw?.datos || p.raw || p.normalized || {})
          const headers = rows.length > 0 ? Object.keys(rows[0]) : []
          if (!cancelled) {
            setFetchedHeaders(headers)
            setFetchedRows(rows)
          }
        } else {
          const items = await listItems(item.batchId, { authToken: token || undefined })
          const rows = Array.isArray(items) ? items.map((p: any) => p.raw?.datos || p.raw || p.normalized || {}) : []
          const headers = rows.length > 0 ? Object.keys(rows[0]) : []
          if (!cancelled) {
            setFetchedHeaders(headers)
            setFetchedRows(rows)
          }
        }
      } catch (e) {
        if (!cancelled) {
          setFetchedHeaders([])
          setFetchedRows([])
        }
      }
    }
    loadFromBatch()
    return () => { cancelled = true }
  }, [queue, token])

  const headers = readyItem?.headers || fetchedHeaders
  const rows = ((readyItem?.rows as Record<string, any>[] | undefined) || fetchedRows || []).filter(Boolean)

  const camposObjetivo = useMemo(
    () => entityConfig?.fields.map((f) => f.field) || ['nombre', 'precio'],
    [entityConfig]
  )

  const [mapa, setMapa] = useState<Partial<Record<string, string>>>(() => {
    const sugeridos = autoMapeoColumnas(headers, getAliasSugeridos(entityConfig))
    return sugeridos as any
  })

  // Recalcular mapeo sugerido cuando cambian headers o la config
  React.useEffect(() => {
    const sugeridos = autoMapeoColumnas(headers, getAliasSugeridos(entityConfig))
    setMapa(sugeridos as any)
  }, [headers, entityConfig])

  const requiredCampos = useMemo(() => {
    if (entityConfig?.fields) return entityConfig.fields.filter((f) => f.required !== false).map((f) => f.field)
    return camposObjetivo
  }, [entityConfig, camposObjetivo])

  const validar = () => {
    const faltan = requiredCampos.filter((c) => !mapa[c])
    if (rows.length === 0) {
      toast.error(t('wizard.validation.fileHasNoRows'))
      return
    }
    if (faltan.length) {
      toast.error(t('wizard.validation.missingMappingFor', { field: faltan.join(', ') }))
      return
    }
    toast.success(t('wizard.validation.passed'))
  }

  return (
    <ImportadorLayout
      title={t('mapeoCampos.title', { defaultValue: 'Mapeo de campos' })}
      description={t('wizard.mapping.reviewAdjust', { defaultValue: 'Revisa y ajusta el mapeo antes de validar.' })}
    >
      {!readyItem && rows.length === 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800">
          {t('mapeoCampos.emptyState', { defaultValue: 'No hay archivos listos para mapear. Sube uno desde Importar.' })}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-sm text-slate-600">
            {t('mapeoCampos.fileReady', { defaultValue: 'Archivo listo:' })}{' '}
            <strong>{readyItem?.name || 'batch/import'}</strong>
          </div>
          <MapeoCampos
            headers={headers}
            camposObjetivo={camposObjetivo}
            mapa={mapa}
            onChange={setMapa}
            sourceType={readyItem?.docType || 'products'}
            previewData={rows}
            fieldConfig={entityConfig || undefined}
          />
          <div className="flex gap-2">
            <button
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              onClick={validar}
            >
              {t('wizard.actions.validateMapping', { defaultValue: 'Validar mapeo' })}
            </button>
            <button
              className="border border-slate-300 text-slate-700 hover:bg-slate-100 px-4 py-2 rounded"
              onClick={() => {
                if (readyItem?.id) removeFromQueue(readyItem.id)
                const base = empresa ? `/${empresa}/importer` : '/importer'
                navigate(base)
              }}
            >
              {t('common.cancel', { defaultValue: 'Cancelar' })}
            </button>
          </div>
        </div>
      )}
    </ImportadorLayout>
  )
}
