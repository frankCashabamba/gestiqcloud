import React, { useEffect, useState } from 'react'
import { listPaymentMethods, createPaymentMethod, updatePaymentMethod, deletePaymentMethod, listCuentas } from '../services'
import type { PaymentMethod, PlanCuenta } from '../services'

export default function PaymentMethods() {
  const [methods, setMethods] = useState<PaymentMethod[]>([])
  const [accounts, setAccounts] = useState<PlanCuenta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingId, setSavingId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<{ id?: string; name: string; description?: string; account_id: string; is_active: boolean }>({
    name: '',
    description: '',
    account_id: '',
    is_active: true,
  })

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [pm, cuentas] = await Promise.all([listPaymentMethods(), listCuentas()])
      setMethods(pm)
      setAccounts(cuentas)
    } catch (e: any) {
      setError(e?.message || 'No se pudieron cargar los medios de pago')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const resetForm = () => {
    setForm({ name: '', description: '', account_id: '', is_active: true })
    setCreating(false)
    setSavingId(null)
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.account_id) {
      setError('Nombre y cuenta son obligatorios')
      return
    }
    setError(null)
    setSavingId(form.id || 'new')
    try {
      if (form.id) {
        const updated = await updatePaymentMethod(form.id, form)
        setMethods((prev) => prev.map((m) => (m.id === updated.id ? updated : m)))
      } else {
        const created = await createPaymentMethod(form)
        setMethods((prev) => [...prev, created])
      }
      resetForm()
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'No se pudo guardar')
    } finally {
      setSavingId(null)
    }
  }

  const handleEdit = (m: PaymentMethod) => {
    setForm({
      id: m.id,
      name: m.name,
      description: m.description || '',
      account_id: m.account_id,
      is_active: m.is_active,
    })
    setCreating(true)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar este medio de pago?')) return
    try {
      await deletePaymentMethod(id)
      setMethods((prev) => prev.filter((m) => m.id !== id))
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'No se pudo eliminar')
    }
  }

  if (loading) return <div className="p-4">Cargando medios de pago…</div>

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Medios de pago POS</h3>
        <p className="text-sm text-gray-600">Asocia cada medio de pago a una cuenta contable. Sin mapeo no se puede contabilizar.</p>
      </div>
      {error && <div className="p-2 rounded bg-red-50 text-red-700 text-sm">{error}</div>}

      <div className="border rounded p-3 space-y-3">
        <div className="grid md:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium">Nombre</label>
            <input
              className="w-full border rounded px-3 py-2"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="EFECTIVO, TARJETA, LINK..."
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Cuenta contable</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={form.account_id}
              onChange={(e) => setForm((f) => ({ ...f, account_id: e.target.value }))}
            >
              <option value="">— Selecciona —</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.codigo} - {a.nombre}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Descripción</label>
          <input
            className="w-full border rounded px-3 py-2"
            value={form.description || ''}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            placeholder="Opcional"
          />
        </div>
        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
          />
          Activo
        </label>
        <div className="flex gap-2 justify-end">
          {form.id && (
            <button className="px-3 py-2 rounded border" onClick={resetForm}>
              Cancelar
            </button>
          )}
          <button
            className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
            onClick={handleSave}
            disabled={!!savingId}
          >
            {savingId ? 'Guardando…' : form.id ? 'Actualizar' : 'Crear'}
          </button>
        </div>
      </div>

      <div className="border rounded">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 text-gray-700">
            <tr>
              <th className="p-2 text-left">Nombre</th>
              <th className="p-2 text-left">Cuenta</th>
              <th className="p-2 text-left">Estado</th>
              <th className="p-2 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {methods.map((m) => {
              const cuenta = accounts.find((a) => a.id === m.account_id)
              return (
                <tr key={m.id} className="border-t">
                  <td className="p-2 font-medium">{m.name}</td>
                  <td className="p-2 text-gray-600">
                    {cuenta ? `${cuenta.codigo} - ${cuenta.nombre}` : m.account_id}
                  </td>
                  <td className="p-2">{m.is_active ? 'Activo' : 'Inactivo'}</td>
                  <td className="p-2 text-right space-x-2">
                    <button className="text-blue-600 hover:underline" onClick={() => handleEdit(m)}>
                      Editar
                    </button>
                    <button className="text-red-600 hover:underline" onClick={() => handleDelete(m.id)}>
                      Eliminar
                    </button>
                  </td>
                </tr>
              )
            })}
            {methods.length === 0 && (
              <tr>
                <td className="p-3 text-center text-gray-500" colSpan={4}>
                  No hay medios de pago configurados.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
