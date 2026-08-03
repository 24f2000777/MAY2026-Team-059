<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { deleteNotification, listNotifications, markAllNotificationsRead, markNotificationRead } from '../api/notificationApi'

const auth = useAuthStore()
const router = useRouter()

const notifications = ref([])
const loading = ref(true)
const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await listNotifications({ accessToken: auth.accessToken })
    notifications.value = data.notifications
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

async function open(item) {
  if (!item.is_read) {
    try {
      await markNotificationRead({ id: item.id, accessToken: auth.accessToken })
      item.is_read = true
    } catch {
      // Non-fatal, navigating away regardless is fine even if the
      // read-marking call itself failed.
    }
  }
  if (item.complaint_id) {
    if (auth.role === 'citizen') router.push(`/citizen/${item.complaint_id}`)
    else if (auth.role === 'staff') router.push(`/staff/${item.complaint_id}`)
    else router.push('/admin')
  }
}

async function markAllRead() {
  try {
    await markAllNotificationsRead({ accessToken: auth.accessToken })
    notifications.value = notifications.value.map((n) => ({ ...n, is_read: true }))
  } catch (e) {
    loadError.value = e.message
  }
}

async function remove(item) {
  try {
    await deleteNotification({ id: item.id, accessToken: auth.accessToken })
    notifications.value = notifications.value.filter((n) => n.id !== item.id)
  } catch (e) {
    loadError.value = e.message
  }
}

function iconFor(type) {
  if (type.includes('resolved') || type.includes('closed')) return '✓'
  if (type.includes('progress') || type.includes('assigned')) return '→'
  if (type.includes('rejected')) return '✕'
  return '•'
}

onMounted(load)
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>Notifications</h2>
        <p class="page-intro">Updates on complaints relevant to you.</p>
      </div>
      <button v-if="notifications.some((n) => !n.is_read)" class="btn secondary" @click="markAllRead">Mark all as read</button>
    </div>

    <p v-if="loadError" class="error-text">{{ loadError }}</p>
    <p v-else-if="loading" class="page-intro">Loading...</p>

    <div v-else-if="notifications.length === 0" class="empty-state">No notifications yet.</div>

    <div v-else class="list-stack">
      <div
        v-for="item in notifications" :key="item.id"
        class="card notif-card"
        :class="{ unread: !item.is_read }"
        @click="open(item)"
      >
        <span class="notif-icon" :class="`accent-${item.type}`">{{ iconFor(item.type) }}</span>
        <div class="notif-body">
          <p class="notif-title"><strong>{{ item.title }}</strong></p>
          <p class="notif-note">{{ item.message }}</p>
          <span class="notif-time">{{ new Date(item.created_at).toLocaleString() }}</span>
        </div>
        <button class="btn secondary notif-remove" @click.stop="remove(item)">Dismiss</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notif-card { display: flex; gap: 14px; align-items: flex-start; cursor: pointer; }
.notif-card.unread { border-color: var(--accent); }
.notif-icon {
  flex-shrink: 0; width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; color: #fff; background: var(--accent);
}
.notif-body { flex: 1; }
.notif-icon.accent-complaint_resolved,
.notif-icon.accent-complaint_closed { background: var(--ok); }
.notif-icon.accent-complaint_rejected { background: var(--danger, #c0392b); }
.notif-title { margin: 0; font-size: 14px; }
.notif-note { margin: 4px 0 0 0; font-size: 13px; color: var(--text-dim); }
.notif-time { font-size: 12px; color: var(--text-dim); }
.notif-remove { flex-shrink: 0; }
</style>
