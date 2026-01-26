import React, { useEffect, useState } from 'react'
import { getErrorMessage, useToast } from '../../shared/toast'
import {
  createNotificationChannel,
  listNotificationChannels,
  updateNotificationChannel,
} from './notificationsService'
import type { NotificationChannelCreate, NotificationChannelType } from './types'

type ChannelState = {
  id: string
  active: boolean
  name: string
  config: Record<string, any>
}

const DEFAULT_EMAIL: ChannelState = {
  id: '',
  active: false,
  name: 'Email',
  config: {
    smtp_host: '',
    smtp_port: '',
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    use_tls: true,
  },
}

const DEFAULT_WHATSAPP: ChannelState = {
  id: '',
  active: false,
  name: 'WhatsApp',
  config: {
    provider: 'twilio',
    account_sid: '',
    auth_token: '',
    from_number: '',
    api_url: '',
    api_key: '',
  },
}

const DEFAULT_TELEGRAM: ChannelState = {
  id: '',
  active: false,
  name: 'Telegram',
  config: {
    bot_token: '',
    parse_mode: 'HTML',
  },
}

export default function NotificacionesSettings() {
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<NotificationChannelType | null>(null)
  const [emailChannel, setEmailChannel] = useState<ChannelState>(DEFAULT_EMAIL)
  const [whatsappChannel, setWhatsappChannel] = useState<ChannelState>(DEFAULT_WHATSAPP)
  const [telegramChannel, setTelegramChannel] = useState<ChannelState>(DEFAULT_TELEGRAM)

  useEffect(() => {
    loadChannels()
  }, [])

  const loadChannels = async () => {
    try {
      setLoading(true)
      const channels = await listNotificationChannels()
      const byType = new Map(channels.map((c) => [c.tipo, c]))

      const email = byType.get('email')
      setEmailChannel((prev) => ({
        ...prev,
        id: email?.id || '',
        active: email?.active ?? prev.active,
        name: email?.name || prev.name,
        config: { ...prev.config, ...(email?.config || {}) },
      }))

      const whatsapp = byType.get('whatsapp')
      setWhatsappChannel((prev) => ({
        ...prev,
        id: whatsapp?.id || '',
        active: whatsapp?.active ?? prev.active,
        name: whatsapp?.name || prev.name,
        config: { ...prev.config, ...(whatsapp?.config || {}) },
      }))

      const telegram = byType.get('telegram')
      setTelegramChannel((prev) => ({
        ...prev,
        id: telegram?.id || '',
        active: telegram?.active ?? prev.active,
        name: telegram?.name || prev.name,
        config: { ...prev.config, ...(telegram?.config || {}) },
      }))
    } catch (err: any) {
      error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const saveChannel = async (tipo: NotificationChannelType, data: ChannelState) => {
    try {
      setSaving(tipo)
      const normalizedConfig = { ...data.config }
      if (tipo === 'email' && normalizedConfig.smtp_port !== '') {
        const portNum = Number(normalizedConfig.smtp_port)
        normalizedConfig.smtp_port = Number.isFinite(portNum)
          ? portNum
          : normalizedConfig.smtp_port
      }

      if (data.id) {
        await updateNotificationChannel(data.id, {
          name: data.name,
          config: normalizedConfig,
          active: data.active,
        })
      } else {
        const payload: NotificationChannelCreate = {
          tipo,
          name: data.name,
          config: normalizedConfig,
          active: data.active,
        }
        await createNotificationChannel(payload)
      }

      await loadChannels()
      success('Canal guardado correctamente')
    } catch (err: any) {
      error(getErrorMessage(err))
    } finally {
      setSaving(null)
    }
  }

  return (
    <div className="p-4" style={{ maxWidth: 920 }}>
      <h2 className="font-semibold text-lg mb-2">Notificaciones</h2>
      <p className="text-sm text-slate-600 mb-6">
        Configura canales para alertas y avisos. Los datos se guardan por tenant.
      </p>

      {loading && <div className="text-sm text-slate-500 mb-4">Loading configuration...</div>}

      <section className="border rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Email (SMTP)</h3>
          <label className="text-sm flex items-center gap-2">
            <input
              type="checkbox"
              checked={emailChannel.active}
              onChange={(e) => setEmailChannel({ ...emailChannel, active: e.target.checked })}
            />
            Active
          </label>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">SMTP Host</label>
            <input
              className="border px-2 py-1 w-full rounded"
              value={emailChannel.config.smtp_host || ''}
              onChange={(e) =>
                setEmailChannel({
                  ...emailChannel,
                  config: { ...emailChannel.config, smtp_host: e.target.value },
                })
              }
            />
          </div>
          <div>
            <label className="block text-sm mb-1">SMTP Port</label>
            <input
              className="border px-2 py-1 w-full rounded"
              type="number"
              value={emailChannel.config.smtp_port || ''}
              onChange={(e) =>
                setEmailChannel({
                  ...emailChannel,
                  config: { ...emailChannel.config, smtp_port: e.target.value },
                })
              }
            />
          </div>
          <div>
            <label className="block text-sm mb-1">SMTP User</label>
            <input
              className="border px-2 py-1 w-full rounded"
              value={emailChannel.config.smtp_user || ''}
              onChange={(e) =>
                setEmailChannel({
                  ...emailChannel,
                  config: { ...emailChannel.config, smtp_user: e.target.value },
                })
              }
            />
          </div>
          <div>
            <label className="block text-sm mb-1">SMTP Password</label>
            <input
              className="border px-2 py-1 w-full rounded"
              type="password"
              value={emailChannel.config.smtp_password || ''}
              onChange={(e) =>
                setEmailChannel({
                  ...emailChannel,
                  config: { ...emailChannel.config, smtp_password: e.target.value },
                })
              }
            />
          </div>
          <div>
            <label className="block text-sm mb-1">From Email</label>
            <input
              className="border px-2 py-1 w-full rounded"
              value={emailChannel.config.from_email || ''}
              onChange={(e) =>
                setEmailChannel({
                  ...emailChannel,
                  config: { ...emailChannel.config, from_email: e.target.value },
                })
              }
            />
          </div>
          <div className="flex items-center">
            <label className="text-sm flex items-center gap-2 mt-6">
              <input
                type="checkbox"
                checked={!!emailChannel.config.use_tls}
                onChange={(e) =>
                  setEmailChannel({
                    ...emailChannel,
                    config: { ...emailChannel.config, use_tls: e.target.checked },
                  })
                }
              />
              Usar TLS
            </label>
          </div>
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded mt-4 disabled:opacity-60"
          onClick={() => saveChannel('email', emailChannel)}
          disabled={saving === 'email'}
        >
          Save Email
        </button>
      </section>

      <section className="border rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">WhatsApp</h3>
          <label className="text-sm flex items-center gap-2">
            <input
              type="checkbox"
              checked={whatsappChannel.active}
              onChange={(e) => setWhatsappChannel({ ...whatsappChannel, active: e.target.checked })}
            />
            Active
          </label>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">Proveedor</label>
            <select
              className="border px-2 py-1 w-full rounded"
              value={whatsappChannel.config.provider || 'twilio'}
              onChange={(e) =>
                setWhatsappChannel({
                  ...whatsappChannel,
                  config: { ...whatsappChannel.config, provider: e.target.value },
                })
              }
            >
              <option value="twilio">Twilio</option>
              <option value="generic">API Generica</option>
            </select>
          </div>
          {whatsappChannel.config.provider === 'twilio' && (
            <>
              <div>
                <label className="block text-sm mb-1">Account SID</label>
                <input
                  className="border px-2 py-1 w-full rounded"
                  value={whatsappChannel.config.account_sid || ''}
                  onChange={(e) =>
                    setWhatsappChannel({
                      ...whatsappChannel,
                      config: { ...whatsappChannel.config, account_sid: e.target.value },
                    })
                  }
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Auth Token</label>
                <input
                  className="border px-2 py-1 w-full rounded"
                  type="password"
                  value={whatsappChannel.config.auth_token || ''}
                  onChange={(e) =>
                    setWhatsappChannel({
                      ...whatsappChannel,
                      config: { ...whatsappChannel.config, auth_token: e.target.value },
                    })
                  }
                />
              </div>
              <div>
                <label className="block text-sm mb-1">From Number</label>
                <input
                  className="border px-2 py-1 w-full rounded"
                  value={whatsappChannel.config.from_number || ''}
                  onChange={(e) =>
                    setWhatsappChannel({
                      ...whatsappChannel,
                      config: { ...whatsappChannel.config, from_number: e.target.value },
                    })
                  }
                />
              </div>
            </>
          )}
          {whatsappChannel.config.provider === 'generic' && (
            <>
              <div>
                <label className="block text-sm mb-1">API URL</label>
                <input
                  className="border px-2 py-1 w-full rounded"
                  value={whatsappChannel.config.api_url || ''}
                  onChange={(e) =>
                    setWhatsappChannel({
                      ...whatsappChannel,
                      config: { ...whatsappChannel.config, api_url: e.target.value },
                    })
                  }
                />
              </div>
              <div>
                <label className="block text-sm mb-1">API Key</label>
                <input
                  className="border px-2 py-1 w-full rounded"
                  type="password"
                  value={whatsappChannel.config.api_key || ''}
                  onChange={(e) =>
                    setWhatsappChannel({
                      ...whatsappChannel,
                      config: { ...whatsappChannel.config, api_key: e.target.value },
                    })
                  }
                />
              </div>
            </>
          )}
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded mt-4 disabled:opacity-60"
          onClick={() => saveChannel('whatsapp', whatsappChannel)}
          disabled={saving === 'whatsapp'}
        >
          Save WhatsApp
        </button>
      </section>

      <section className="border rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Telegram</h3>
          <label className="text-sm flex items-center gap-2">
            <input
              type="checkbox"
              checked={telegramChannel.active}
              onChange={(e) => setTelegramChannel({ ...telegramChannel, active: e.target.checked })}
            />
            Active
          </label>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">Bot Token</label>
            <input
              className="border px-2 py-1 w-full rounded"
              type="password"
              value={telegramChannel.config.bot_token || ''}
              onChange={(e) =>
                setTelegramChannel({
                  ...telegramChannel,
                  config: { ...telegramChannel.config, bot_token: e.target.value },
                })
              }
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Parse Mode</label>
            <select
              className="border px-2 py-1 w-full rounded"
              value={telegramChannel.config.parse_mode || 'HTML'}
              onChange={(e) =>
                setTelegramChannel({
                  ...telegramChannel,
                  config: { ...telegramChannel.config, parse_mode: e.target.value },
                })
              }
            >
              <option value="HTML">HTML</option>
              <option value="Markdown">Markdown</option>
            </select>
          </div>
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded mt-4 disabled:opacity-60"
          onClick={() => saveChannel('telegram', telegramChannel)}
          disabled={saving === 'telegram'}
        >
          Save Telegram
        </button>
      </section>
    </div>
  )
}
