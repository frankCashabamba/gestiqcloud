/**
 * Webhooks Panel Page
 * Manage webhooks and view their logs
 */

import React, { useState } from 'react';
import { WebhooksList } from '../features/webhooks/WebhooksList';
import { WebhookLogs } from '../features/webhooks/WebhookLogs';
import { Webhook } from '../services/webhooks';
import '../features/webhooks/styles.css';
import '../features/webhooks/webhooks-page.css';

export const WebhooksPanel: React.FC = () => {
  const [selectedWebhook, setSelectedWebhook] = useState<Webhook | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleEditWebhook = (webhook: Webhook) => {
    setSelectedWebhook(webhook);
    // TODO: Open webhook form modal
    console.log('Edit webhook:', webhook);
  };

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="webhooks-panel">
      <div className="webhooks-panel__header">
        <h1 className="webhooks-panel__title">Webhooks</h1>
        <button
          className="webhooks-panel__create-btn"
          onClick={() => {
            // TODO: Open webhook form modal for creating new webhook
            console.log('Create new webhook');
          }}
        >
          <svg className="webhooks-panel__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Webhook
        </button>
      </div>

      <div className="webhooks-panel__content">
        <WebhooksList onEdit={handleEditWebhook} onRefresh={handleRefresh} key={refreshTrigger} />

        {selectedWebhook && (
          <div className="webhooks-panel__logs">
            <WebhookLogs webhookId={selectedWebhook.id} />
          </div>
        )}
      </div>
    </div>
  );
};
