<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { listComplaints } from '../api/complaintApi'
import { categoryLabel } from '../constants/categories'
import ComplaintCard from '../components/ComplaintCard.vue'
import DashboardHero from '../components/DashboardHero.vue'
import ActionTile from '../components/ActionTile.vue'

const auth = useAuthStore()
const router = useRouter()

const STATUSES = [
  { value: 'All', label: 'All' },
  { value: 'approved', label: 'Approved' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' }
]

const searchText = ref('')
const statusFilter = ref('All')
const loadError = ref('')
const rawComplaints = ref([])

const allTasks = computed(() =>
  rawComplaints.value
    .map((c) => ({
      id: c.id,
      category: categoryLabel(c.category),
      status: c.status,
      description: c.description,
      location: c.location_text || 'No location recorded',
      priorityScore: c.priority_score,
      createdAt: c.created_at
    }))
    .sort((a, b) => b.priorityScore - a.priorityScore)
)

const myTasks = computed(() =>
  allTasks.value
    .filter((c) => statusFilter.value === 'All' || c.status === statusFilter.value)
    .filter((c) => !searchText.value || c.category.toLowerCase().includes(searchText.value.toLowerCase()) || c.location.toLowerCase().includes(searchText.value.toLowerCase()))
)

onMounted(async () => {
  try {
    const data = await listComplaints({ accessToken: auth.accessToken, assignedTo: auth.user.id })
    rawComplaints.value = data.complaints
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  }
})
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

    <p v-if="loadError" class="error-text">{{ loadError }}</p>

    <div v-if="allTasks.length > 0" class="card">
      <div class="filter-toolbar">
        <div class="filter-group">
          <label>Search</label>
          <input v-model="searchText" type="text" placeholder="Category or location..." />
        </div>
        <div class="filter-group">
          <label>Status</label>
          <select v-model="statusFilter">
            <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
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
