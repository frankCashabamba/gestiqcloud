/**
 * Notifications Page
 * Full page view for notification center
 */

import React from 'react';
import { NotificationCenter } from '../features/notifications/NotificationCenter';
import '../features/notifications/styles.css';

export const Notifications: React.FC = () => {
  return (
    <div className="notifications-page">
      <NotificationCenter />
    </div>
  );
};
