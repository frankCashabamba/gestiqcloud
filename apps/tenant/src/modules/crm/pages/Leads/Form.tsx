import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createLead, getLead, updateLead, convertLead, type Lead } from '../../services'
import { useCrmLabels } from '../../useCrmLabels'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { LeadStatus, LeadSource } from '../../types'
import { BackButton } from '@ui'

export default function LeadForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useCrmLabels()
  const [form, setForm] = useState<Partial<Omit<Lead, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>>>({
    name: '',
    email: '',
    phone: '',
    company: '',
    position: '',
    source: LeadSource.WEBSITE,
    status: LeadStatus.NEW,
    score: 0,
    notes: '',
    assigned_to: '',
  })
  const { success, error } = useToast()
  const [converting, setConverting] = useState(false)

  useEffect(() => {
    if (!id) return
    getLead(id).then((x)=> setForm({ ...x }))
  }, [id])

  const canConvert = !!id && (form.status === LeadStatus.NEW || form.status === LeadStatus.QUALIFIED)

  const handleConvert = async () => {
    if (!id) return
    setConverting(true)
    try {
      await convertLead(id, { create_opportunity: true })
      success(t('leads.converted'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setConverting(false)
    }
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.name || String(form.name).trim() === '') throw new Error(t('leads.nameRequired'))
      if (!form.email || String(form.email).trim() === '') throw new Error(t('leads.emailRequired'))
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form.email))) throw new Error(t('leads.emailInvalid'))
      if (id) await updateLead(id, form)
      else await createLead(form as any)
      success(t('leads.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="gc-container py-6">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <h3 className="text-xl font-semibold mb-3">{id ? t('leads.editLead') : t('leads.newLead')}</h3>
      <form onSubmit={onSubmit} className="space-y-4 max-w-xl">
        <div>
          <label className="gc-label">{t('leads.name')} *</label>
          <input
            type="text"
            value={form.name ?? ''}
            onChange={(e)=> setForm({ ...form, name: e.target.value })}
            className="gc-input"
            required
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.email')} *</label>
          <input
            type="email"
            value={form.email ?? ''}
            onChange={(e)=> setForm({ ...form, email: e.target.value })}
            className="gc-input"
            required
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.phone')}</label>
          <input
            type="text"
            value={form.phone ?? ''}
            onChange={(e)=> setForm({ ...form, phone: e.target.value })}
            className="gc-input"
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.company')}</label>
          <input
            type="text"
            value={form.company ?? ''}
            onChange={(e)=> setForm({ ...form, company: e.target.value })}
            className="gc-input"
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.position')}</label>
          <input
            type="text"
            value={form.position ?? ''}
            onChange={(e)=> setForm({ ...form, position: e.target.value })}
            className="gc-input"
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.status')}</label>
          <select
            value={form.status ?? LeadStatus.NEW}
            onChange={(e)=> setForm({ ...form, status: e.target.value as LeadStatus })}
            className="gc-input"
          >
            <option value={LeadStatus.NEW}>{t('leads.statusNew')}</option>
            <option value={LeadStatus.CONTACTED}>{t('leads.statusContacted')}</option>
            <option value={LeadStatus.QUALIFIED}>{t('leads.statusQualified')}</option>
            <option value={LeadStatus.LOST}>{t('leads.statusLost')}</option>
            <option value={LeadStatus.CONVERTED}>{t('leads.statusConverted')}</option>
          </select>
        </div>
        <div>
          <label className="gc-label">{t('leads.source')}</label>
          <select
            value={form.source ?? LeadSource.WEBSITE}
            onChange={(e)=> setForm({ ...form, source: e.target.value as LeadSource })}
            className="gc-input"
          >
            <option value={LeadSource.WEBSITE}>{t('leads.sourceWebsite')}</option>
            <option value={LeadSource.REFERRAL}>{t('leads.sourceReferral')}</option>
            <option value={LeadSource.SOCIAL_MEDIA}>{t('leads.sourceSocialMedia')}</option>
            <option value={LeadSource.EMAIL}>{t('leads.sourceEmail')}</option>
            <option value={LeadSource.PHONE}>{t('leads.phoneSource')}</option>
            <option value={LeadSource.EVENT}>{t('leads.sourceEvent')}</option>
            <option value={LeadSource.OTHER}>{t('leads.sourceOther')}</option>
          </select>
        </div>
        <div>
          <label className="gc-label">{t('leads.assignedTo')}</label>
          <input
            type="text"
            value={form.assigned_to ?? ''}
            onChange={(e)=> setForm({ ...form, assigned_to: e.target.value })}
            className="gc-input"
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.score')}</label>
          <input
            type="number"
            value={form.score ?? 0}
            onChange={(e)=> setForm({ ...form, score: Number(e.target.value) })}
            className="gc-input"
            min="0"
            max="100"
          />
        </div>
        <div>
          <label className="gc-label">{t('leads.notes')}</label>
          <textarea
            value={form.notes ?? ''}
            onChange={(e)=> setForm({ ...form, notes: e.target.value })}
            className="gc-input"
            rows={4}
          />
        </div>
        <div className="pt-2 flex flex-wrap items-center gap-2">
          <button type="submit" className="gc-btn gc-btn--primary">{t('leads.save')}</button>
          {canConvert && (
            <button
              type="button"
              className="gc-btn gc-btn--secondary"
              onClick={handleConvert}
              disabled={converting}
            >
              {converting ? '...' : t('leads.convert')}
            </button>
          )}
          <button type="button" className="gc-btn gc-btn--ghost" onClick={()=> nav('..')}>{t('leads.cancel')}</button>
        </div>
      </form>
    </div>
  )
}
