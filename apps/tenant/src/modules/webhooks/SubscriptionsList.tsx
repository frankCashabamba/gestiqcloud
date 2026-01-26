import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useToast } from '../../shared/toast'
import { listSubscriptions, deleteSubscription, testSubscription, WebhookSubscription } from './services'

export default function SubscriptionsList() {
  const { t } = useTranslation()
  const { success, error: showError } = useToast()
  const [loading, setLoading] = useState(true)
  const [subscriptions, setSubscriptions] = useState<WebhookSubscription[]>([])
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    loadSubscriptions()
  }, [])

  const loadSubscriptions = async () => {
    setLoading(true)
    try {
      const data = await listSubscriptions()
      setSubscriptions(data)
    } catch {
      showError(t('webhooks.errors.loading'))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm(t('webhooks.deleteConfirm'))) return
    try {
      await deleteSubscription(id)
      success(t('webhooks.deleted'))
      loadSubscriptions()
    } catch {
      showError(t('webhooks.errors.deleting'))
    }
  }

  const handleTest = async (id: string) => {
    try {
      const result = await testSubscription(id)
      success(t('webhooks.testSent', { count: result.enqueued }))
    } catch {
      showError(t('webhooks.errors.sendingTest'))
    }
  }

  if (loading) return <div className="p-6">{t('common.loading')}</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{t('webhooks.title')}</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {showForm ? t('common.cancel') : t('webhooks.newWebhook')}
        </button>
      </div>

      {showForm && (
        <SubscriptionForm
          t={t}
          onSuccess={() => {
            setShowForm(false)
            loadSubscriptions()
          }}
        />
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('webhooks.event')}</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('webhooks.url')}</th>
              <th className="px-6 py-3 text-left text-sm font-semibold">{t('common.status')}</th>
              <th className="px-6 py-3 text-right text-sm font-semibold">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {subscriptions.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                  {t('webhooks.noWebhooks')}
                </td>
              </tr>
            ) : (
              subscriptions.map(sub => (
                <tr key={sub.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium">{sub.event}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 truncate">{sub.url}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      sub.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {sub.active ? t('common.active') : t('common.inactive')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button
                      onClick={() => handleTest(sub.id)}
                      className="text-sm px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
                    >
                      {t('webhooks.test')}
                    </button>
                    <button
                      onClick={() => handleDelete(sub.id)}
                      className="text-sm px-3 py-1 text-red-600 hover:bg-red-50 rounded"
                    >
                      {t('common.delete')}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SubscriptionForm({ onSuccess, t }: { onSuccess: () => void; t: (key: string, vars?: Record<string, any>) => string }) {
  const { success, error: showError } = useToast()
  const [event, setEvent] = useState('')
  const [url, setUrl] = useState('')
  const [secret, setSecret] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!event || !url) {
      showError(t('webhooks.errors.eventUrlRequired'))
      return
    }

    setLoading(true)
    try {
      const { createSubscription } = await import('./services')
      await createSubscription({ event, url, secret: secret || undefined })
      success(t('webhooks.created'))
      onSuccess()
    } catch {
      showError(t('webhooks.errors.creating'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium">{t('webhooks.event')}</label>
        <input
          type="text"
          value={event}
          onChange={e => setEvent(e.target.value)}
          placeholder="ej: order.created"
          className="mt-1 w-full border rounded px-3 py-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">{t('webhooks.url')}</label>
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://..."
          className="mt-1 w-full border rounded px-3 py-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">{t('webhooks.secret')}</label>
        <input
          type="password"
          value={secret}
          onChange={e => setSecret(e.target.value)}
          placeholder="HMAC-SHA256 secret"
          className="mt-1 w-full border rounded px-3 py-2"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? t('webhooks.creating') : t('common.create')}
      </button>
    </form>
  )
}
