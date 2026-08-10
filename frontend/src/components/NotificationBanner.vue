<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useNotificationStore } from '../stores/notificationStore'

const auth = useAuthStore()
const notification = useNotificationStore()

// Local to this mount, not persisted - dismissing just hides it for
// this visit, it reappears next time the dashboard is opened if
// there's still something unread, which is the point (a reminder,
// not a one-time toast).
const dismissed = ref(false)

onMounted(() => {
  notification.refresh(auth.accessToken)
})
</script>

<template>
  <div v-if="!dismissed && notification.unreadCount > 0" class="notification-banner">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
    <span>
      You have {{ notification.unreadCount }} unread notification{{ notification.unreadCount > 1 ? 's' : '' }}.
    </span>
    <router-link to="/notifications" class="notification-banner-link">View</router-link>
    <button type="button" class="notification-banner-dismiss" @click="dismissed = true" aria-label="Dismiss">&times;</button>
  </div>
</template>

<style scoped>
.notification-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
  border: 1px solid rgba(47, 143, 91, .25);
  border-radius: 12px;
  background: rgba(47, 143, 91, .08);
  color: var(--accent-dark);
  font-size: 13px;
  font-weight: 650;
}

.notification-banner svg {
  flex-shrink: 0;
}

.notification-banner span {
  flex: 1;
}

.notification-banner-link {
  color: var(--accent-dark);
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 2px;
  white-space: nowrap;
}

.notification-banner-dismiss {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--accent-dark);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
}

.notification-banner-dismiss:hover {
  background: rgba(47, 143, 91, .14);
}
</style>
