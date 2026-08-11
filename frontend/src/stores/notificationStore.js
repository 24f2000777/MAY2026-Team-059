import { defineStore } from 'pinia'
import { getUnreadCount } from '../api/notificationApi'

// Shared unread count, read by the navbar bell badge and by
// NotificationBanner.vue on each dashboard. Both call refresh() on
// their own mount so the count is fresh wherever it's shown, they
// just happen to share one number rather than tracking their own.
export const useNotificationStore = defineStore('notification', {
  state: () => ({
    unreadCount: 0
  }),
  actions: {
    async refresh(accessToken) {
      if (!accessToken) return
      try {
        const data = await getUnreadCount({ accessToken })
        this.unreadCount = data.unread_count
      } catch {
        // Secondary to whatever page is actually loading, fail silently
        // rather than surfacing an error banner for a badge/reminder.
      }
    }
  }
})
