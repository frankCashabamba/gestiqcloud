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

  const loadRecipes = async () => {
    setLoading(true)
    try {
      setRecipes(await fetchRecipes())
    } catch {
      setError('No se pudieron cargar las plantillas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRecipes()
  }, [])

  const loadRecipeDetail = async (recipe: Recipe) => {
    setSelected(recipe)
    setEditDraft(null)
    try {
      const [draftItems, snapshotItems] = await Promise.all([fetchDrafts(recipe.id), fetchSnapshots(recipe.id)])
      setDrafts(draftItems)
      setSnapshots(snapshotItems)
    } catch {
      setError('No se pudieron cargar los detalles de la plantilla.')
    }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setSaving(true)
    try {
      const created = await createRecipe({ name: newName.trim(), description: newDesc || undefined })
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      await loadRecipes()
      await loadRecipeDetail(created)
    } catch {
      setError('No se pudo crear la plantilla.')
    } finally {
      setSaving(false)
    }
  }

  const handleArchive = async (recipe: Recipe) => {
    try {
      await updateRecipe(recipe.id, { archived: true } as Partial<Recipe>)
      await loadRecipes()
      if (selected?.id === recipe.id) {
        setSelected(null)
        setDrafts([])
        setSnapshots([])
        setEditDraft(null)
      }
    } catch {
      setError('No se pudo archivar la plantilla.')
    }
  }

  const handleCreateDraft = async () => {
    if (!selected) return
    setSaving(true)
    try {
      const draft = await createDraft(selected.id, {})
      setDrafts(prev => [draft, ...prev])
      setEditDraft(draft)
      setDraftSystem(draft.prompt_system || '')
      setDraftUser(draft.prompt_user || '')
    } catch {
      setError('No se pudo crear un borrador.')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveDraft = async () => {
    if (!editDraft) return
    setSaving(true)
    try {
      const updated = await updateDraft(editDraft.id, { prompt_system: draftSystem, prompt_user: draftUser } as Partial<RecipeDraft>)
      setEditDraft(updated)
      setDrafts(prev => prev.map(draft => draft.id === updated.id ? updated : draft))
    } catch {
      setError('No se pudo guardar el borrador.')
    } finally {
      setSaving(false)
    }
  }

  const handleSnapshot = async (draftId: string) => {
    setSaving(true)
    try {
      const tag = `v${snapshots.length + 1}`
      const snapshot = await createSnapshot(draftId, tag)
      setSnapshots(prev => [snapshot, ...prev])
    } catch {
      setError('No se pudo guardar la version.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <style>{`
        @media (max-width: 980px) {
          .recipe-manager__layout {
            grid-template-columns: minmax(0, 1fr) !important;
          }
        }
        @media (max-width: 640px) {
          .recipe-manager {
            padding: 1rem !important;
          }
          .recipe-manager__hero {
            padding: 1rem !important;
          }
          .recipe-manager__top-actions {
            width: 100%;
          }
          .recipe-manager__top-actions button {
            flex: 1;
          }
        }
      `}</style>

      <div className="recipe-manager" style={{ padding: '1.5rem', display: 'grid', gap: '1rem' }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            width: 'fit-content',
            cursor: 'pointer',
            border: '1px solid #dbe4f0',
            background: '#fff',
            fontSize: 14,
            color: '#0f172a',
            padding: '0.5rem 0.8rem',
            borderRadius: 12,
            boxShadow: '0 8px 18px rgba(15, 23, 42, 0.04)',
          }}
        >
          {'<-'} Volver
        </button>

        <section
          className="recipe-manager__hero"
          style={{
            borderRadius: 28,
            padding: '1.35rem',
            background: 'linear-gradient(135deg, #fffdf8 0%, #eef6ff 52%, #ffffff 100%)',
            border: '1px solid #e2e8f0',
            boxShadow: '0 22px 40px rgba(15, 23, 42, 0.06)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div style={{ maxWidth: 760 }}>
              <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#0f766e', marginBottom: 6 }}>
                Configuracion avanzada
              </div>
              <h1 style={{ margin: 0, fontSize: 30, lineHeight: 1.05, color: '#0f172a' }}>Plantillas de lectura</h1>
              <p style={{ margin: '0.55rem 0 0', fontSize: 15, color: '#475569', maxWidth: 700 }}>
                Las plantillas ayudan a orientar la lectura de determinados formatos. Puedes crear borradores, probar ajustes y conservar versiones estables para reutilizarlas en futuras importaciones.
              </p>
            </div>
            <div className="recipe-manager__top-actions" style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <button onClick={() => setShowCreate(true)} style={primaryBtn}>Nueva plantilla</button>
            </div>
          </div>
        </section>

        {error && (
          <div style={{ color: '#991B1B', background: '#FEF2F2', padding: '0.8rem 0.9rem', borderRadius: 14, border: '1px solid #fecaca', fontSize: 13 }}>
            {error}
            <button onClick={() => setError('')} style={{ marginLeft: 12, border: 'none', background: 'none', cursor: 'pointer', color: '#991B1B', fontWeight: 800 }}>
              Cerrar
            </button>
          </div>
        )}

        {showCreate && (
          <section style={{ padding: '1rem', border: '1px solid #dbe4f0', borderRadius: 20, background: '#fff', boxShadow: '0 14px 26px rgba(15, 23, 42, 0.04)' }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', marginBottom: '0.75rem' }}>Crear plantilla</div>
            <div style={{ display: 'grid', gap: '0.65rem' }}>
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="Nombre de la plantilla"
                style={inputStyle}
              />
              <input
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                placeholder="Descripcion breve"
                style={inputStyle}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.85rem', flexWrap: 'wrap' }}>
              <button onClick={handleCreate} disabled={saving} style={primaryBtn}>{saving ? 'Creando...' : 'Crear plantilla'}</button>
              <button onClick={() => setShowCreate(false)} style={secondaryBtn}>Cancelar</button>
            </div>
          </section>
        )}

        <div className="recipe-manager__layout" style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr)', gap: '1rem' }}>
          <aside
            style={{
              borderRadius: 24,
              border: '1px solid #e2e8f0',
              background: '#fff',
              boxShadow: '0 18px 36px rgba(15, 23, 42, 0.05)',
              padding: '1rem',
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a' }}>Plantillas disponibles</div>
            <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
              Selecciona una plantilla para ver sus borradores y sus versiones guardadas.
            </div>

            <div style={{ marginTop: '0.85rem', display: 'grid', gap: '0.65rem' }}>
              {loading ? (
                <div style={{ color: '#64748b', fontSize: 13 }}>Cargando plantillas...</div>
              ) : recipes.length === 0 ? (
                <div style={{ padding: '1rem', borderRadius: 14, background: '#f8fafc', color: '#64748b', fontSize: 13 }}>
                  Aun no hay plantillas creadas.
                </div>
              ) : (
                recipes.map(recipe => (
                  <button
                    key={recipe.id}
                    onClick={() => { void loadRecipeDetail(recipe) }}
                    style={{
                      textAlign: 'left',
                      padding: '0.85rem 0.9rem',
                      borderRadius: 16,
                      border: `1px solid ${selected?.id === recipe.id ? '#0f766e' : '#e5e7eb'}`,
                      background: selected?.id === recipe.id ? '#ecfdf5' : '#fff',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'start' }}>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 800, color: '#0f172a' }}>{recipe.name}</div>
                        {recipe.description && <div style={{ marginTop: 4, fontSize: 12, color: '#64748b' }}>{recipe.description}</div>}
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 800, color: selected?.id === recipe.id ? '#0f766e' : '#94a3b8' }}>
                        {selected?.id === recipe.id ? 'ACTIVA' : ''}
                      </span>
                    </div>
                    <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', gap: '0.5rem', alignItems: 'center' }}>
                      <span style={{ fontSize: 11, color: '#94a3b8' }}>{new Date(recipe.updated_at).toLocaleDateString()}</span>
                      <span
                        onClick={(event) => {
                          event.stopPropagation()
                          void handleArchive(recipe)
                        }}
                        style={{ fontSize: 12, color: '#991b1b', fontWeight: 700 }}
                      >
                        Archivar
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>

          <section
            style={{
              borderRadius: 24,
              border: '1px solid #e2e8f0',
              background: '#fff',
              boxShadow: '0 18px 36px rgba(15, 23, 42, 0.05)',
              padding: '1rem',
            }}
          >
            {!selected ? (
              <div style={{ padding: '1.4rem', borderRadius: 18, background: '#f8fafc', color: '#64748b' }}>
                Selecciona una plantilla para ver su configuracion.
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a' }}>{selected.name}</div>
                    <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
                      {selected.description || 'Sin descripcion'}
                    </div>
                  </div>
                  <button onClick={handleCreateDraft} disabled={saving} style={secondaryBtn}>
                    {saving ? 'Creando...' : 'Nuevo borrador'}
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.8rem' }}>
                  <div style={summaryCard}>
                    <div style={summaryLabel}>Borradores</div>
                    <div style={summaryValue}>{drafts.length}</div>
                    <div style={summaryNote}>Versiones editables en trabajo</div>
                  </div>
                  <div style={summaryCard}>
                    <div style={summaryLabel}>Versiones guardadas</div>
                    <div style={summaryValue}>{snapshots.length}</div>
                    <div style={summaryNote}>Snapshots listos para reutilizar</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gap: '1rem' }}>
                  <section style={innerSection}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.75rem' }}>
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Borradores</div>
                        <div style={{ marginTop: 4, fontSize: 13, color: '#64748b' }}>
                          Ajusta aqui el texto de apoyo para esta plantilla antes de publicar una version.
                        </div>
                      </div>
                    </div>

                    {drafts.length === 0 ? (
                      <div style={{ padding: '0.9rem', borderRadius: 14, background: '#f8fafc', color: '#64748b', fontSize: 13 }}>
                        Esta plantilla todavia no tiene borradores.
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gap: '0.7rem' }}>
                        {drafts.map(draft => (
                          <div key={draft.id} style={{ border: '1px solid #e5e7eb', borderRadius: 16, padding: '0.8rem 0.9rem', background: '#fff' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                              <div>
                                <div style={{ fontSize: 14, fontWeight: 800, color: '#0f172a' }}>
                                  Borrador del {new Date(draft.created_at).toLocaleDateString()}
                                </div>
                                <div style={{ marginTop: 4, fontSize: 12, color: '#64748b' }}>
                                  Ultima actualizacion: {new Date(draft.updated_at).toLocaleString()}
                                </div>
                              </div>
                              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <button
                                  onClick={() => {
                                    setEditDraft(draft)
                                    setDraftSystem(draft.prompt_system || '')
                                    setDraftUser(draft.prompt_user || '')
                                  }}
                                  style={secondaryBtn}
                                >
                                  Editar
                                </button>
                                <button onClick={() => { void handleSnapshot(draft.id) }} disabled={saving} style={successBtn}>
                                  Guardar version
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {editDraft && (
                      <div style={{ marginTop: '1rem', border: '1px solid #c7d2fe', borderRadius: 18, padding: '1rem', background: '#fafbff' }}>
                        <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', marginBottom: '0.75rem' }}>Editar borrador</div>
                        <div style={{ display: 'grid', gap: '0.75rem' }}>
                          <div>
                            <label style={fieldLabel}>Instrucciones generales</label>
                            <textarea
                              value={draftSystem}
                              onChange={e => setDraftSystem(e.target.value)}
                              rows={5}
                              placeholder="Indicaciones generales para interpretar este tipo de documento."
                              style={textareaStyle}
                            />
                          </div>
                          <div>
                            <label style={fieldLabel}>Instrucciones de extraccion</label>
                            <textarea
                              value={draftUser}
                              onChange={e => setDraftUser(e.target.value)}
                              rows={6}
                              placeholder="Indica como extraer los datos relevantes. Puedes usar {text}, {tipo} y {fields}."
                              style={textareaStyle}
                            />
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.85rem', flexWrap: 'wrap' }}>
                          <button onClick={handleSaveDraft} disabled={saving} style={primaryBtn}>
                            {saving ? 'Guardando...' : 'Guardar cambios'}
                          </button>
                          <button onClick={() => setEditDraft(null)} style={secondaryBtn}>Cancelar</button>
                        </div>
                      </div>
                    )}
                  </section>

                  <section style={innerSection}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', marginBottom: '0.75rem' }}>Versiones guardadas</div>
                    {snapshots.length === 0 ? (
                      <div style={{ padding: '0.9rem', borderRadius: 14, background: '#f8fafc', color: '#64748b', fontSize: 13 }}>
                        Todavia no hay versiones guardadas para esta plantilla.
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gap: '0.7rem' }}>
                        {snapshots.map(snapshot => (
                          <div key={snapshot.id} style={{ border: '1px solid #d1fae5', borderRadius: 16, padding: '0.8rem 0.9rem', background: '#f0fdf4' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                              <div>
                                <div style={{ fontSize: 14, fontWeight: 800, color: '#0f172a' }}>{snapshot.version_tag || 'Sin nombre'}</div>
                                <div style={{ marginTop: 4, fontSize: 12, color: '#64748b' }}>
                                  Guardada el {new Date(snapshot.created_at).toLocaleString()}
                                </div>
                              </div>
                            </div>
                            <details style={{ marginTop: 8 }}>
                              <summary style={{ cursor: 'pointer', color: '#0f766e', fontSize: 12, fontWeight: 700 }}>
                                Ver contenido
                              </summary>
                              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, background: '#fff', padding: '0.75rem', borderRadius: 10, marginTop: 8, border: '1px solid #d1fae5', overflowX: 'auto' }}>
                                {JSON.stringify(snapshot.content_json, null, 2)}
                              </pre>
                            </details>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </>
  )
}

const primaryBtn: React.CSSProperties = {
  padding: '0.78rem 1rem',
  border: 'none',
  borderRadius: 14,
  cursor: 'pointer',
  background: 'linear-gradient(135deg, #0f766e 0%, #0d9488 100%)',
  color: '#fff',
  fontSize: 14,
  fontWeight: 800,
  boxShadow: '0 14px 28px rgba(13, 148, 136, 0.22)',
}

const secondaryBtn: React.CSSProperties = {
  padding: '0.7rem 0.95rem',
  border: '1px solid #cbd5e1',
  borderRadius: 14,
  cursor: 'pointer',
  background: '#fff',
  color: '#334155',
  fontSize: 13,
  fontWeight: 800,
}

const successBtn: React.CSSProperties = {
  padding: '0.7rem 0.95rem',
  border: '1px solid #10b981',
  borderRadius: 14,
  cursor: 'pointer',
  background: '#ecfdf5',
  color: '#047857',
  fontSize: 13,
  fontWeight: 800,
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.75rem 0.85rem',
  border: '1px solid #d1d5db',
  borderRadius: 14,
  fontSize: 14,
  color: '#0f172a',
}

const textareaStyle: React.CSSProperties = {
  width: '100%',
  padding: '0.75rem 0.85rem',
  border: '1px solid #d1d5db',
  borderRadius: 14,
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: 13,
  color: '#0f172a',
  resize: 'vertical',
}

const fieldLabel: React.CSSProperties = {
  display: 'block',
  fontSize: 13,
  fontWeight: 700,
  color: '#475569',
  marginBottom: 6,
}

const summaryCard: React.CSSProperties = {
  padding: '0.95rem 1rem',
  borderRadius: 18,
  background: '#fff',
  border: '1px solid rgba(148, 163, 184, 0.16)',
}

const summaryLabel: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: '#64748b',
}

const summaryValue: React.CSSProperties = {
  marginTop: 8,
  fontSize: 28,
  fontWeight: 800,
  color: '#0f172a',
}

const summaryNote: React.CSSProperties = {
  marginTop: 4,
  fontSize: 12,
  color: '#64748b',
}

const innerSection: React.CSSProperties = {
  border: '1px solid #e5e7eb',
  borderRadius: 20,
  background: '#fff',
  padding: '1rem',
}
