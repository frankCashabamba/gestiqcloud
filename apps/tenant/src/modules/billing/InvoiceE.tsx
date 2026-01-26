import React from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { exportarFacturae } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function FacturaePage() {
  const { id } = useParams()
  const { t } = useTranslation()
  const { success, error } = useToast()
  const descargar = async () => {
    try {
      if (!id) throw new Error(t('billing.facturae.errors.idRequired'))
      const blob = await exportarFacturae(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `factura-${id}.xml`
      a.click()
      URL.revokeObjectURL(url)
      success(t('billing.facturae.exported'))
    } catch(e:any) { error(getErrorMessage(e)) }
  }
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-2">{t('billing.facturae.title')}</h2>
      <button onClick={descargar} className="bg-blue-600 text-white px-3 py-2 rounded">{t('billing.facturae.downloadXml')}</button>
    </div>
  )
}
