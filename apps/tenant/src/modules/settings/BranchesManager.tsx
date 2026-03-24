import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import tenantApi from '../../shared/api/client'
import { useToast } from '../../shared/toast'

interface Branch {
  id: string
  name: string
  code: string
  address: string | null
  city: string | null
  phone: string | null
  is_main: boolean
  is_active: boolean
}

interface BranchForm {
  name: string
  code: string
  address: string
  city: string
  phone: string
  is_main: boolean
}

const emptyForm: BranchForm = { name: '', code: '', address: '', city: '', phone: '', is_main: false }

export default function BranchesManager() {
  const { t } = useTranslation(['settings', 'common'])
  const { success, error: showError } = useToast()
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const [form, setForm] = useState<BranchForm>(emptyForm)
  const [deleteTarget, setDeleteTarget] = useState<Branch | null>(null)

  const load = () => {
    setLoading(true)
    tenantApi.get('/api/v1/tenant/branches')
      .then(r => setBranches(r.data))
      .catch(() => showError(t('settings:branches.errorLoad')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editing) {
        await tenantApi.put(`/api/v1/tenant/branches/${editing}`, form)
        success(t('settings:branches.updated'))
      } else {
        await tenantApi.post('/api/v1/tenant/branches', form)
        success(t('settings:branches.created'))
      }
      setShowForm(false)
      setEditing(null)
      setForm(emptyForm)
      load()
    } catch {
      showError(t('settings:branches.errorSave'))
    }
  }

  const handleEdit = (b: Branch) => {
    setForm({ name: b.name, code: b.code, address: b.address || '', city: b.city || '', phone: b.phone || '', is_main: b.is_main })
    setEditing(b.id)
    setShowForm(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await tenantApi.delete(`/api/v1/tenant/branches/${id}`)
      success(t('settings:branches.deleted'))
      load()
    } catch {
      showError(t('settings:branches.errorDelete'))
    } finally {
      setDeleteTarget(null)
    }
  }

  if (loading) return <div className="p-6">{t('settings:branches.loading')}</div>

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">{t('settings:branches.title')}</h2>
        <button
          onClick={() => { setShowForm(true); setEditing(null); setForm(emptyForm) }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {t('settings:branches.newBranch')}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder={t('settings:branches.namePlaceholder')}
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              required
              className="border rounded px-3 py-2"
            />
            <input
              placeholder={t('settings:branches.codePlaceholder')}
              value={form.code}
              onChange={e => setForm({ ...form, code: e.target.value })}
              required
              disabled={!!editing}
              className="border rounded px-3 py-2 disabled:bg-gray-100"
            />
            <input
              placeholder={t('settings:branches.addressPlaceholder')}
              value={form.address}
              onChange={e => setForm({ ...form, address: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <input
              placeholder={t('settings:branches.cityPlaceholder')}
              value={form.city}
              onChange={e => setForm({ ...form, city: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <input
              placeholder={t('settings:branches.phonePlaceholder')}
              value={form.phone}
              onChange={e => setForm({ ...form, phone: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_main}
                onChange={e => setForm({ ...form, is_main: e.target.checked })}
              />
              {t('settings:branches.isMain')}
            </label>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
              {editing ? t('settings:branches.update') : t('settings:branches.create')}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditing(null) }} className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">
              {t('settings:branches.cancel')}
            </button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">{t('settings:branches.colName')}</th>
              <th className="px-4 py-3 text-left">{t('settings:branches.colCode')}</th>
              <th className="px-4 py-3 text-left">{t('settings:branches.colCity')}</th>
              <th className="px-4 py-3 text-left">{t('settings:branches.colPhone')}</th>
              <th className="px-4 py-3 text-center">{t('settings:branches.colMain')}</th>
              <th className="px-4 py-3 text-center">{t('settings:branches.colActive')}</th>
              <th className="px-4 py-3 text-right">{t('settings:branches.colActions')}</th>
            </tr>
          </thead>
          <tbody>
            {branches.map(b => (
              <tr key={b.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">{b.name}</td>
                <td className="px-4 py-3 font-mono">{b.code}</td>
                <td className="px-4 py-3">{b.city || '—'}</td>
                <td className="px-4 py-3">{b.phone || '—'}</td>
                <td className="px-4 py-3 text-center">{b.is_main ? '⭐' : ''}</td>
                <td className="px-4 py-3 text-center">{b.is_active ? '✅' : '❌'}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(b)} className="text-blue-600 hover:underline">{t('settings:branches.edit')}</button>
                  {!b.is_main && (
                    <button onClick={() => setDeleteTarget(b)} className="text-red-600 hover:underline">{t('settings:branches.delete')}</button>
                  )}
                </td>
              </tr>
            ))}
            {branches.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">{t('settings:branches.empty')}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">{t('settings:branches.confirmDeleteTitle')}</h3>
            <p className="text-sm text-slate-600 mb-4">
              {t('settings:branches.confirmDeleteMsg', { name: deleteTarget.name })}
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">
                {t('settings:branches.cancel')}
              </button>
              <button onClick={() => handleDelete(deleteTarget.id)} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">
                {t('settings:branches.confirmDelete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
