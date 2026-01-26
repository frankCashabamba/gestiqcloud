/**
 * Notification Center Component
 * Displays notifications list with filtering and actions
 */

import React, { useState } from 'react';
import { useNotifications } from '../../hooks/useNotifications';
import './styles.css';

export const NotificationCenter: React.FC = () => {
  const {
    notifications,
    unreadCount,
    loading,
    error,
    markAsRead,
    markAllAsRead,
  } = useNotifications(true, 10000);
  
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  const filteredNotifications =
    filter === 'unread'
      ? notifications.filter((n) => !n.read)
      : notifications;

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return (
          <svg className="notification-item__icon notification-item__icon--success" viewBox="0 0 24 24" fill="currentColor">
            <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="notification-item__icon notification-item__icon--warning" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
        );
      case 'error':
        return (
          <svg className="notification-item__icon notification-item__icon--error" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
        );
      default:
        return (
          <svg className="notification-item__icon notification-item__icon--info" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
          </svg>
        );
    }
  };

  return (
    <div className="notification-center">
      <div className="notification-center__header">
        <h2 className="notification-center__title">Notificaciones</h2>
        <div className="notification-center__actions">
          {unreadCount > 0 && (
            <button
              className="notification-center__mark-all-btn"
              onClick={() => markAllAsRead()}
              title="Marcar todas como leídas"
            >
              Marcar todas como leídas
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="notification-center__error">
          Error al cargar notificaciones: {error.message}
        </div>
      )}

      <div className="notification-center__filters">
        <button
          className={`notification-center__filter ${filter === 'all' ? 'is-active' : ''}`}
          onClick={() => setFilter('all')}
        >
          Todas ({notifications.length})
        </button>
        <button
          className={`notification-center__filter ${filter === 'unread' ? 'is-active' : ''}`}
          onClick={() => setFilter('unread')}
        >
          Sin leer ({unreadCount})
        </button>
      </div>

      <div className="notification-center__list">
        {loading ? (
          <div className="notification-center__loading">
            <p>Cargando notificaciones...</p>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="notification-center__empty">
            <p>{filter === 'unread' ? 'No hay notificaciones sin leer' : 'No hay notificaciones'}</p>
          </div>
        ) : (
          filteredNotifications.map((notification) => (
            <div
              key={notification.id}
              className={`notification-item ${!notification.read ? 'is-unread' : ''}`}
              onClick={() => !notification.read && markAsRead(notification.id)}
            >
              <div className="notification-item__icon-wrapper">
                {getNotificationIcon(notification.type)}
              </div>
              <div className="notification-item__content">
                <h3 className="notification-item__title">{notification.title}</h3>
                <p className="notification-item__message">{notification.message}</p>
                {notification.related_entity && (
                  <p className="notification-item__entity">
                    {notification.related_entity.name}
                  </p>
                )}
                <span className="notification-item__time">
                  {new Date(notification.created_at).toLocaleDateString('es-ES', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
              {!notification.read && (
                <div className="notification-item__unread-indicator"></div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
