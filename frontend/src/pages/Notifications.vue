<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()

const relevantComplaints = computed(() => {
  if (auth.role === 'citizen') return store.forCitizen(auth.user.id)
  if (auth.role === 'staff') return store.forStaff(auth.user.id)
  return store.complaints
})

const feed = computed(() => {
  const items = []
  relevantComplaints.value.forEach((c) => {
    c.history.forEach((h) => {
      items.push({
        complaintId: c.id,
        category: c.category,
        status: h.status,
        note: h.note,
        at: h.at
      })
    })
  })
  return items.sort((a, b) => b.at - a.at).slice(0, 30)
})

function goTo(complaintId) {
  if (auth.role === 'citizen') router.push(`/citizen/${complaintId}`)
  else if (auth.role === 'staff') router.push(`/staff/${complaintId}`)
  else router.push('/admin')
}

function iconFor(status) {
  if (status === 'Resolved') return '✓'
  if (status === 'In Progress') return '→'
  return '•'
}
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>Notifications</h2>
        <p class="page-intro">Recent status changes on complaints relevant to you.</p>
      </div>
    </div>

    <div v-if="feed.length === 0" class="empty-state">No notifications yet.</div>

    <div v-else class="list-stack">
      <div v-for="(item, i) in feed" :key="i" class="card notif-card" @click="goTo(item.complaintId)">
        <span class="notif-icon" :class="`accent-${item.status.toLowerCase().replace(/\s+/g,'-')}`">{{ iconFor(item.status) }}</span>
        <div class="notif-body">
          <p class="notif-title"><strong>{{ item.category }}</strong> - {{ item.status }}</p>
          <p class="notif-note">{{ item.note }}</p>
          <span class="notif-time">{{ new Date(item.at).toLocaleString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notif-card { display: flex; gap: 14px; align-items: flex-start; cursor: pointer; }
.notif-icon {
  flex-shrink: 0; width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; color: #fff; background: var(--accent);
}
.notif-icon.accent-submitted { background: var(--warn); }
.notif-icon.accent-in-progress { background: var(--accent); }
.notif-icon.accent-resolved { background: var(--ok); }
.notif-title { margin: 0; font-size: 14px; }
.notif-note { margin: 4px 0 0 0; font-size: 13px; color: var(--text-dim); }
.notif-time { font-size: 12px; color: var(--text-dim); }
</style>