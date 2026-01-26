/**
 * Notifications Hook
 * Manages notification state and fetching
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getNotifications,
  markAsRead,
  markAllAsRead,
  Notification,
  NotificationResponse,
} from '../services/notifications';

interface UseNotificationsReturn {
  notifications: Notification[];
  unreadCount: number;
  total: number;
  loading: boolean;
  error: Error | null;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  refetch: () => Promise<void>;
}

const DEFAULT_POLL_INTERVAL = 10000; // 10 seconds

export function useNotifications(
  autoRefresh = true,
  pollInterval = DEFAULT_POLL_INTERVAL
): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getNotifications({ limit: 50 });
      setNotifications(response.notifications);
      setUnreadCount(response.unread);
      setTotal(response.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch notifications'));
      console.error('Notifications error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleMarkAsRead = useCallback(
    async (notificationId: string) => {
      try {
        await markAsRead(notificationId);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (err) {
        console.error('Failed to mark notification as read:', err);
        throw err;
      }
    },
    []
  );

  const handleMarkAllAsRead = useCallback(async () => {
    try {
      await markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err);
      throw err;
    }
  }, []);

  useEffect(() => {
    fetchNotifications();

    if (!autoRefresh) return;

    const interval = setInterval(fetchNotifications, pollInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, pollInterval, fetchNotifications]);

  return {
    notifications,
    unreadCount,
    total,
    loading,
    error,
    markAsRead: handleMarkAsRead,
    markAllAsRead: handleMarkAllAsRead,
    refetch: fetchNotifications,
  };
}
