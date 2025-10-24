/**
 * Cliente Form
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createCliente } from './services'

export default function ClienteForm() {
  const navigate = useNavigate()
  const [nombre, setNombre] = useState('')
  const [nif, setNif] = useState('')
  const [email, setEmail] = useState('')
  const [telefono, setTelefono] = useState('')
  const [direccion, setDireccion] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!nombre) {
      alert('El nombre es obligatorio')
      return
    }
    
    try {
      setLoading(true)
      await createCliente({ nombre, nif, email, telefono, direccion })
      alert('Cliente creado')
      navigate('/clientes')
    } catch (err: any) {
      alert(err.message || 'Error al crear cliente')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Nuevo Cliente</h1>

      <form onSubmit={handleSubmit} className="rounded-xl border bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Nombre *</label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">NIF/CIF</label>
              <input
                type="text"
                value={nif}
                onChange={(e) => setNif(e.target.value)}
                className="mt-1 block w-full rounded-lg border px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium">Teléfono</label>
              <input
                type="tel"
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
                className="mt-1 block w-full rounded-lg border px-3 py-2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Dirección</label>
            <textarea
              value={direccion}
              onChange={(e) => setDireccion(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-3 py-2"
              rows={3}
            />
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
            >
              {loading ? 'Guardando...' : 'Guardar Cliente'}
            </button>
            
            <button
              type="button"
              onClick={() => navigate('/clientes')}
              className="rounded-lg border px-6 py-3 font-medium hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
