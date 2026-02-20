/**
 * Webhook Form Modal
 * For creating and editing webhooks with event selection
 */

import React, { useState, useEffect } from 'react';
import { createWebhook, updateWebhook, Webhook } from '../../services/webhooks';
import './webhook-form.css';

interface WebhookFormProps {
  webhook?: Webhook;
  onClose: () => void;
  onSuccess?: () => void;
}

const AVAILABLE_EVENTS = [
  // Invoice events
  { group: 'Invoices', events: [
    'invoice.created',
    'invoice.sent',
    'invoice.authorized',
    'invoice.rejected',
    'invoice.cancelled',
  ]},
  // Payment events
  { group: 'Payments', events: [
    'payment.received',
    'payment.failed',
  ]},
  // Customer events
  { group: 'Customers', events: [
    'customer.created',
    'customer.updated',
  ]},
  // Sales Order events
  { group: 'Sales Orders', events: [
    'sales_order.created',
    'sales_order.confirmed',
    'sales_order.cancelled',
  ]},
  // Inventory events
  { group: 'Inventory', events: [
    'inventory.updated',
    'inventory.low',
  ]},
];

export const WebhookForm: React.FC<WebhookFormProps> = ({
  webhook,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    url: webhook?.url || '',
    events: webhook?.events || [],
    secret: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.url.trim()) {
      errors.url = 'URL is required';
    } else if (!formData.url.startsWith('https://')) {
      errors.url = 'URL must start with https://';
    } else if (formData.url.length > 2048) {
      errors.url = 'URL is too long (max 2048 characters)';
    }

    if (formData.events.length === 0) {
      errors.events = 'Select at least one event';
    }

    if (formData.secret) {
      if (formData.secret.length < 8) {
        errors.secret = 'Secret must be at least 8 characters';
      } else if (formData.secret.length > 500) {
        errors.secret = 'Secret is too long (max 500 characters)';
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleEventToggle = (event: string) => {
    setFormData((prev) => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event],
    }));
  };

  const handleSelectAllGroup = (events: string[]) => {
    setFormData((prev) => {
      const allSelected = events.every((e) => prev.events.includes(e));
      const newEvents = allSelected
        ? prev.events.filter((e) => !events.includes(e))
        : [...new Set([...prev.events, ...events])];
      return { ...prev, events: newEvents };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);
      const payload = {
        url: formData.url.trim(),
        events: formData.events,
        ...(formData.secret && { secret: formData.secret }),
      };

      if (webhook) {
        await updateWebhook(webhook.id, payload);
      } else {
        await createWebhook(payload);
      }

      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error saving webhook');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="webhook-form-modal">
      <div className="webhook-form-modal__overlay" onClick={onClose} />
      <form className="webhook-form-modal__form" onSubmit={handleSubmit}>
        <div className="webhook-form-modal__header">
          <h2>{webhook ? 'Edit Webhook' : 'Create Webhook'}</h2>
          <button
            type="button"
            className="webhook-form-modal__close"
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        <div className="webhook-form-modal__body">
          {error && (
            <div className="webhook-form-modal__alert webhook-form-modal__alert--error">
              {error}
            </div>
          )}

          {/* URL Field */}
          <div className="webhook-form-modal__field">
            <label htmlFor="url">
              Webhook URL <span className="webhook-form-modal__required">*</span>
            </label>
            <input
              id="url"
              type="url"
              placeholder="https://your-app.com/webhooks"
              value={formData.url}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, url: e.target.value }));
                if (validationErrors.url) {
                  setValidationErrors((prev) => ({ ...prev, url: '' }));
                }
              }}
              className={validationErrors.url ? 'is-invalid' : ''}
              disabled={loading}
            />
            {validationErrors.url && (
              <div className="webhook-form-modal__field-error">
                {validationErrors.url}
              </div>
            )}
            <small>Must use HTTPS protocol</small>
          </div>

          {/* Secret Field */}
          <div className="webhook-form-modal__field">
            <label htmlFor="secret">Secret (Optional)</label>
            <input
              id="secret"
              type="password"
              placeholder="Enter webhook secret"
              value={formData.secret}
              onChange={(e) => {
                setFormData((prev) => ({ ...prev, secret: e.target.value }));
                if (validationErrors.secret) {
                  setValidationErrors((prev) => ({ ...prev, secret: '' }));
                }
              }}
              className={validationErrors.secret ? 'is-invalid' : ''}
              disabled={loading}
            />
            {validationErrors.secret && (
              <div className="webhook-form-modal__field-error">
                {validationErrors.secret}
              </div>
            )}
            <small>Used to sign webhook payloads (HMAC-SHA256)</small>
          </div>

          {/* Events Field */}
          <div className="webhook-form-modal__field">
            <label>
              Events <span className="webhook-form-modal__required">*</span>
            </label>
            <div className="webhook-form-modal__events">
              {AVAILABLE_EVENTS.map(({ group, events }) => (
                <div key={group} className="webhook-form-modal__event-group">
                  <div className="webhook-form-modal__event-group-header">
                    <label className="webhook-form-modal__event-group-label">
                      <input
                        type="checkbox"
                        checked={events.every((e) => formData.events.includes(e))}
                        onChange={() => handleSelectAllGroup(events)}
                        disabled={loading}
                      />
                      <strong>{group}</strong>
                    </label>
                  </div>
                  <div className="webhook-form-modal__event-list">
                    {events.map((event) => (
                      <label
                        key={event}
                        className="webhook-form-modal__event-checkbox"
                      >
                        <input
                          type="checkbox"
                          checked={formData.events.includes(event)}
                          onChange={() => handleEventToggle(event)}
                          disabled={loading}
                        />
                        <code className="webhook-form-modal__event-name">
                          {event}
                        </code>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {validationErrors.events && (
              <div className="webhook-form-modal__field-error">
                {validationErrors.events}
              </div>
            )}
          </div>

          {/* Info Section */}
          <div className="webhook-form-modal__info">
            <h4>About Webhooks</h4>
            <ul>
              <li>Webhooks are HTTP POST requests sent to your URL when events occur</li>
              <li>Each request includes a signature header for verification</li>
              <li>
                Failed deliveries are retried automatically with exponential backoff
              </li>
              <li>You can view delivery logs and retry failed deliveries manually</li>
            </ul>
          </div>
        </div>

        <div className="webhook-form-modal__footer">
          <button
            type="button"
            className="webhook-form-modal__cancel"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="webhook-form-modal__submit"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Webhook'}
          </button>
        </div>
      </form>
    </div>
  );
};
