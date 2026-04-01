import React, { useEffect, useMemo, useState } from 'react'

import { useSearchParams } from 'react-router-dom'

import api from '../../services/api'

type FieldItem = { field: string; visible: boolean; required: boolean; ord?: number | null; label?: string | null; help?: string | null; field_type?: string | null; options?: string[] | null; validation_pattern?: string | null }

export default function FieldConfigManager() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [sector, setSector] = useState(searchParams.get('sector') || 'global')
  const [moduleKey, setModuleKey] = useState(searchParams.get('module') || 'clientes')
  const [empresa, setEmpresa] = useState(searchParams.get('empresa') || '')
  const [formMode, setFormMode] = useState<'mixed'|'tenant'|'sector'|'basic'>((searchParams.get('mode') as any) || 'mixed')
  const [items, setItems] = useState<FieldItem[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  async function load() {
    setMsg(null)
    setLoading(true)
    try {
      // Prefer tenant config when empresa slug is present; otherwise sector defaults
      if (empresa) {
        const { data } = await api.get(`/company/settings/fields`, { params: { module: moduleKey, empresa } })
        setItems(data.items || [])
      } else {
        const { data } = await api.get(`/admin/field-config/sector`, { params: { module: moduleKey, sector } })
        setItems(data.items || [])
      }
    } catch (e: any) {
      setMsg(e?.message || 'Error cargando configuración')
    } finally {
      setLoading(false)
    }
  }

  async function save() {
    setMsg(null)
    setLoading(true)
    try {
      if (empresa) {
        await api.put(`/admin/field-config/tenant`, { empresa, module: moduleKey, items })
        await api.put(`/admin/field-config/tenant/mode`, { empresa, module: moduleKey, form_mode: formMode })
      } else {
        await api.put(`/admin/field-config/sector`, { sector, module: moduleKey, items })
      }
      setMsg('Configuration saved')
    } catch (e: any) {
      setMsg(e?.message || 'Error guardando configuración')
    } finally {
      setLoading(false)
    }
  }

  // Auto-apply query param changes
  useEffect(() => {
    const sp = new URLSearchParams()
    if (sector) sp.set('sector', sector)
    if (moduleKey) sp.set('module', moduleKey)
    if (empresa) sp.set('empresa', empresa)
    if (formMode) sp.set('mode', formMode)
    setSearchParams(sp, { replace: true })
  }, [sector, moduleKey, empresa, formMode])

  // Auto-load when selection changes
  useEffect(() => { load() }, [sector, moduleKey, empresa])

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Configuración de Campos</h2>
      <p className="text-sm text-slate-500">Gestiona visibilidad y obligatoriedad por sector o por tenant.</p>

      <div style={{ display: 'flex', gap: 12, alignItems: 'end', marginBottom: 12 }}>
        <div>
          <label htmlFor="sector-select">Sector</label>
          <select id="sector-select" name="sector" value={sector} onChange={(e) => setSector(e.target.value)} className="input">
            <option value="global">Global (plantillas base)</option>
            <option value="retail">Retail/Bazar</option>
            <option value="panaderia">Panadería</option>
            <option value="taller">Taller</option>
            <option value="restaurante">Restaurante</option>
            <option value="farmacia">Farmacia</option>
          </select>
        </div>
        <div>
          <label>Módulo</label>
          <select id="module-select" name="module" aria-label="Module" value={moduleKey} onChange={(e) => setModuleKey(e.target.value)} className="input">
            <option value="clientes">Clientes</option>
            <option value="products">Productos</option>
            <option value="inventory">Inventario</option>
            <option value="ventas">Ventas</option>
            <option value="suppliers">Proveedores</option>
            <option value="expenses">Gastos</option>
            <option value="billing">Facturación</option>
            <option value="purchases">Compras</option>
            <option value="crm_leads">CRM Leads</option>
            <option value="crm_opportunities">CRM Oportunidades</option>
          </select>
        </div>
        <div>
          <label htmlFor="empresa-input">Empresa (slug) opcional</label>
          <input id="empresa-input" name="empresa" aria-label="Empresa (slug) opcional" value={empresa} onChange={(e)=> setEmpresa(e.target.value)} placeholder="bazar-omar" className="input" />
        </div>
        <div>
          <label>Modo</label>
          <select aria-label="Modo" value={formMode} onChange={(e)=> setFormMode(e.target.value as any)} className="input">
            <option value="mixed">Mixto (sector + tenant)</option>
            <option value="tenant">Solo tenant (100% personalizado)</option>
            <option value="sector">Solo sector</option>
            <option value="basic">Básico</option>
          </select>
        </div>
        <button className="gc-button gc-button--primary" onClick={save} disabled={loading}>Guardar</button>
      </div>

      {msg && <div className="notice">{msg}</div>}

      {loading ? (
        <div>Cargando…</div>
      ) : (
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              <th>Campo</th>
              <th>Visible</th>
              <th>Obligatorio</th>
              <th>Orden</th>
              <th>Etiqueta</th>
              <th>Ayuda</th>
              <th>Tipo</th>
              <th>Opciones</th>
              <th>Patrón</th>
              <th>✕</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td><input aria-label={`Campo fila ${i+1}`} name={`field-${i}`} value={it.field} onChange={(e)=> {
                  const v = e.target.value; setItems(prev => prev.map((x,idx)=> idx===i? {...x, field: v}: x))
                }} className="input" /></td>
                <td><input aria-label={`Visible fila ${i+1}`} name={`visible-${i}`} type="checkbox" checked={!!it.visible} onChange={(e)=> setItems(prev => prev.map((x,idx)=> idx===i? {...x, visible: e.target.checked}: x))} /></td>
                <td><input aria-label={`Obligatorio fila ${i+1}`} name={`required-${i}`} type="checkbox" checked={!!it.required} onChange={(e)=> setItems(prev => prev.map((x,idx)=> idx===i? {...x, required: e.target.checked}: x))} /></td>
                <td><input aria-label={`Orden fila ${i+1}`} name={`ord-${i}`} type="number" value={it.ord ?? ''} onChange={(e)=> {
                  const num = e.target.value === '' ? null : Number(e.target.value);
                  setItems(prev => prev.map((x,idx)=> idx===i? {...x, ord: (num as any)}: x))
                }} className="input" style={{ width: 80 }} /></td>
                <td><input aria-label={`Etiqueta fila ${i+1}`} name={`label-${i}`} value={it.label || ''} onChange={(e)=> setItems(prev => prev.map((x,idx)=> idx===i? {...x, label: e.target.value}: x))} className="input" /></td>
                <td><input aria-label={`Ayuda fila ${i+1}`} name={`help-${i}`} value={it.help || ''} onChange={(e)=> setItems(prev => prev.map((x,idx)=> idx===i? {...x, help: e.target.value}: x))} className="input" /></td>
                <td>
                  <select
                    aria-label={`Tipo fila ${i+1}`}
                    value={it.field_type || 'text'}
                    onChange={(e) => setItems(prev => prev.map((x, idx) => idx === i ? { ...x, field_type: e.target.value } : x))}
                    className="input"
                  >
                    <option value="text">Texto</option>
                    <option value="number">Número</option>
                    <option value="date">Fecha</option>
                    <option value="boolean">Sí/No</option>
                    <option value="select">Desplegable</option>
                    <option value="textarea">Texto largo</option>
                    <option value="email">Email</option>
                  </select>
                </td>
                <td>
                  <input
                    aria-label={`Opciones fila ${i+1}`}
                    value={(it.options || []).join(', ')}
                    onChange={(e) => {
                      const opts = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                      setItems(prev => prev.map((x, idx) => idx === i ? { ...x, options: opts } : x))
                    }}
                    className="input"
                    placeholder="op1, op2, op3"
                    disabled={it.field_type !== 'select'}
                    style={{ width: 160 }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`Patrón fila ${i+1}`}
                    value={it.validation_pattern || ''}
                    onChange={(e) => setItems(prev => prev.map((x, idx) => idx === i ? { ...x, validation_pattern: e.target.value } : x))}
                    className="input"
                    placeholder="^[0-9]+$"
                    style={{ width: 140 }}
                  />
                </td>
                <td>
                  <button
                    type="button"
                    aria-label={`Eliminar fila ${i+1}`}
                    onClick={() => setItems(prev => prev.filter((_, idx) => idx !== i))}
                    style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}
                    title="Eliminar campo"
                  >✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ marginTop: 12 }}>
        <button className="gc-button" onClick={()=> setItems(prev => [...prev, { field: '', visible: true, required: false, field_type: 'text' }])}>Añadir campo</button>
      </div>
    </div>
  )
}
