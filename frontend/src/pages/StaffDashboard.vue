<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()
const myTasks = computed(() =>
  store.forStaff(auth.user.id).sort((a, b) => b.priorityScore - a.priorityScore)
)

function statusClass(status) {
  return status.toLowerCase().replace(/\s+/g, '-')
}
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <h2>My Assigned Tasks</h2>
    </div>

    <div v-if="myTasks.length === 0" class="empty-state">
      No complaints assigned to you right now.
    </div>

    <div v-else class="list-stack">
      <div v-for="c in myTasks" :key="c.id" class="card">
        <div class="card-row">
          <div>
            <div class="card-title">{{ c.category }}</div>
            <div class="card-meta">{{ c.location }}, Priority {{ c.priorityScore }}</div>
          </div>
          <span class="badge" :class="statusClass(c.status)">{{ c.status }}</span>
        </div>
        <div class="card-row" style="margin-top: 12px; justify-content: flex-end;">
          <button class="btn secondary" @click="router.push(`/staff/${c.id}`)">Update Task</button>
        </div>
      </div>
    </div>
  </div>
</template>