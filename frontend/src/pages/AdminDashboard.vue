<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'
import StatusBadge from '../components/StatusBadge.vue'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()

const searchText = ref('')
const statusFilter = ref('All')
const categoryFilter = ref('All')
const areaFilter = ref('')
const dateFilter = ref('')

const categories = computed(() => ['All', ...new Set(store.complaints.map((c) => c.category))])

const unassignedCount = computed(() => store.complaints.filter((c) => !c.assignedStaffId).length)
const openCount = computed(() => store.complaints.filter((c) => c.status !== 'Resolved').length)
const resolvedCount = computed(() => store.complaints.filter((c) => c.status === 'Resolved').length)

const filtered = computed(() =>
  store.complaints
    .filter((c) => {
      if (!searchText.value) return true
      const q = searchText.value.toLowerCase()
      return c.category.toLowerCase().includes(q) || c.location.toLowerCase().includes(q)
    })
    .filter((c) => statusFilter.value === 'All' || c.status === statusFilter.value)
    .filter((c) => categoryFilter.value === 'All' || c.category === categoryFilter.value)
    .filter((c) => !areaFilter.value || c.location.toLowerCase().includes(areaFilter.value.toLowerCase()))
    .filter((c) => !dateFilter.value || new Date(c.createdAt).toISOString().slice(0, 10) === dateFilter.value)
    .sort((a, b) => b.createdAt - a.createdAt)
)

function resetFilters() {
  searchText.value = ''
  statusFilter.value = 'All'
  categoryFilter.value = 'All'
  areaFilter.value = ''
  dateFilter.value = ''
}
</script>

<template>
  <div class="app-content">
    <div class="ops-hero">
      <div class="ops-hero-intro">
        <p class="ops-hero-eyebrow">Operations Overview</p>
        <h1 class="ops-hero-title">Welcome, {{ auth.user?.name }}</h1>
        <p class="ops-hero-sub">Every complaint across every ward, searchable and filterable in one screen.</p>

        <div class="ops-search">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="M21 21l-4.35-4.35"></path></svg>
          <input v-model="searchText" type="text" placeholder="Search by category or location..." />
        </div>
      </div>

      <div class="ops-summary">
        <p class="ops-summary-title">Live Snapshot</p>
        <div class="ops-summary-row">
          <span>Total Complaints</span>
          <strong>{{ store.complaints.length }}</strong>
        </div>
        <div class="ops-summary-row">
          <span>Open</span>
          <strong>{{ openCount }}</strong>
        </div>
        <div class="ops-summary-row">
          <span>Resolved</span>
          <strong>{{ resolvedCount }}</strong>
        </div>
        <div class="ops-summary-row">
          <span>Unassigned</span>
          <strong>{{ unassignedCount }}</strong>
        </div>
        <div class="ops-summary-row">
          <span>Staff Available</span>
          <strong>{{ store.staffList.length }}</strong>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="filter-toolbar">
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
          <label>Category</label>
          <select v-model="categoryFilter">
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <div class="filter-group">
          <label>Area</label>
          <input v-model="areaFilter" type="text" placeholder="e.g. Andheri" />
        </div>

        <div class="filter-group">
          <label>Date Filed</label>
          <input v-model="dateFilter" type="date" />
        </div>

        <button class="btn secondary filter-reset" @click="resetFilters">Clear Filters</button>
      </div>

      <div v-if="filtered.length === 0" class="empty-state">No complaints match these filters.</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Location</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Assigned</th>
              <th>Filed</th>
              <th></th>
            </tr>
          </thead>
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
  </div>
</template>