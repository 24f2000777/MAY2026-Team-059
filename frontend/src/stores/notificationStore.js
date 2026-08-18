import { defineStore } from 'pinia'
import { getUnreadCount } from '../api/notificationApi'

// Shared unread count, read by the navbar bell badge and by
// NotificationBanner.vue on each dashboard. Both call refresh() on
// their own mount so the count is fresh wherever it's shown, they
// just happen to share one number rather than tracking their own.
export const useNotificationStore = defineStore('notification', {
  state: () => ({
    unreadCount: 0,
    // The navbar and a dashboard's NotificationBanner both mount (and
    // both call refresh()) on the same page load, one right after the
    // other. Without this, that's two separate network requests for
    // the exact same number. Tracking the in-flight request lets a
    // second caller that shows up while the first is still pending
    // just await the same one instead of firing its own.
    _pending: null
  }),
  actions: {
    async refresh(accessToken) {
      if (!accessToken) return
      if (this._pending) return this._pending

      this._pending = (async () => {
        try {
          const data = await getUnreadCount({ accessToken })
          this.unreadCount = data.unread_count
        } catch {
          // Secondary to whatever page is actually loading, fail silently
          // rather than surfacing an error banner for a badge/reminder.
        } finally {
          this._pending = null
        }
      })()

      return this._pending
    }
  }
})
