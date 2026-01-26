/**
 * Webhook Logs Component
 * Displays execution logs for a specific webhook
 */

import React, { useState, useEffect } from 'react';
import { getWebhookLogs, WebhookLog } from '../../services/webhooks';
import './styles.css';

interface WebhookLogsProps {
  webhookId: string;
}

export const WebhookLogs: React.FC<WebhookLogsProps> = ({ webhookId }) => {
  const [logs, setLogs] = useState<WebhookLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const response = await getWebhookLogs(webhookId, { limit: 20 });
        setLogs(response.logs);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Error loading logs'));
        console.error('Logs error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [webhookId]);

  return (
    <div className="webhook-logs">
      <h3 className="webhook-logs__title">Logs de Ejecución</h3>

      {error && (
        <div className="webhook-logs__error">{error.message}</div>
      )}

      {loading ? (
        <div className="webhook-logs__loading">Cargando logs...</div>
      ) : logs.length === 0 ? (
        <div className="webhook-logs__empty">No hay logs disponibles</div>
      ) : (
        <div className="webhook-logs__list">
          {logs.map((log) => (
            <div
              key={log.id}
              className={`webhook-log-item ${log.success ? 'is-success' : 'is-failed'}`}
              onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
            >
              <div className="webhook-log-item__header">
                <div className="webhook-log-item__status">
                  {log.success ? '✓' : '✗'}
                </div>
                <div className="webhook-log-item__info">
                  <span className="webhook-log-item__event">{log.event}</span>
                  <span className="webhook-log-item__code">{log.response_status}</span>
                </div>
                <span className="webhook-log-item__time">
                  {new Date(log.created_at).toLocaleString('es-ES')}
                </span>
              </div>
              {expandedId === log.id && (
                <div className="webhook-log-item__details">
                  <div className="webhook-log-item__section">
                    <h4 className="webhook-log-item__section-title">Payload</h4>
                    <pre className="webhook-log-item__code-block">
                      {JSON.stringify(log.payload, null, 2)}
                    </pre>
                  </div>
                  {log.response_body && (
                    <div className="webhook-log-item__section">
                      <h4 className="webhook-log-item__section-title">Respuesta</h4>
                      <pre className="webhook-log-item__code-block">
                        {log.response_body}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
