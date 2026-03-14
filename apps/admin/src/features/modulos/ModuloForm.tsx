import React, { useEffect, useState, CSSProperties } from 'react'

import { useNavigate, useParams } from 'react-router-dom'

import { createModulo, getModulo, updateModulo } from '../../services/modulos'
import { useToast, getErrorMessage } from '../../shared/toast'

import type { Module } from '../../modulos/types'

const CATEGORIES = [
  { value: '', label: 'Sin categoría' },
  { value: 'core', label: 'Negocio principal' },
  { value: 'operations', label: 'Operaciones' },
  { value: 'finance', label: 'Finanzas y contabilidad' },
  { value: 'integrations', label: 'Integraciones' },
  { value: 'ai', label: 'IA y automatización' },
  { value: 'admin', label: 'Administración' },
]

const s = {
  page: {
    padding: 'var(--gc-page-x)',
    maxWidth: 640,
    margin: '0 auto',
  } as CSSProperties,
  backLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--gc-muted)',
    textDecoration: 'none',
    marginBottom: 20,
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: 0,
  } as CSSProperties,
  card: {
    background: 'var(--gc-surface)',
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-md)',
    boxShadow: 'var(--gc-shadow-xs)',
    overflow: 'hidden',
  } as CSSProperties,
  cardHeader: {
    padding: '18px 24px',
    borderBottom: '1px solid var(--gc-border)',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  } as CSSProperties,
  headerIcon: {
    width: 36,
    height: 36,
    borderRadius: 'var(--gc-radius-sm)',
    background: 'var(--gc-primary-soft)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 16,
  } as CSSProperties,
  headerTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: 'var(--gc-foreground)',
    margin: 0,
  } as CSSProperties,
  headerSub: {
    fontSize: 12,
    color: 'var(--gc-muted)',
    margin: 0,
  } as CSSProperties,
  body: {
    padding: 24,
    display: 'flex',
    flexDirection: 'column',
    gap: 18,
  } as CSSProperties,
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 18,
  } as CSSProperties,
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  } as CSSProperties,
  label: {
    fontSize: 12,
    fontWeight: 500,
    color: 'var(--gc-muted)',
    letterSpacing: '0.01em',
  } as CSSProperties,
  input: {
    padding: '9px 12px',
    fontSize: 13,
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-sm)',
    outline: 'none',
    background: 'var(--gc-surface)',
    color: 'var(--gc-foreground)',
    width: '100%',
    transition: 'border-color 0.15s, box-shadow 0.15s',
  } as CSSProperties,
  select: {
    padding: '9px 12px',
    fontSize: 13,
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-sm)',
    outline: 'none',
    background: 'var(--gc-surface)',
    color: 'var(--gc-foreground)',
    width: '100%',
    cursor: 'pointer',
  } as CSSProperties,
  textarea: {
    padding: '9px 12px',
    fontSize: 13,
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-sm)',
    outline: 'none',
    background: 'var(--gc-surface)',
    color: 'var(--gc-foreground)',
    width: '100%',
    resize: 'vertical',
    minHeight: 60,
    fontFamily: 'inherit',
  } as CSSProperties,
  footer: {
    padding: '14px 24px',
    borderTop: '1px solid var(--gc-border)',
    background: 'var(--gc-bg)',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
  } as CSSProperties,
  btnCancel: {
    padding: '8px 18px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--gc-foreground)',
    background: 'var(--gc-surface)',
    border: '1px solid var(--gc-border)',
    borderRadius: 'var(--gc-radius-sm)',
    cursor: 'pointer',
  } as CSSProperties,
  btnSave: {
    padding: '8px 18px',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--gc-on-primary)',
    background: 'var(--gc-primary)',
    border: 'none',
    borderRadius: 'var(--gc-radius-sm)',
    cursor: 'pointer',
  } as CSSProperties,
}

export default function ModuloForm({ mode }: { mode: 'create' | 'edit' }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const [form, setForm] = useState<Partial<Module>>({
    name: '',
    initial_template: '',
    category: null,
    description: null,
    icon: null,
    url: null,
    active: true,
  })
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()

  useEffect(() => {
    if (mode === 'edit' && id) {
      getModulo(id)
        .then((m) =>
          setForm({
            ...m,
            initial_template: m.initial_template || '',
            description: m.description ?? '',
          }),
        )
        .catch((e: any) => {
          const status = e?.response?.status
          if (status === 404) {
            error('El módulo ya no existe; regresando al listado')
            navigate('..')
          } else {
            error(getErrorMessage(e))
          }
        })
    }
  }, [mode, id])

  const set = (field: string, value: string | null) =>
    setForm((f) => ({ ...f, [field]: value }))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      setSaving(true)
      if (!form.name?.trim() || !form.initial_template?.trim())
        throw new Error('Complete name and initial template')
      if (mode === 'edit' && id) {
        await updateModulo(id, form)
      } else {
        await createModulo(form)
      }
      success('Módulo guardado')
      navigate('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const isEdit = mode === 'edit'

  return (
    <div style={s.page}>
      {/* Back */}
      <button style={s.backLink} onClick={() => navigate('..')}>
        ← Volver a módulos
      </button>

      <form onSubmit={onSubmit}>
        <div style={s.card}>
          {/* Card header */}
          <div style={s.cardHeader}>
            <div style={s.headerIcon}>{form.icon || '🧩'}</div>
            <div>
              <h2 style={s.headerTitle}>{isEdit ? 'Editar módulo' : 'Crear módulo'}</h2>
              <p style={s.headerSub}>
                {isEdit ? `Editando: ${form.name || ''}` : 'Nuevo módulo del sistema'}
              </p>
            </div>
          </div>

          {/* Form body */}
          <div style={s.body}>
            {/* Name + URL */}
            <div style={s.row}>
              <div style={s.field}>
                <label style={s.label}>Nombre *</label>
                <input
                  style={s.input}
                  name="name"
                  value={form.name || ''}
                  onChange={(e) => set('name', e.target.value)}
                  placeholder="products"
                  required
                />
              </div>
              <div style={s.field}>
                <label style={s.label}>URL</label>
                <input
                  style={s.input}
                  name="url"
                  value={form.url || ''}
                  onChange={(e) => set('url', e.target.value || null)}
                  placeholder="products"
                />
              </div>
            </div>

            {/* Template + Icon */}
            <div style={s.row}>
              <div style={s.field}>
                <label style={s.label}>Initial template *</label>
                <input
                  style={s.input}
                  name="initial_template"
                  value={form.initial_template || ''}
                  onChange={(e) => set('initial_template', e.target.value)}
                  placeholder="products"
                  required
                />
              </div>
              <div style={s.field}>
                <label style={s.label}>Icono</label>
                <input
                  style={s.input}
                  name="icon"
                  value={form.icon || ''}
                  onChange={(e) => set('icon', e.target.value || null)}
                  placeholder="📦"
                />
              </div>
            </div>

            {/* Category */}
            <div style={s.field}>
              <label style={s.label}>Categoría</label>
              <select
                style={s.select}
                value={form.category || ''}
                onChange={(e) => set('category', e.target.value || null)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            {/* Description */}
            <div style={s.field}>
              <label style={s.label}>Descripción</label>
              <textarea
                style={s.textarea}
                value={form.description || ''}
                onChange={(e) => set('description', e.target.value || null)}
                placeholder="Breve descripción del módulo"
                rows={2}
              />
            </div>
          </div>

          {/* Footer actions */}
          <div style={s.footer}>
            <button type="button" style={s.btnCancel} onClick={() => navigate('..')}>
              Cancelar
            </button>
            <button type="submit" style={s.btnSave} disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
