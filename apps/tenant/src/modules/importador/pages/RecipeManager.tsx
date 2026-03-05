import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchRecipes, createRecipe, updateRecipe,
  fetchDrafts, createDraft, updateDraft,
  fetchSnapshots, createSnapshot,
  type Recipe, type RecipeDraft, type RecipeSnapshot,
} from '../services'

export default function RecipeManager() {
  const navigate = useNavigate()
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [selected, setSelected] = useState<Recipe | null>(null)
  const [drafts, setDrafts] = useState<RecipeDraft[]>([])
  const [snapshots, setSnapshots] = useState<RecipeSnapshot[]>([])
  const [editDraft, setEditDraft] = useState<RecipeDraft | null>(null)
  const [draftSystem, setDraftSystem] = useState('')
  const [draftUser, setDraftUser] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const loadRecipes = () => {
    setLoading(true)
    fetchRecipes().then(setRecipes).catch(() => setError('Error cargando recetas')).finally(() => setLoading(false))
  }

  useEffect(() => { loadRecipes() }, [])

  const loadRecipeDetail = async (r: Recipe) => {
    setSelected(r)
    setEditDraft(null)
    try {
      const [d, s] = await Promise.all([fetchDrafts(r.id), fetchSnapshots(r.id)])
      setDrafts(d)
      setSnapshots(s)
    } catch { setError('Error cargando detalles') }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setSaving(true)
    try {
      await createRecipe({ name: newName, description: newDesc || undefined })
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      loadRecipes()
    } catch { setError('Error creando receta') }
    setSaving(false)
  }

  const handleArchive = async (r: Recipe) => {
    try {
      await updateRecipe(r.id, { archived: true } as any)
      loadRecipes()
      if (selected?.id === r.id) setSelected(null)
    } catch { setError('Error archivando') }
  }

  const handleCreateDraft = async () => {
    if (!selected) return
    setSaving(true)
    try {
      const d = await createDraft(selected.id, {})
      setDrafts(prev => [d, ...prev])
      setEditDraft(d)
      setDraftSystem(d.prompt_system || '')
      setDraftUser(d.prompt_user || '')
    } catch { setError('Error creando borrador') }
    setSaving(false)
  }

  const handleSaveDraft = async () => {
    if (!editDraft) return
    setSaving(true)
    try {
      const updated = await updateDraft(editDraft.id, { prompt_system: draftSystem, prompt_user: draftUser } as any)
      setEditDraft(updated)
      setDrafts(prev => prev.map(d => d.id === updated.id ? updated : d))
    } catch { setError('Error guardando') }
    setSaving(false)
  }

  const handleSnapshot = async (draftId: string) => {
    setSaving(true)
    try {
      const tag = `v${snapshots.length + 1}`
      const s = await createSnapshot(draftId, tag)
      setSnapshots(prev => [s, ...prev])
    } catch { setError('Error creando snapshot') }
    setSaving(false)
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <button onClick={() => navigate(-1)} style={{ marginBottom: '1rem', cursor: 'pointer', border: 'none', background: 'none', fontSize: 14, color: '#6366F1' }}>← Volver</button>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>📋 Recetas de Importación</h2>
        <button onClick={() => setShowCreate(true)} style={{ padding: '0.5rem 1rem', background: '#6366F1', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}>+ Nueva Receta</button>
      </div>
      <p style={{ color: '#6b7280', fontSize: 13, marginBottom: '1rem' }}>Las recetas configuran los prompts AI para clasificar y extraer datos. Son opcionales (RB-01): sin receta, el sistema usa Zero-shot.</p>

      {error && <div style={{ color: '#991B1B', background: '#FEF2F2', padding: '0.5rem', borderRadius: 6, marginBottom: '0.5rem', fontSize: 13 }}>{error} <button onClick={() => setError('')} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>×</button></div>}

      {/* Create form */}
      {showCreate && (
        <div style={{ padding: '1rem', border: '1px solid #d1d5db', borderRadius: 8, marginBottom: '1rem', background: '#fff' }}>
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Nombre de la receta" style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: 6, marginBottom: '0.5rem' }} />
          <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Descripción (opcional)" style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: 6, marginBottom: '0.5rem' }} />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={handleCreate} disabled={saving} style={{ padding: '0.4rem 1rem', background: '#10B981', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Crear</button>
            <button onClick={() => setShowCreate(false)} style={{ padding: '0.4rem 1rem', background: '#e5e7eb', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Cancelar</button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Recipe list */}
        <div style={{ flex: '0 0 280px' }}>
          {loading ? <p>Cargando...</p> : recipes.length === 0 ? <p style={{ color: '#9ca3af' }}>Sin recetas creadas</p> : recipes.map(r => (
            <div key={r.id} onClick={() => loadRecipeDetail(r)} style={{ padding: '0.75rem', border: `1px solid ${selected?.id === r.id ? '#6366F1' : '#e5e7eb'}`, borderRadius: 8, marginBottom: '0.5rem', background: selected?.id === r.id ? '#EEF2FF' : '#fff', cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</span>
                <button onClick={e => { e.stopPropagation(); handleArchive(r) }} title="Archivar" style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 14, color: '#9ca3af' }}>🗑</button>
              </div>
              {r.description && <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>{r.description}</p>}
            </div>
          ))}
        </div>

        {/* Detail panel */}
        {selected && (
          <div style={{ flex: 1, minWidth: 400 }}>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '1rem', background: '#fff' }}>
              <h3 style={{ marginTop: 0 }}>{selected.name}</h3>

              {/* Drafts */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <h4 style={{ margin: 0 }}>📝 Borradores (CA-05: editables)</h4>
                <button onClick={handleCreateDraft} disabled={saving} style={{ padding: '0.3rem 0.75rem', border: '1px solid #6366F1', borderRadius: 6, background: '#fff', color: '#6366F1', cursor: 'pointer', fontSize: 13 }}>+ Borrador</button>
              </div>

              {drafts.map(d => (
                <div key={d.id} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: '0.5rem', marginBottom: '0.5rem', fontSize: 13 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Borrador {new Date(d.created_at).toLocaleDateString()}</span>
                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                      <button onClick={() => { setEditDraft(d); setDraftSystem(d.prompt_system || ''); setDraftUser(d.prompt_user || '') }} style={{ padding: '2px 8px', border: '1px solid #d1d5db', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12 }}>✏️ Editar</button>
                      <button onClick={() => handleSnapshot(d.id)} disabled={saving} style={{ padding: '2px 8px', border: '1px solid #10B981', borderRadius: 4, background: '#fff', color: '#10B981', cursor: 'pointer', fontSize: 12 }}>📌 Snapshot</button>
                    </div>
                  </div>
                </div>
              ))}

              {/* Draft editor */}
              {editDraft && (
                <div style={{ border: '1px solid #6366F1', borderRadius: 8, padding: '0.75rem', marginTop: '0.75rem', background: '#FAFBFF' }}>
                  <h4 style={{ margin: '0 0 0.5rem' }}>Editando borrador</h4>
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#6b7280', marginBottom: 4 }}>Prompt Sistema</label>
                  <textarea value={draftSystem} onChange={e => setDraftSystem(e.target.value)} rows={4} placeholder="Instrucciones generales para el AI. Ej: Eres un experto contable..." style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontFamily: 'monospace', fontSize: 13, resize: 'vertical' }} />
                  <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#6b7280', marginTop: '0.5rem', marginBottom: 4 }}>Prompt Extracción (usa {'{text}'}, {'{tipo}'}, {'{fields}'} como variables)</label>
                  <textarea value={draftUser} onChange={e => setDraftUser(e.target.value)} rows={4} placeholder="Instrucciones para extracción de campos. Dejar vacío para usar el prompt por defecto." style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: 6, fontFamily: 'monospace', fontSize: 13, resize: 'vertical' }} />
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <button onClick={handleSaveDraft} disabled={saving} style={{ padding: '0.4rem 1rem', background: '#6366F1', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>{saving ? '...' : '💾 Guardar'}</button>
                    <button onClick={() => setEditDraft(null)} style={{ padding: '0.4rem 1rem', background: '#e5e7eb', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>Cancelar</button>
                  </div>
                </div>
              )}

              {/* Snapshots — CA-05: read-only */}
              <h4 style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>📌 Snapshots (CA-05: inmutables)</h4>
              {snapshots.length === 0 ? <p style={{ color: '#9ca3af', fontSize: 13 }}>Sin snapshots. Crea un borrador y genera un snapshot para usar en procesamiento.</p> : snapshots.map(s => (
                <div key={s.id} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: '0.5rem', marginBottom: '0.5rem', fontSize: 13, background: '#F0FDF4' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 600 }}>{s.version_tag || 'Sin tag'}</span>
                    <span style={{ color: '#6b7280' }}>{new Date(s.created_at).toLocaleString()}</span>
                  </div>
                  <details style={{ marginTop: 4 }}>
                    <summary style={{ cursor: 'pointer', color: '#6366F1', fontSize: 12 }}>Ver contenido</summary>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, background: '#f9fafb', padding: '0.5rem', borderRadius: 4, marginTop: 4 }}>{JSON.stringify(s.content_json, null, 2)}</pre>
                  </details>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
