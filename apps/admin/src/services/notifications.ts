/**
 * Notifications Service
 * Handles notification-related API calls
 */

import apiClient from './api';

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  read: boolean;
  created_at: string;
  updated_at?: string;
  related_entity?: {
    type: string;
    id: string;
    name: string;
  };
}

export interface NotificationResponse {
  notifications: Notification[];
  total: number;
  unread: number;
}

export async function getNotifications(params?: {
  limit?: number;
  offset?: number;
  read?: boolean;
}): Promise<NotificationResponse> {
  return apiClient.notifications.list(params);
}

export async function getNotification(notificationId: string): Promise<Notification> {
  return apiClient.notifications.get(notificationId);
}

export async function markAsRead(notificationId: string): Promise<Notification> {
  return apiClient.notifications.markAsRead(notificationId);
}

export async function markAllAsRead(): Promise<void> {
  // This would need to be added to the API client if not already present
  // For now, we'll implement it as a batch operation
  try {
    const response = await apiClient.notifications.list({ limit: 1000 });
    const unreadNotifications = response.notifications.filter((n) => !n.read);
    
    await Promise.all(
      unreadNotifications.map((n) => markAsRead(n.id))
    );
  } catch (error) {
    console.error('Failed to mark all notifications as read:', error);
    throw error;
  }
}
