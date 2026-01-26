/**
 * Webhooks List Component
 * Displays list of webhooks with actions
 */

import React, { useState, useEffect } from 'react';
import { getWebhooks, testWebhook, deleteWebhook, Webhook } from '../../services/webhooks';
import './styles.css';

interface WebhooksListProps {
  onEdit?: (webhook: Webhook) => void;
  onRefresh?: () => void;
}

export const WebhooksList: React.FC<WebhooksListProps> = ({ onEdit, onRefresh }) => {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchWebhooks = async () => {
    try {
      setLoading(true);
      const response = await getWebhooks({ limit: 50 });
      setWebhooks(response.webhooks);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Error loading webhooks'));
      console.error('Webhooks error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWebhooks();
  }, []);

  const handleTest = async (webhook: Webhook) => {
    try {
      setTestingId(webhook.id);
      const result = await testWebhook(webhook.id);
      alert(`Test result: ${result.success ? 'Success' : 'Failed'} (Status: ${result.status})`);
    } catch (err) {
      alert(`Test failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async (webhookId: string) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este webhook?')) return;

    try {
      setDeletingId(webhookId);
      await deleteWebhook(webhookId);
      setWebhooks((prev) => prev.filter((w) => w.id !== webhookId));
      onRefresh?.();
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="webhooks-list">
      {error && (
        <div className="webhooks-list__error">
          {error.message}
          <button onClick={fetchWebhooks}>Reintentar</button>
        </div>
      )}

      {loading ? (
        <div className="webhooks-list__loading">Cargando webhooks...</div>
      ) : webhooks.length === 0 ? (
        <div className="webhooks-list__empty">No hay webhooks configurados</div>
      ) : (
        <div className="webhooks-list__table">
          <div className="webhooks-list__table-head">
            <div className="webhooks-list__table-cell">URL</div>
            <div className="webhooks-list__table-cell">Eventos</div>
            <div className="webhooks-list__table-cell">Estado</div>
            <div className="webhooks-list__table-cell">Acciones</div>
          </div>
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="webhooks-list__table-row">
              <div className="webhooks-list__table-cell" title={webhook.url}>
                <code className="webhooks-list__url">{webhook.url}</code>
              </div>
              <div className="webhooks-list__table-cell">
                <div className="webhooks-list__events">
                  {webhook.events.slice(0, 2).map((event) => (
                    <span key={event} className="webhooks-list__event">
                      {event}
                    </span>
                  ))}
                  {webhook.events.length > 2 && (
                    <span className="webhooks-list__event-more">+{webhook.events.length - 2}</span>
                  )}
                </div>
              </div>
              <div className="webhooks-list__table-cell">
                <span className={`webhooks-list__status ${webhook.active ? 'is-active' : 'is-inactive'}`}>
                  {webhook.active ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              <div className="webhooks-list__table-cell">
                <div className="webhooks-list__actions">
                  <button
                    className="webhooks-list__action-btn webhooks-list__action-btn--test"
                    onClick={() => handleTest(webhook)}
                    disabled={testingId === webhook.id}
                    title="Probar webhook"
                  >
                    {testingId === webhook.id ? 'Probando...' : 'Probar'}
                  </button>
                  <button
                    className="webhooks-list__action-btn webhooks-list__action-btn--edit"
                    onClick={() => onEdit?.(webhook)}
                    title="Editar webhook"
                  >
                    Editar
                  </button>
                  <button
                    className="webhooks-list__action-btn webhooks-list__action-btn--delete"
                    onClick={() => handleDelete(webhook.id)}
                    disabled={deletingId === webhook.id}
                    title="Eliminar webhook"
                  >
                    {deletingId === webhook.id ? 'Eliminando...' : 'Eliminar'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
