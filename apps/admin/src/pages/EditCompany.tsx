import React, { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { getEmpresa, updateEmpresa } from '../services/empresa'
import { useToast, getErrorMessage } from '../shared/toast'

export function EditarEmpresa() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { success, error } = useToast()
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<{ nombre: string; slug?: string }>({ nombre: '' })

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const data = await getEmpresa(id as string)
        setForm({ nombre: data?.nombre || '', slug: data?.slug || '' })
      } catch (e: any) {
        error(getErrorMessage(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  const onChange: React.ChangeEventHandler<HTMLInputElement> = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      await updateEmpresa(id as string, form)
      success('Company updated')
      navigate('/admin/companies')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Edit Company</h2>
        <Link to="/admin/companies" className="text-sm text-blue-600">Back</Link>
      </div>
      {loading ? (
        <div className="text-sm text-gray-500">Loading…</div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4 max-w-md">
          <div>
            <label className="block mb-1">Name</label>
            <input name="nombre" value={form.nombre} onChange={onChange} className="border px-2 py-1 w-full rounded" required />
          </div>
          <div>
            <label className="block mb-1">Slug</label>
            <input name="slug" value={form.slug || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
          </div>
          <div className="pt-2">
            <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Save</button>
          </div>
        </form>
      )}
    </div>
  )
}
