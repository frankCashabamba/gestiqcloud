import React, { useCallback, useEffect, useState } from 'react'
import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast } from '../../../shared/toast'
import ConfirmActionModal from './ConfirmActionModal'
import {
    listImportTemplates,
    deleteImportTemplate,
    listTemplatesV2,
    createTemplateV2,
    updateTemplateV2,
    deleteTemplateV2,
    simulateTemplate,
    type ImportTemplate,
    listTemplateFields,
} from '../services/templates'
import type { TemplateV2, ImportTemplateV2 } from '@api-types/imports'
import { useAuth } from '../../../auth/AuthContext'

interface Props {
    isOpen: boolean
    onClose: () => void
    onSelect: (template: ImportTemplate) => void
    sourceType: string
}

const LANGUAGES = ['es', 'en', 'pt'] as const
const STEPS = ['info', 'mapping', 'transforms', 'dedupe', 'simulate'] as const
type StepKey = typeof STEPS[number]

const STEP_LABELS: Record<StepKey, string> = {
    info: 'Info',
    mapping: 'Mapeo',
    transforms: 'Transforms',
    dedupe: 'Dedupe & Output',
    simulate: 'Simular',
}

type WizardState = {
    step: number
    name: string
    source_type: string
    match: { filename_regex: string; language: string[]; priority: number }
    map: Record<string, string[]>
    header_normalization: { strip_accents: boolean; synonyms: Record<string, Record<string, string[]>> }
    transforms: Record<string, { type?: 'number' | 'date' | 'string'; expr?: string; fallback?: unknown }>
    defaults: Record<string, string>
    dedupe_keys: string[]
    output: { doc_type: string }
    simulationInput: string
    simulationResults: Record<string, unknown>[] | null
}

const emptyWizard = (sourceType: string): WizardState => ({
    step: 0,
    name: '',
    source_type: sourceType,
    match: { filename_regex: '', language: ['es'], priority: 50 },
    map: {},
    header_normalization: { strip_accents: true, synonyms: {} },
    transforms: {},
    defaults: {},
    dedupe_keys: [],
    output: { doc_type: 'product' },
    simulationInput: '[\n  {"producto": "Arroz", "precio": "5.50", "cantidad": "100"}\n]',
    simulationResults: null,
})

