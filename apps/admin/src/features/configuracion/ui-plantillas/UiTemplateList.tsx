import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listUiTemplates, deleteUiTemplate, type UiTemplateItem } from '../../../services/configuracion/uiTemplates'
import { useToast } from '../../../shared/toast'

export default function UiTemplateList() {
  const nav = useNavigate()
  const { success, error } = useToast()
  const [items, setItems] = useState<UiTemplateItem[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setLoading(true)
      const rows = await listUiTemplates()
      setItems(rows)
    } catch (e: any) {
      error('Error cargando plantillas UI')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function onDelete(slug: string) {
    if (!confirm('¿Eliminar plantilla UI?')) return
    try {
      await deleteUiTemplate(slug)
      success('Eliminado')
      load()
    } catch (e: any) {
      error('No se pudo eliminar')
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Plantillas UI</h1>
        <button className="btn btn-primary" onClick={() => nav('nuevo')}>Nueva</button>
      </div>
      {loading ? (
        <div>Cargando…</div>
      ) : (
        <div className="overflow-auto">
          <table className="min-w-full border">
            <thead>
              <tr className="bg-slate-50">
                <th className="p-2 text-left">Slug</th>
                <th className="p-2 text-left">Label</th>
                <th className="p-2 text-left">Pro</th>
                <th className="p-2 text-left">Activo</th>
                <th className="p-2 text-left">Orden</th>
                <th className="p-2"></th>
              </tr>
            </thead>
            <tbody>
              {items.map(it => (
                <tr key={it.slug} className="border-t">
                  <td className="p-2 font-mono">{it.slug}</td>
                  <td className="p-2">{it.label}</td>
                  <td className="p-2">{it.pro ? 'Sí' : 'No'}</td>
                  <td className="p-2">{it.active ? 'Sí' : 'No'}</td>
                  <td className="p-2">{it.ord ?? ''}</td>
                  <td className="p-2 text-right">
                    <button className="btn btn-sm" onClick={() => nav(`${encodeURIComponent(it.slug)}/editar`)}>Editar</button>
                    <button className="btn btn-sm btn-danger ml-2" onClick={() => onDelete(it.slug)}>Eliminar</button>
                  </td>
                </tr>
              ))}
              {!items.length && (
                <tr><td className="p-4 text-center" colSpan={6}>Sin plantillas</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

