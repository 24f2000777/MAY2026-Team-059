// Real backend calls for /notifications. Same pattern as
// complaintApi.js: thin wrappers around request() from httpClient.js.
import { request } from './httpClient'

export function listNotifications({ accessToken }) {
  return request('/notifications', { token: accessToken })
}

export function getUnreadCount({ accessToken }) {
  return request('/notifications/unread-count', { token: accessToken })
}

export function markNotificationRead({ id, accessToken }) {
  return request(`/notifications/${id}/read`, { method: 'PATCH', token: accessToken })
}

export function markAllNotificationsRead({ accessToken }) {
  return request('/notifications/read-all', { method: 'PATCH', token: accessToken })
}

export function deleteNotification({ id, accessToken }) {
  return request(`/notifications/${id}`, { method: 'DELETE', token: accessToken })
}

export function updateNotificationPreferences({ emailEnabled, accessToken }) {
  return request('/notifications/preferences', {
    method: 'POST',
    token: accessToken,
    body: { email_enabled: emailEnabled }
  })
}
