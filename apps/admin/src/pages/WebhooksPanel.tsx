/**
 * Webhooks Panel Page
 * Manage webhooks and view their logs
 */

import React, { useState } from 'react';
import { WebhooksList } from '../features/webhooks/WebhooksList';
import { WebhookLogs } from '../features/webhooks/WebhookLogs';
import { WebhookForm } from '../features/webhooks/WebhookForm';
import { Webhook } from '../services/webhooks';
import '../features/webhooks/styles.css';
import '../features/webhooks/webhooks-page.css';

export const WebhooksPanel: React.FC = () => {
  const [selectedWebhook, setSelectedWebhook] = useState<Webhook | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<Webhook | null>(null);

  const handleEditWebhook = (webhook: Webhook) => {
    setEditingWebhook(webhook);
    setShowForm(true);
  };

  const handleCreateWebhook = () => {
    setEditingWebhook(null);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingWebhook(null);
  };

  const handleFormSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
    handleFormClose();
  };

  return (
    <div className="webhooks-panel">
      <div className="webhooks-panel__header">
        <h1 className="webhooks-panel__title">Webhooks</h1>
        <button
          className="webhooks-panel__create-btn"
          onClick={handleCreateWebhook}
        >
          <svg className="webhooks-panel__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nuevo Webhook
        </button>
      </div>

      <div className="webhooks-panel__content">
        <WebhooksList 
          onEdit={handleEditWebhook} 
          onRefresh={handleFormSuccess} 
          key={refreshTrigger} 
        />

        {selectedWebhook && (
          <div className="webhooks-panel__logs">
            <WebhookLogs webhookId={selectedWebhook.id} />
          </div>
        )}
      </div>

      {showForm && (
        <WebhookForm
          webhook={editingWebhook}
          onClose={handleFormClose}
          onSuccess={handleFormSuccess}
        />
      )}
    </div>
  );
};
