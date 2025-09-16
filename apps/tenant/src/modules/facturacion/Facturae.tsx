import React from 'react'
import { useParams } from 'react-router-dom'
import { exportarFacturae } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function FacturaePage() {
  const { id } = useParams()
  const { success, error } = useToast()
  const descargar = async () => {
    try {
      if (!id) throw new Error('Id requerido')
      const blob = await exportarFacturae(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `factura-${id}.xml`
      a.click()
      URL.revokeObjectURL(url)
      success('Facturae exportada')
    } catch(e:any) { error(getErrorMessage(e)) }
  }
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-2">Facturae</h2>
      <button onClick={descargar} className="bg-blue-600 text-white px-3 py-2 rounded">Descargar XML</button>
    </div>
  )
}