export default function TemplateManager({ isOpen, onClose, onSelect, sourceType }: Props) {
    const { t } = useTranslation('importer')
    const toast = useToast()
    const { token } = useAuth() as { token: string | null }

    const [templates, setTemplates] = useState<ImportTemplate[]>([])
    const [templatesV2, setTemplatesV2] = useState<ImportTemplateV2[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [deletingId, setDeletingId] = useState<string | null>(null)
    const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

    const [wizardOpen, setWizardOpen] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [wiz, setWiz] = useState<WizardState>(emptyWizard(sourceType))
    const [canonicalFields, setCanonicalFields] = useState<string[]>([])
    const [fieldsSeeded, setFieldsSeeded] = useState<boolean>(false)
    const [fieldsError, setFieldsError] = useState<string | null>(null)
    const [availableSourceTypes, setAvailableSourceTypes] = useState<string[]>([])
    const [saving, setSaving] = useState(false)
    const [simulating, setSimulating] = useState(false)
    const prevSourceType = useRef<string>(sourceType)

    const loadTemplates = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const [legacy, v2] = await Promise.all([
                listImportTemplates(sourceType, token || undefined).catch(() => []),
                listTemplatesV2(sourceType, token || undefined).catch(() => []),
            ])
            setTemplates(legacy)
            setTemplatesV2(v2)
        } catch (err: any) {
            setError(err?.message || 'Error loading templates')
        } finally {
            setLoading(false)
        }
    }, [sourceType, token])

    useEffect(() => {
        if (isOpen) loadTemplates()
    }, [isOpen, loadTemplates])

    // Load available source types (only those with fields configured)
    useEffect(() => {
        let cancelled = false
        async function probeTypes() {
            try {
                const res = await listTemplateFields('*', token || undefined)
                const types = Array.isArray((res as any).source_types) ? (res as any).source_types : []
                if (!cancelled) {
                    setAvailableSourceTypes(types)
                    if (types.length > 0 && !types.includes(wiz.source_type)) {
                        setWiz(p => ({ ...p, source_type: types[0] }))
                    }
                }
            } catch (e:any) {
                if (!cancelled) {
                    setAvailableSourceTypes([])
                }
            }
        }
        if (isOpen) probeTypes()
        return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, token])

    // Reset map when user cambia el tipo de fuente en el wizard
    useEffect(() => {
        if (wiz.source_type !== prevSourceType.current) {
            prevSourceType.current = wiz.source_type
            setWiz(p => ({ ...p, map: {} }))
        }
    }, [wiz.source_type])

    // load canonical fields by wizard source type
    useEffect(() => {
        let cancelled = false
        async function loadFields() {
            try {
                if (!wiz.source_type) return
                const res = await listTemplateFields(wiz.source_type, token || undefined)
                if (!cancelled && Array.isArray(res.fields)) {
                    setCanonicalFields(res.fields)
                    setFieldsSeeded(!!res.seeded)
                    setFieldsError(null)
                    return
                }
            } catch (err: any) {
                if (!cancelled) {
                    setFieldsError(err?.message || 'No hay campos configurados para este tipo')
                }
            }
            if (!cancelled) {
                setCanonicalFields([])
                setFieldsSeeded(false)
                setFieldsError(prev => prev || 'No hay campos configurados para este tipo')
            }
        }
        if (isOpen) loadFields()
        return () => { cancelled = true }
    }, [wiz.source_type, token, isOpen])

    const handleDelete = (id: string, isSystem: boolean) => {
        if (isSystem) {
            toast.warning(t('templateManager.errors.cannotDeleteSystemTemplate'))
            return
        }
        setConfirmDeleteId(id)
    }

    const confirmDelete = async () => {
        if (!confirmDeleteId) return
        setDeletingId(confirmDeleteId)
        try {
            const isV2 = templatesV2.some(t => t.id === confirmDeleteId)
            if (isV2) {
                await deleteTemplateV2(confirmDeleteId, token || undefined)
            } else {
                await deleteImportTemplate(confirmDeleteId, token || undefined)
            }
            await loadTemplates()
        } catch (err: any) {
            toast.error(err?.message || 'Error deleting template')
        } finally {
            setDeletingId(null)
            setConfirmDeleteId(null)
        }
    }

    const handleSelect = (template: ImportTemplate) => {
        onSelect(template)
        onClose()
    }

    const openCreateWizard = () => {
        setEditingId(null)
        prevSourceType.current = sourceType
        setWiz(emptyWizard(sourceType))
        setWizardOpen(true)
    }

    const openEditWizard = (tpl: ImportTemplateV2) => {
        setEditingId(tpl.id)
        prevSourceType.current = tpl.source_type
        const m = tpl.mappings || {} as TemplateV2
        setWiz({
            step: 0,
            name: tpl.name,
            source_type: tpl.source_type,
            match: {
                filename_regex: m.match?.filename_regex || '',
                language: m.match?.language || ['es'],
                priority: m.match?.priority ?? 50,
            },
            map: (m.map || {}) as Record<string, string[]>,
            header_normalization: {
                strip_accents: m.header_normalization?.strip_accents ?? true,
                synonyms: (m.header_normalization?.synonyms || {}) as Record<string, Record<string, string[]>>,
            },
            transforms: (m.transforms || {}) as Record<string, { type?: 'number' | 'date' | 'string'; expr?: string; fallback?: unknown }>,
            defaults: (m.defaults || {}) as Record<string, string>,
            dedupe_keys: m.dedupe_keys || [],
            output: { doc_type: m.output?.doc_type || 'product' },
            simulationInput: '[\n  {"producto": "Arroz", "precio": "5.50", "cantidad": "100"}\n]',
            simulationResults: null,
        })
        setWizardOpen(true)
    }

    const buildTemplateV2 = (): TemplateV2 => ({
        template_version: 2,
        match: wiz.match.filename_regex ? wiz.match : undefined,
        extract: { mode: 'excel_grid', all_sheets: true },
        header_normalization: wiz.header_normalization,
        map: wiz.map,
        transforms: wiz.transforms,
        defaults: wiz.defaults,
        dedupe_keys: wiz.dedupe_keys.length > 0 ? wiz.dedupe_keys : undefined,
        output: wiz.output,
    })

    const handleSave = async () => {
        if (!wiz.name.trim()) {
            toast.error('Name is required')
            return
        }
        setSaving(true)
        try {
            const payload = {
                name: wiz.name,
                source_type: wiz.source_type,
                mappings: buildTemplateV2(),
            }
            if (editingId) {
                await updateTemplateV2(editingId, payload, token || undefined)
            } else {
                await createTemplateV2(payload, token || undefined)
            }
            toast.success(editingId ? 'Template updated' : 'Template created')
            setWizardOpen(false)
            await loadTemplates()
        } catch (err: any) {
            toast.error(err?.message || 'Error saving template')
        } finally {
            setSaving(false)
        }
    }

    const handleSimulate = async () => {
        setSimulating(true)
        try {
            const rows = JSON.parse(wiz.simulationInput)
            if (!Array.isArray(rows)) throw new Error('Must be a JSON array')
            if (editingId) {
                const res = await simulateTemplate(editingId, rows, token || undefined)
                setWiz(prev => ({ ...prev, simulationResults: res.results }))
            } else {
                toast.warning('Save the template first to simulate')
            }
        } catch (err: any) {
            toast.error(err?.message || 'Simulation error')
        } finally {
            setSimulating(false)
        }
    }

    // Wizard field helpers
    const updateMap = (field: string, aliases: string[]) => {
        setWiz(prev => ({ ...prev, map: { ...prev.map, [field]: aliases } }))
    }
    const removeMapField = (field: string) => {
        setWiz(prev => {
            const m = { ...prev.map }
            delete m[field]
            return { ...prev, map: m }
        })
    }
    const updateTransform = (field: string, val: { type?: 'number' | 'date' | 'string'; expr?: string; fallback?: unknown }) => {
        setWiz(prev => ({ ...prev, transforms: { ...prev.transforms, [field]: val } }))
    }
    const removeTransform = (field: string) => {
        setWiz(prev => {
            const tr = { ...prev.transforms }
            delete tr[field]
            return { ...prev, transforms: tr }
        })
    }

    if (!isOpen) return null

    // ===== WIZARD MODAL =====
    if (wizardOpen) {
        const step = STEPS[wiz.step] || 'info'
        return (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
                    {/* Header */}
                    <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-gray-900">
                            {editingId ? 'Edit Template V2' : 'Create Template V2'}
                        </h3>
                        <button onClick={() => setWizardOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
                    </div>

                    {/* Step Tabs */}
                    <div className="flex border-b border-gray-200 px-6">
                        {STEPS.map((s, i) => (
                            <button
                                key={s}
                                onClick={() => setWiz(prev => ({ ...prev, step: i }))}
                                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                                    wiz.step === i
                                        ? 'border-blue-600 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700'
                                }`}
                            >
                                {STEP_LABELS[s]}
                            </button>
                        ))}
                    </div>

                    {/* Step Content */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {/* STEP: INFO */}
                        {step === 'info' && (
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                                    <input
                                        value={wiz.name}
                                        onChange={e => setWiz(p => ({ ...p, name: e.target.value }))}
                                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500"
                                        placeholder="e.g. PAN KUSI Products"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Source Type</label>
                                    <select
                                        value={wiz.source_type}
                                        onChange={e => setWiz(p => ({ ...p, source_type: e.target.value }))}
                                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                    >
                                        {availableSourceTypes.map(st => (
                                            <option key={st} value={st}>{st.charAt(0).toUpperCase() + st.slice(1)}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Filename Pattern (regex)
                                    </label>
                                    <input
                                        value={wiz.match.filename_regex}
                                        onChange={e => setWiz(p => ({
                                            ...p,
                                            match: { ...p.match, filename_regex: e.target.value },
                                        }))}
                                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
                                        placeholder="PAN KUSI.*\.xlsx$"
                                    />
                                </div>
                                <div className="flex gap-4">
                                    <div className="flex-1">
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Languages</label>
                                        <div className="flex gap-2">
                                            {LANGUAGES.map(lang => (
                                                <label key={lang} className="flex items-center gap-1 text-sm">
                                                    <input
                                                        type="checkbox"
                                                        checked={wiz.match.language.includes(lang)}
                                                        onChange={e => {
                                                            const langs = e.target.checked
                                                                ? [...wiz.match.language, lang]
                                                                : wiz.match.language.filter(l => l !== lang)
                                                            setWiz(p => ({ ...p, match: { ...p.match, language: langs } }))
                                                        }}
                                                    />
                                                    {lang.toUpperCase()}
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                                        <input
                                            type="number"
                                            value={wiz.match.priority}
                                            onChange={e => setWiz(p => ({
                                                ...p,
                                                match: { ...p.match, priority: Number(e.target.value) || 50 },
                                            }))}
                                            className="w-24 border border-gray-300 rounded px-3 py-2 text-sm"
                                        />
                                    </div>
                                </div>
                                <label className="flex items-center gap-2 text-sm">
                                    <input
                                        type="checkbox"
                                        checked={wiz.header_normalization.strip_accents}
                                        onChange={e => setWiz(p => ({
                                            ...p,
                                            header_normalization: { ...p.header_normalization, strip_accents: e.target.checked },
                                        }))}
                                    />
                                    Strip accents in headers
                                </label>
                            </div>
                        )}

                        {/* STEP: MAPPING */}
                        {step === 'mapping' && (
                            <div className="space-y-4">
                                {fieldsError && (
                                    <div className="bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded text-sm">
                                        {fieldsError}
                                    </div>
                                )}
                                {!fieldsError && fieldsSeeded && canonicalFields.length > 0 && (
                                    <div className="bg-blue-50 border border-blue-200 text-blue-800 px-3 py-2 rounded text-sm">
                                        Campos base cargados automáticamente para este tipo. Ajusta aliases y guarda la plantilla.
                                    </div>
                                )}
                                <p className="text-sm text-gray-600">
                                    Map each target field to one or more source column aliases (multilingual).
                                </p>
                                {canonicalFields.length === 0 && (
                                    <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                                        No se encontraron campos para este tipo. Intenta recargar o contacta a un admin para agregar el catálogo global.
                                    </div>
                                )}
                                <div className="border border-gray-200 rounded overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-3 py-2 text-left text-gray-600">Target Field</th>
                                                <th className="px-3 py-2 text-left text-gray-600">Source Aliases (comma separated)</th>
                                                <th className="px-3 py-2 w-10"></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {canonicalFields.map(field => {
                                                const aliases = wiz.map[field] || []
                                                return (
                                                    <tr key={field} className="border-t border-gray-100">
                                                        <td className="px-3 py-2 font-mono text-gray-800">{field}</td>
                                                        <td className="px-3 py-2">
                                                            <input
                                                                value={aliases.join(', ')}
                                                                onChange={e => {
                                                                    const vals = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                                                                    if (vals.length > 0) {
                                                                        updateMap(field, vals)
                                                                    } else {
                                                                        removeMapField(field)
                                                                    }
                                                                }}
                                                                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                                                                placeholder="producto, product, nombre"
                                                            />
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            {aliases.length > 0 && (
                                                                <button
                                                                    onClick={() => removeMapField(field)}
                                                                    className="text-red-400 hover:text-red-600 text-xs"
                                                                >✕</button>
                                                            )}
                                                        </td>
                                                    </tr>
                                                )
                                            })}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Synonym Dictionary */}
                                <div className="mt-4">
                                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Synonym Dictionary (by language)</h4>
                                    {LANGUAGES.map(lang => (
                                        <div key={lang} className="mb-3">
                                            <span className="text-xs font-semibold text-gray-500 uppercase">{lang}</span>
                                            <div className="mt-1 space-y-1">
                                                {Object.entries(wiz.header_normalization.synonyms[lang] || {}).map(([canon, syns]) => (
                                                    <div key={canon} className="flex items-center gap-2 text-xs">
                                                        <span className="font-mono text-gray-700 w-24">{canon}</span>
                                                        <input
                                                            value={(syns as string[]).join(', ')}
                                                            onChange={e => {
                                                                const vals = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                                                                setWiz(prev => ({
                                                                    ...prev,
                                                                    header_normalization: {
                                                                        ...prev.header_normalization,
                                                                        synonyms: {
                                                                            ...prev.header_normalization.synonyms,
                                                                            [lang]: {
                                                                                ...prev.header_normalization.synonyms[lang],
                                                                                [canon]: vals,
                                                                            },
                                                                        },
                                                                    },
                                                                }))
                                                            }}
                                                            className="flex-1 border border-gray-200 rounded px-2 py-0.5 text-xs"
                                                        />
                                                        <button
                                                            onClick={() => {
                                                                setWiz(prev => {
                                                                    const langSyns = { ...(prev.header_normalization.synonyms[lang] || {}) }
                                                                    delete langSyns[canon]
                                                                    return {
                                                                        ...prev,
                                                                        header_normalization: {
                                                                            ...prev.header_normalization,
                                                                            synonyms: {
                                                                                ...prev.header_normalization.synonyms,
                                                                                [lang]: langSyns,
                                                                            },
                                                                        },
                                                                    }
                                                                })
                                                            }}
                                                            className="text-red-400 hover:text-red-600"
                                                        >✕</button>
                                                    </div>
                                                ))}
                                                <button
                                                    onClick={() => {
                                                        const canon = prompt('Canonical field name:')
                                                        if (!canon) return
                                                        setWiz(prev => ({
                                                            ...prev,
                                                            header_normalization: {
                                                                ...prev.header_normalization,
                                                                synonyms: {
                                                                    ...prev.header_normalization.synonyms,
                                                                    [lang]: {
                                                                        ...prev.header_normalization.synonyms[lang],
                                                                        [canon]: [],
                                                                    },
                                                                },
                                                            },
                                                        }))
                                                    }}
                                                    className="text-xs text-blue-600 hover:text-blue-800"
                                                >+ Add synonym for {lang.toUpperCase()}</button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* STEP: TRANSFORMS */}
                        {step === 'transforms' && (
                            <div className="space-y-4">
                                <p className="text-sm text-gray-600">
                                    Configure transforms (DSL expressions) and default values for fields.
                                </p>

                                <h4 className="text-sm font-semibold text-gray-700">Transforms</h4>
                                <div className="space-y-2">
                                    {Object.entries(wiz.transforms).map(([field, spec]) => (
                                        <div key={field} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                                            <span className="font-mono text-sm text-gray-700 w-28">{field}</span>
                                            <select
                                                value={spec.type || ''}
                                                onChange={e => updateTransform(field, { ...spec, type: (e.target.value || undefined) as 'number' | 'date' | 'string' | undefined })}
                                                className="border border-gray-300 rounded px-2 py-1 text-xs w-24"
                                            >
                                                <option value="">auto</option>
                                                <option value="number">number</option>
                                                <option value="date">date</option>
                                                <option value="string">string</option>
                                            </select>
                                            <input
                                                value={spec.expr || ''}
                                                onChange={e => updateTransform(field, { ...spec, expr: e.target.value || undefined })}
                                                className="flex-1 border border-gray-300 rounded px-2 py-1 text-xs font-mono"
                                                placeholder="coalesce(unit, 'unit')"
                                            />
                                            <input
                                                value={spec.fallback != null ? String(spec.fallback) : ''}
                                                onChange={e => updateTransform(field, { ...spec, fallback: e.target.value || undefined })}
                                                className="w-20 border border-gray-300 rounded px-2 py-1 text-xs"
                                                placeholder="fallback"
                                            />
                                            <button onClick={() => removeTransform(field)} className="text-red-400 hover:text-red-600 text-xs">✕</button>
                                        </div>
                                    ))}
                                    <button
                                        onClick={() => {
                                            const field = prompt('Field name:')
                                            if (field) updateTransform(field, { type: 'number' })
                                        }}
                                        className="text-sm text-blue-600 hover:text-blue-800"
                                    >+ Add transform</button>
                                </div>

                                <h4 className="text-sm font-semibold text-gray-700 mt-6">Defaults</h4>
                                <div className="space-y-2">
                                    {Object.entries(wiz.defaults).map(([field, val]) => (
                                        <div key={field} className="flex items-center gap-2">
                                            <span className="font-mono text-sm text-gray-700 w-28">{field}</span>
                                            <input
                                                value={val}
                                                onChange={e => setWiz(p => ({ ...p, defaults: { ...p.defaults, [field]: e.target.value } }))}
                                                className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                                            />
                                            <button
                                                onClick={() => setWiz(p => {
                                                    const d = { ...p.defaults }
                                                    delete d[field]
                                                    return { ...p, defaults: d }
                                                })}
                                                className="text-red-400 hover:text-red-600 text-xs"
                                            >✕</button>
                                        </div>
                                    ))}
                                    <button
                                        onClick={() => {
                                            const field = prompt('Field name:')
                                            if (field) setWiz(p => ({ ...p, defaults: { ...p.defaults, [field]: '' } }))
                                        }}
                                        className="text-sm text-blue-600 hover:text-blue-800"
                                    >+ Add default</button>
                                </div>
                            </div>
                        )}

                        {/* STEP: DEDUPE & OUTPUT */}
                        {step === 'dedupe' && (
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Dedupe Keys (comma separated)
                                    </label>
                                    <input
                                        value={wiz.dedupe_keys.join(', ')}
                                        onChange={e => setWiz(p => ({
                                            ...p,
                                            dedupe_keys: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
                                        }))}
                                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
                                        placeholder="name, price, stock"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Rows with identical values in these fields will be deduplicated.
                                    </p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Output doc_type</label>
                                    <select
                                        value={wiz.output.doc_type}
                                        onChange={e => setWiz(p => ({ ...p, output: { doc_type: e.target.value } }))}
                                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                    >
                                        <option value="product">product</option>
                                        <option value="invoice">invoice</option>
                                        <option value="expense">expense</option>
                                        <option value="bank_tx">bank_tx</option>
                                        <option value="recipe">recipe</option>
                                    </select>
                                </div>
                            </div>
                        )}

                        {/* STEP: SIMULATE */}
                        {step === 'simulate' && (
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Sample Rows (JSON array)
                                    </label>
                                    <textarea
                                        value={wiz.simulationInput}
                                        onChange={e => setWiz(p => ({ ...p, simulationInput: e.target.value }))}
                                        rows={6}
                                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
                                    />
                                </div>
                                <button
                                    onClick={handleSimulate}
                                    disabled={simulating || !editingId}
                                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
                                >
                                    {simulating ? 'Simulating...' : 'Run Simulation'}
                                </button>
                                {!editingId && (
                                    <p className="text-xs text-amber-600">Save the template first to run simulation.</p>
                                )}
                                {wiz.simulationResults && (
                                    <div className="mt-4">
                                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Results</h4>
                                        <div className="bg-gray-50 rounded border border-gray-200 p-3 max-h-60 overflow-auto">
                                            <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap">
                                                {JSON.stringify(wiz.simulationResults, null, 2)}
                                            </pre>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
                        <div className="flex gap-2">
                            {wiz.step > 0 && (
                                <button
                                    onClick={() => setWiz(p => ({ ...p, step: p.step - 1 }))}
                                    className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded text-sm"
                                >Back</button>
                            )}
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setWizardOpen(false)}
                                className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded text-sm"
                            >Cancel</button>
                            {wiz.step < STEPS.length - 1 ? (
                                <button
                                    onClick={() => setWiz(p => ({ ...p, step: p.step + 1 }))}
                                    disabled={canonicalFields.length === 0 && wiz.step === 1}
                                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
                                >Next</button>
                            ) : (
                                <button
                                    onClick={handleSave}
                                    disabled={saving || canonicalFields.length === 0}
                                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
                                >{saving ? 'Saving...' : 'Save Template'}</button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // ===== MAIN LIST MODAL =====
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-gray-900">{t('templateManager.title')}</h3>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={openCreateWizard}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition"
                        >+ Template V2</button>
                        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">✕</button>
                    </div>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading && (
                        <div className="text-center py-8 text-gray-600">{t('templateManager.loading')}</div>
                    )}
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">{error}</div>
                    )}
                    {!loading && !error && templates.length === 0 && templatesV2.length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                            {t('templateManager.empty.noTemplates')}
                            <br />
                            <span className="text-sm">{t('templateManager.empty.createFromMapping')}</span>
                        </div>
                    )}

                    {!loading && !error && (templates.length > 0 || templatesV2.length > 0) && (
                        <div className="space-y-6">
                            {/* V2 Templates */}
                            {templatesV2.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-semibold text-gray-500 mb-3 uppercase tracking-wide">Templates V2</h4>
                                    <div className="grid md:grid-cols-2 gap-4">
                                        {templatesV2.map(tpl => (
                                            <div key={tpl.id} className="border border-blue-200 rounded-lg p-4 hover:shadow-md transition bg-blue-50/30">
                                                <div className="flex items-start justify-between mb-2">
                                                    <h4 className="font-semibold text-gray-900">{tpl.name}</h4>
                                                    <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded font-medium">V2</span>
                                                </div>
                                                <div className="text-xs text-gray-500 mb-2">
                                                    {tpl.source_type} · {tpl.mappings?.output?.doc_type || 'generic'}
                                                </div>
                                                {tpl.mappings?.map && (
                                                    <div className="bg-white rounded p-2 mb-3 text-xs space-y-1 max-h-24 overflow-y-auto border border-gray-100">
                                                        {Object.entries(tpl.mappings.map).slice(0, 5).map(([target, aliases]) => (
                                                            <div key={target} className="flex items-center gap-2">
                                                                <span className="text-gray-600 font-mono">{target}</span>
                                                                <span className="text-gray-400">←</span>
                                                                <span className="text-gray-900">{(aliases as string[]).join(', ')}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleSelect({
                                                            id: tpl.id,
                                                            name: tpl.name,
                                                            source_type: tpl.source_type,
                                                            mappings: tpl.mappings?.map
                                                                ? Object.fromEntries(Object.entries(tpl.mappings.map).map(([k, v]) => [k, (v as string[])[0] || k]))
                                                                : {},
                                                            is_system: false,
                                                            created_at: tpl.created_at,
                                                        })}
                                                        className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition"
                                                    >{t('templateManager.actions.useTemplate')}</button>
                                                    <button
                                                        onClick={() => openEditWizard(tpl)}
                                                        className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded text-sm transition"
                                                    >✏️</button>
                                                    <button
                                                        onClick={() => handleDelete(tpl.id, false)}
                                                        disabled={deletingId === tpl.id}
                                                        className="bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded text-sm transition disabled:opacity-50"
                                                    >{deletingId === tpl.id ? '...' : '🗑️'}</button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Legacy Templates */}
                            {templates.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-semibold text-gray-500 mb-3 uppercase tracking-wide">Legacy Templates</h4>
                                    <div className="grid md:grid-cols-2 gap-4">
                                        {templates.map(template => (
                                            <div key={template.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
                                                <div className="flex items-start justify-between mb-2">
                                                    <h4 className="font-semibold text-gray-900">{template.name}</h4>
                                                    {template.is_system && (
                                                        <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">
                                                            {t('templateManager.badges.system')}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="bg-gray-50 rounded p-2 mb-3 text-xs space-y-1 max-h-32 overflow-y-auto">
                                                    {Object.entries(template.mappings).map(([target, source]) => (
                                                        <div key={target} className="flex items-center gap-2">
                                                            <span className="text-gray-600 font-mono">{target}</span>
                                                            <span className="text-gray-400">←</span>
                                                            <span className="text-gray-900">{source}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleSelect(template)}
                                                        className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition"
                                                    >{t('templateManager.actions.useTemplate')}</button>
                                                    {!template.is_system && (
                                                        <button
                                                            onClick={() => handleDelete(template.id, template.is_system)}
                                                            disabled={deletingId === template.id}
                                                            className="bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded text-sm transition disabled:opacity-50"
                                                        >{deletingId === template.id ? '...' : '🗑️'}</button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <button
                        onClick={onClose}
                        className="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-2 rounded transition"
                    >{t('common.close')}</button>
                </div>
                <ConfirmActionModal
                    open={Boolean(confirmDeleteId)}
                    message={t('templateManager.confirm.deleteTemplate')}
                    loading={Boolean(deletingId)}
                    onCancel={() => setConfirmDeleteId(null)}
                    onConfirm={confirmDelete}
                />
            </div>
        </div>
    )
}
