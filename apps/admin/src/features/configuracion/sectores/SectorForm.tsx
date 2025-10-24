import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createSector, getSector, updateSector, listTipoEmpresa, listTipoNegocio, type Sector } from '../../../services/configuracion/sectores'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<Sector, 'id'>

export default function SectorForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ nombre: '', tipo_empresa_id: 0, tipo_negocio_id: 0, config_json: {} })
  const { success, error } = useToast()
  const [empresas, setEmpresas] = useState<Array<{ id: number; nombre: string }>>([])
  const [negocios, setNegocios] = useState<Array<{ id: number; nombre: string }>>([])

  useEffect(() => {
    ;(async () => {
      const [es, ns] = await Promise.all([listTipoEmpresa(), listTipoNegocio()])
      setEmpresas(es)
      setNegocios(ns)
      if (es.length && !form.tipo_empresa_id) setForm((f) => ({ ...f, tipo_empresa_id: es[0].id }))
      if (ns.length && !form.tipo_negocio_id) setForm((f) => ({ ...f, tipo_negocio_id: ns[0].id }))
    })()
  }, [])

  useEffect(() => {
    if (id) {
      getSector(id).then((m) => setForm({ nombre: m.nombre, tipo_empresa_id: m.tipo_empresa_id, tipo_negocio_id: m.tipo_negocio_id, config_json: m.config_json || {} })).catch(() => {})
    }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.nombre?.trim()) throw new Error('Nombre es requerido')
      if (!form.tipo_empresa_id || !form.tipo_negocio_id) throw new Error('Seleccione tipo de empresa y de negocio')
      if (id) await updateSector(id, form)
      else await createSector(form)
      success('Sector guardado')
      nav('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar Sector' : 'Nuevo Sector'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 620 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Tipo de Empresa</label>
          <select value={form.tipo_empresa_id} onChange={(e) => setForm({ ...form, tipo_empresa_id: Number(e.target.value) })} className="border px-2 py-1 w-full rounded">
            {empresas.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
          </select>
        </div>
        <div>
          <label className="block mb-1">Tipo de Negocio</label>
          <select value={form.tipo_negocio_id} onChange={(e) => setForm({ ...form, tipo_negocio_id: Number(e.target.value) })} className="border px-2 py-1 w-full rounded">
            {negocios.map((x) => <option key={x.id} value={x.id}>{x.nombre}</option>)}
          </select>
        </div>
        <div>
          <label className="block mb-1">Config JSON (opcional)</label>
          <textarea
            value={JSON.stringify(form.config_json, null, 2)}
            onChange={(e) => {
              try { setForm({ ...form, config_json: JSON.parse(e.target.value || '{}') }) } catch {}
            }}
            rows={6}
            className="w-full border px-3 py-2 font-mono rounded"
          />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
