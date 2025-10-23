import React, { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { getEmpresa, updateEmpresa } from '../services/empresa'
import { useToast, getErrorMessage } from '../shared/toast'

export function EditarEmpresa() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { success, error } = useToast()
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<{
    nombre: string;
    slug?: string;
    ruc?: string;
    telefono?: string;
    direccion?: string;
    ciudad?: string;
    provincia?: string;
    cp?: string;
    pais?: string;
    logo?: string;
    color_primario?: string;
    activo?: boolean;
    motivo_desactivacion?: string;
    plantilla_inicio?: string;
    sitio_web?: string;
    config_json?: object;
  }>({ nombre: '' })

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const data = await getEmpresa(id as string)
        setForm({
          nombre: data?.nombre || '',
          slug: data?.slug || '',
          ruc: data?.ruc || '',
          telefono: data?.telefono || '',
          direccion: data?.direccion || '',
          ciudad: data?.ciudad || '',
          provincia: data?.provincia || '',
          cp: data?.cp || '',
          pais: data?.pais || '',
          logo: data?.logo || '',
          color_primario: data?.color_primario || '',
          activo: data?.activo ?? true,
          motivo_desactivacion: data?.motivo_desactivacion || '',
          plantilla_inicio: data?.plantilla_inicio || '',
          sitio_web: data?.sitio_web || '',
          config_json: data?.config_json || {},
        })
      } catch (e: any) {
        error(getErrorMessage(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  const onChange: React.ChangeEventHandler<HTMLInputElement | HTMLTextAreaElement> = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      await updateEmpresa(id as string, form)
      success('Empresa actualizada')
      navigate('/admin/empresas')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Editar Empresa</h2>
        <Link to="/admin/empresas" className="text-sm text-blue-600">Volver</Link>
      </div>
      {loading ? (
        <div className="text-sm text-gray-500">Cargando…</div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4 max-w-md">
          <div>
            <label className="block mb-1">Nombre</label>
            <input name="nombre" value={form.nombre} onChange={onChange} className="border px-2 py-1 w-full rounded" required />
          </div>
          <div>
            <label className="block mb-1">Slug</label>
            <input name="slug" value={form.slug || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">RUC</label>
            <input name="ruc" value={form.ruc || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Teléfono</label>
            <input name="telefono" value={form.telefono || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Dirección</label>
            <textarea name="direccion" value={form.direccion || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" rows={3} />
          </div>
          <div>
            <label className="block mb-1">Ciudad</label>
            <input name="ciudad" value={form.ciudad || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Provincia</label>
            <input name="provincia" value={form.provincia || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Código Postal</label>
            <input name="cp" value={form.cp || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">País</label>
            <input name="pais" value={form.pais || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Logo</label>
            <input name="logo" value={form.logo || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Color Primario</label>
            <input name="color_primario" type="color" value={form.color_primario || '#4f46e5'} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">
              <input name="activo" type="checkbox" checked={form.activo ?? true} onChange={(e) => setForm(f => ({ ...f, activo: e.target.checked }))} /> Activo
            </label>
          </div>
          {!form.activo && (
            <div>
              <label className="block mb-1">Motivo Desactivación</label>
              <input name="motivo_desactivacion" value={form.motivo_desactivacion || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
            </div>
          )}
          <div>
            <label className="block mb-1">Plantilla Inicio</label>
            <input name="plantilla_inicio" value={form.plantilla_inicio || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Sitio Web</label>
            <input name="sitio_web" value={form.sitio_web || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div>
            <label className="block mb-1">Config JSON</label>
            <textarea name="config_json" value={JSON.stringify(form.config_json || {}, null, 2)} onChange={(e) => {
              try {
                const val = JSON.parse(e.target.value);
                setForm(f => ({ ...f, config_json: val }));
              } catch {
                // ignore invalid json
              }
            }} className="border px-2 py-1 w-full rounded" rows={4} />
          </div>
          <div className="pt-2">
            <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          </div>
        </form>
      )}
    </div>
  )
}
