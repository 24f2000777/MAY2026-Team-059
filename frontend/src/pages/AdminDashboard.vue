<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'
import StatusBadge from '../components/StatusBadge.vue'

const store = useComplaintStore()
const router = useRouter()
const statusFilter = ref('All')
const categoryFilter = ref('All')
const areaFilter = ref('')
const dateFilter = ref('')
const categories = computed(() => ['All', ...new Set(store.complaints.map((c) => c.category))])

const filtered = computed(() =>
  store.complaints
    .filter((c) => statusFilter.value === 'All' || c.status === statusFilter.value)
    .filter((c) => categoryFilter.value === 'All' || c.category === categoryFilter.value)
    .filter((c) => !areaFilter.value || c.location.toLowerCase().includes(areaFilter.value.toLowerCase()))
    .filter((c) => !dateFilter.value || new Date(c.createdAt).toISOString().slice(0, 10) === dateFilter.value)
    .sort((a, b) => b.createdAt - a.createdAt)
)
</script>

<template>
  <div class="app-content">
    <h2>Admin Dashboard</h2>
    <div class="filter-bar">
      <select v-model="statusFilter"><option>All</option><option>Submitted</option><option>In Progress</option><option>Resolved</option></select>
      <select v-model="categoryFilter"><option v-for="c in categories" :key="c" :value="c">{{ c }}</option></select>
      <input v-model="areaFilter" placeholder="Filter by area" />
      <input v-model="dateFilter" type="date" />
    </div>
    <div v-if="filtered.length === 0" class="empty-state">No complaints match these filters.</div>
    <div v-else class="card table-wrap">
      <table class="data-table">
        <thead><tr><th>Category</th><th>Location</th><th>Severity</th><th>Status</th><th>Assigned</th><th>Filed</th><th></th></tr></thead>
        <tbody>
          <tr v-for="c in filtered" :key="c.id">
            <td>{{ c.category }}</td>
            <td>{{ c.location }}</td>
            <td><StatusBadge :value="c.severity" kind="severity" /></td>
            <td><StatusBadge :value="c.status" /></td>
            <td>{{ store.staffList.find((s) => s.id === c.assignedStaffId)?.name || 'Unassigned' }}</td>
            <td>{{ new Date(c.createdAt).toLocaleDateString() }}</td>
            <td><button class="btn secondary" @click="router.push(`/admin/assign/${c.id}`)">{{ c.assignedStaffId ? 'Reassign' : 'Assign' }}</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<style scoped>
.table-wrap { overflow-x: auto; }
</style>