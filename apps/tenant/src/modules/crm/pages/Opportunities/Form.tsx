import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createOpportunity, getOpportunity, updateOpportunity, type Opportunity } from '../../services'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { OpportunityStage } from '../../types'

export default function OpportunityForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { t } = useTranslation('crm')
  const [form, setForm] = useState<Partial<Omit<Opportunity, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>>>({
    name: '',
    description: '',
    value: 0,
    currency: 'USD',
    stage: OpportunityStage.PROSPECTING,
    probability: 0,
    expected_close_date: '',
    assigned_to: '',
  })
  const { success, error } = useToast()

  useEffect(() => {
    if (!id) return
    getOpportunity(id).then((x)=> setForm({ ...x }))
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.name || String(form.name).trim() === '') throw new Error(t('opportunities.titleRequired'))
      if (form.value === undefined || form.value === null) throw new Error(t('opportunities.valueRequired'))
      if (id) await updateOpportunity(id, form)
      else await createOpportunity(form as any)
      success(t('opportunities.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? t('opportunities.edit') : t('opportunities.new')}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">{t('opportunities.name')} *</label>
          <input
            type="text"
            value={form.name ?? ''}
            onChange={(e)=> setForm({ ...form, name: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
          />
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.description')}</label>
          <textarea
            value={form.description ?? ''}
            onChange={(e)=> setForm({ ...form, description: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={3}
          />
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.value')} *</label>
          <input
            type="number"
            value={form.value ?? 0}
            onChange={(e)=> setForm({ ...form, value: Number(e.target.value) })}
            className="border px-2 py-1 w-full rounded"
            required
            min="0"
            step="0.01"
          />
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.currency')}</label>
          <input
            type="text"
            value={form.currency ?? 'USD'}
            onChange={(e)=> setForm({ ...form, currency: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.probability')}</label>
          <input
            type="number"
            value={form.probability ?? 0}
            onChange={(e)=> setForm({ ...form, probability: Number(e.target.value) })}
            className="border px-2 py-1 w-full rounded"
            min="0"
            max="100"
          />
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.stage')}</label>
          <select
            value={form.stage ?? OpportunityStage.PROSPECTING}
            onChange={(e)=> setForm({ ...form, stage: e.target.value as OpportunityStage })}
            className="border px-2 py-1 w-full rounded"
          >
            <option value={OpportunityStage.PROSPECTING}>{t('opportunities.stageProspecting')}</option>
            <option value={OpportunityStage.QUALIFICATION}>{t('opportunities.stageQualification')}</option>
            <option value={OpportunityStage.PROPOSAL}>{t('opportunities.stageProposal')}</option>
            <option value={OpportunityStage.NEGOTIATION}>{t('opportunities.stageNegotiation')}</option>
            <option value={OpportunityStage.CLOSED_WON}>{t('opportunities.stageClosedWon')}</option>
            <option value={OpportunityStage.CLOSED_LOST}>{t('opportunities.stageClosedLost')}</option>
          </select>
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.expectedCloseDate')}</label>
          <input
            type="date"
            value={form.expected_close_date ?? ''}
            onChange={(e)=> setForm({ ...form, expected_close_date: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div>
          <label className="block mb-1">{t('opportunities.assignedTo')}</label>
          <input
            type="text"
            value={form.assigned_to ?? ''}
            onChange={(e)=> setForm({ ...form, assigned_to: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">{t('opportunities.save')}</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>{t('opportunities.cancel')}</button>
        </div>
      </form>
    </div>
  )
}
