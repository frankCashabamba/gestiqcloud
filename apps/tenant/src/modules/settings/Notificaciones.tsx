import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getErrorMessage, useToast } from '../../shared/toast'
import {
  createNotificationChannel,
  generateTelegramSecret,
  listNotificationChannels,
  registerTelegramWebhook,
  updateNotificationChannel,
} from './notificationsService'
import type { NotificationChannelCreate, NotificationChannelType } from './types'

type ChannelState = {
  id: string
  tenant_id?: string
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
  tenant_id: '',
  active: false,
  name: 'Telegram',
  config: {
    bot_token: '',
    parse_mode: 'HTML',
    default_recipient: '',
    allowed_chat_ids: '',
    low_stock_threshold: 5,
    webhook_secret: '',
  },
}


export default function NotificacionesSettings() {
  const { t } = useTranslation(['settings', 'common'])
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<NotificationChannelType | null>(null)
  const [emailChannel, setEmailChannel] = useState<ChannelState>(DEFAULT_EMAIL)
  const [whatsappChannel, setWhatsappChannel] = useState<ChannelState>(DEFAULT_WHATSAPP)
  const [telegramChannel, setTelegramChannel] = useState<ChannelState>(DEFAULT_TELEGRAM)
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [activating, setActivating] = useState(false)
  const [botStatus, setBotStatus] = useState<'idle' | 'ok' | 'error'>('idle')
  const [botStatusMsg, setBotStatusMsg] = useState('')
  const [tunnelUrl, setTunnelUrl] = useState('')
  const [showTunnel, setShowTunnel] = useState(() => window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')

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
        tenant_id: telegram?.tenant_id || '',
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
      success(t('settings:notifications.channelSaved'))
    } catch (err: any) {
      error(getErrorMessage(err))
    } finally {
      setSaving(null)
    }
  }

  const generateSecret = async () => {
    try {
      const secret = await generateTelegramSecret()
      setTelegramChannel((prev) => ({
        ...prev,
        config: { ...prev.config, webhook_secret: secret },
      }))
    } catch (err: any) {
      error(getErrorMessage(err))
    }
  }

  const activateBot = async () => {
    try {
      setActivating(true)
      setBotStatus('idle')
      const webhookUrl = await registerTelegramWebhook(tunnelUrl.trim() || undefined)
      setBotStatus('ok')
      setBotStatusMsg(webhookUrl)
      success(t('settings:notifications.botActivated'))
    } catch (err: any) {
      setBotStatus('error')
      setBotStatusMsg(getErrorMessage(err))
      error(getErrorMessage(err))
    } finally {
      setActivating(false)
    }
  }

  return (
    <div className="p-4" style={{ maxWidth: 920 }}>
      <h2 className="font-semibold text-lg mb-2">{t('settings:notifications.title')}</h2>
      <p className="text-sm text-slate-600 mb-6">
        {t('settings:notifications.subtitle')}
      </p>

      {loading && <div className="text-sm text-slate-500 mb-4">{t('settings:notifications.loading')}</div>}

      <section className="border rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Email (SMTP)</h3>
          <label className="text-sm flex items-center gap-2">
            <input
              type="checkbox"
              checked={emailChannel.active}
              onChange={(e) => setEmailChannel({ ...emailChannel, active: e.target.checked })}
            />
            {t('settings:notifications.active')}
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
              {t('settings:notifications.useTls')}
            </label>
          </div>
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded mt-4 disabled:opacity-60"
          onClick={() => saveChannel('email', emailChannel)}
          disabled={saving === 'email'}
        >
          {saving === 'email' ? t('common:saving') : t('settings:notifications.saveEmail')}
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
            {t('settings:notifications.active')}
          </label>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm mb-1">{t('settings:notifications.provider')}</label>
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
          {saving === 'whatsapp' ? t('common:saving') : t('settings:notifications.saveWhatsapp')}
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
            {t('settings:notifications.active')}
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
            <label className="block text-sm mb-1">Chat ID</label>
            <input
              className="border px-2 py-1 w-full rounded"
              type="text"
              placeholder="-100123456789"
              value={telegramChannel.config.default_recipient || ''}
              onChange={(e) =>
                setTelegramChannel({
                  ...telegramChannel,
                  config: { ...telegramChannel.config, default_recipient: e.target.value },
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

        <div className="mt-4 pt-4 border-t">
          <p className="text-sm font-medium text-slate-700 mb-3">Bot de comandos</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">
                Chat IDs autorizados
                <span className="text-slate-400 font-normal ml-1">(separados por coma)</span>
              </label>
              <input
                className="border px-2 py-1 w-full rounded font-mono text-sm"
                placeholder="123456789, 987654321"
                value={telegramChannel.config.allowed_chat_ids || ''}
                onChange={(e) =>
                  setTelegramChannel({
                    ...telegramChannel,
                    config: { ...telegramChannel.config, allowed_chat_ids: e.target.value },
                  })
                }
              />
              <p className="text-xs text-slate-400 mt-1">
                Escribe <code>/start</code> a <strong>@userinfobot</strong> para obtener tu ID
              </p>
            </div>
            <div>
              <label className="block text-sm mb-1">
                Umbral stock bajo
                <span className="text-slate-400 font-normal ml-1">(unidades)</span>
              </label>
              <input
                className="border px-2 py-1 w-full rounded"
                type="number"
                min={0}
                step={1}
                placeholder="5"
                value={telegramChannel.config.low_stock_threshold ?? 5}
                onChange={(e) =>
                  setTelegramChannel({
                    ...telegramChannel,
                    config: {
                      ...telegramChannel.config,
                      low_stock_threshold: Number(e.target.value),
                    },
                  })
                }
              />
              <p className="text-xs text-slate-400 mt-1">
                Productos con stock ≤ este valor aparecen en <code>/stock_bajo</code>
              </p>
            </div>
            <div>
              <label className="block text-sm mb-1">Webhook secret</label>
              <div className="flex gap-2">
                <input
                  className="border px-2 py-1 flex-1 rounded font-mono text-sm"
                  type="password"
                  placeholder="Haz clic en Generar"
                  value={telegramChannel.config.webhook_secret || ''}
                  onChange={(e) =>
                    setTelegramChannel({
                      ...telegramChannel,
                      config: { ...telegramChannel.config, webhook_secret: e.target.value },
                    })
                  }
                />
                <button
                  type="button"
                  className="shrink-0 border px-3 py-1 rounded text-sm hover:bg-slate-50"
                  onClick={generateSecret}
                >
                  Generar
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Activar bot */}
        <div className="mt-4 pt-4 border-t">
          <p className="text-sm font-medium text-slate-700 mb-1">Activar bot de comandos</p>
          <p className="text-xs text-slate-500 mb-3">
            Guarda la configuración y pulsa este botón. En producción funciona directamente.
          </p>

          <button
            type="button"
            className="text-xs text-slate-400 hover:text-slate-600 underline mb-3 block"
            onClick={() => setShowTunnel((v) => !v)}
          >
            {showTunnel ? '▲ Ocultar' : '▼ URL personalizada (opcional)'}
          </button>

          {showTunnel && (
            <div className="mb-3">
              <input
                className="border px-2 py-1 w-full rounded font-mono text-sm"
                placeholder="https://api.tudominio.com"
                value={tunnelUrl}
                onChange={(e) => setTunnelUrl(e.target.value)}
              />
              <p className="text-xs text-slate-400 mt-1">
                {window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
                  ? '⚠ En local Telegram necesita una URL pública HTTPS. Usa ngrok u otro tunnel: ngrok http 8000 → pega la URL aquí.'
                  : 'Déjalo vacío para usar la URL del servidor automáticamente.'}
              </p>
            </div>
          )}

          <div className="flex items-center gap-3 flex-wrap">
            <button
              type="button"
              className="bg-green-600 text-white px-4 py-2 rounded disabled:opacity-60 text-sm font-medium"
              onClick={activateBot}
              disabled={activating || !telegramChannel.id}
              title={!telegramChannel.id ? 'Guarda primero la configuración' : undefined}
            >
              {activating ? 'Activando...' : '⚡ Activar bot'}
            </button>

            {botStatus === 'ok' && (
              <span className="text-xs text-green-700 font-medium">✓ Bot activo</span>
            )}
            {botStatus === 'error' && (
              <span className="text-xs text-red-600">{botStatusMsg}</span>
            )}
          </div>

          {botStatus === 'ok' && botStatusMsg && (
            <div className="mt-3 flex items-center gap-2">
              <code className="flex-1 bg-slate-50 border rounded px-3 py-2 text-xs font-mono break-all text-slate-600">
                {botStatusMsg}
              </code>
              <button
                type="button"
                className="shrink-0 border px-3 py-2 rounded text-sm hover:bg-slate-50"
                onClick={() => {
                  navigator.clipboard.writeText(botStatusMsg)
                  setCopiedUrl(true)
                  setTimeout(() => setCopiedUrl(false), 2000)
                }}
              >
                {copiedUrl ? '✓' : 'Copiar'}
              </button>
            </div>
          )}
        </div>

        <button
          className="bg-blue-600 text-white px-3 py-2 rounded mt-4 disabled:opacity-60"
          onClick={() => saveChannel('telegram', telegramChannel)}
          disabled={saving === 'telegram'}
        >
          {saving === 'telegram' ? t('common:saving') : t('settings:notifications.saveTelegram')}
        </button>
      </section>
    </div>
  )
}
