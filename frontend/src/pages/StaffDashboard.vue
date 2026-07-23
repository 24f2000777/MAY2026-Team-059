<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'
import ComplaintCard from '../components/ComplaintCard.vue'
import DashboardHero from '../components/DashboardHero.vue'
import ActionTile from '../components/ActionTile.vue'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()

const searchText = ref('')
const statusFilter = ref('All')
const severityFilter = ref('All')

const allTasks = computed(() => store.forStaff(auth.user.id).sort((a, b) => b.priorityScore - a.priorityScore))

const myTasks = computed(() =>
  allTasks.value
    .filter((c) => statusFilter.value === 'All' || c.status === statusFilter.value)
    .filter((c) => severityFilter.value === 'All' || c.severity === severityFilter.value)
    .filter((c) => !searchText.value || c.category.toLowerCase().includes(searchText.value.toLowerCase()) || c.location.toLowerCase().includes(searchText.value.toLowerCase()))
)
</script>

<template>
  <div class="app-content">
    <DashboardHero :name="auth.user?.name" subtitle="Here's what needs your attention today.">
      <template #actions>
        <ActionTile to="/staff" label="My Tasks" sublabel="Sorted by priority">
          <template #icon>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
          </template>
        </ActionTile>
        <ActionTile to="/staff/analytics" label="Analytics" sublabel="My performance">
          <template #icon>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"></path><path d="M7 15l4-4 3 3 5-6"></path></svg>
          </template>
        </ActionTile>
        <ActionTile to="/nagrik-saathi" label="Nagrik Saathi" sublabel="Ask a question">
          <template #icon>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          </template>
        </ActionTile>
        <ActionTile to="/notifications" label="Notifications" sublabel="Recent updates">
          <template #icon>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
          </template>
        </ActionTile>
      </template>
    </DashboardHero>

    <div class="header-row">
      <h2>My Assigned Tasks</h2>
    </div>

    <div v-if="allTasks.length > 0" class="card">
      <div class="filter-toolbar">
        <div class="filter-group">
          <label>Search</label>
          <input v-model="searchText" type="text" placeholder="Category or location..." />
        </div>
        <div class="filter-group">
          <label>Status</label>
          <select v-model="statusFilter">
            <option>All</option>
            <option>Submitted</option>
            <option>In Progress</option>
            <option>Resolved</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Severity</label>
          <select v-model="severityFilter">
            <option>All</option>
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </select>
        </div>
      </div>
    </div>

    <div v-if="allTasks.length === 0" class="empty-state">
      No complaints assigned to you right now.
    </div>
    <div v-else-if="myTasks.length === 0" class="empty-state">
      No tasks match your filters.
    </div>

    <div v-else class="grid cols-2">
      <ComplaintCard v-for="c in myTasks" :key="c.id" :complaint="c" show-priority>
        <template #actions>
          <button class="btn secondary" @click="router.push(`/staff/${c.id}`)">Update Task</button>
        </template>
      </ComplaintCard>
    </div>
  </div>
</template>