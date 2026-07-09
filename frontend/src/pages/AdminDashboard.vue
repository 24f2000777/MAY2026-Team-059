<script setup>
import { useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'

const store = useComplaintStore()
const router = useRouter()

function statusClass(status) {
  return status.toLowerCase().replace(/\s+/g, '-')
}

function assignedName(complaint) {
  const staff = store.staffList.find((s) => s.id === complaint.assignedStaffId)
  return staff ? staff.name : 'Unassigned'
}
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <h2>All Complaints</h2>
    </div>

    <div v-if="store.complaints.length === 0" class="empty-state">
      No complaints have been filed yet.
    </div>

    <div v-else class="list-stack">
      <div v-for="c in store.complaints" :key="c.id" class="card">
        <div class="card-row">
          <div>
            <div class="card-title">{{ c.category }}</div>
            <div class="card-meta">{{ c.location }}, {{ assignedName(c) }}</div>
          </div>
          <span class="badge" :class="statusClass(c.status)">{{ c.status }}</span>
        </div>
        <div class="card-row" style="margin-top: 12px; justify-content: flex-end;">
          <button class="btn secondary" @click="router.push(`/admin/assign/${c.id}`)">
            {{ c.assignedStaffId ? 'Reassign' : 'Assign' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>