<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { approveComplaint, listComplaints, listOfficers } from '../api/complaintApi'
import { categoryLabel } from '../constants/categories'
import StatusBadge from '../components/StatusBadge.vue'

const auth = useAuthStore()
const router = useRouter()

const searchText = ref('')
const statusFilter = ref('All')
const categoryFilter = ref('All')
const areaFilter = ref('')
const dateFilter = ref('')
const loadError = ref('')
const actionError = ref('')
const rawComplaints = ref([])
const officers = ref([])

const STATUSES = ['All', 'submitted', 'approved', 'in_progress', 'resolved', 'closed', 'rejected', 'withdrawn']

function localDate(iso) {
  const d = new Date(iso)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

async function load() {
  loadError.value = ''
  try {
    const [complaintsData, officersData] = await Promise.all([
      listComplaints({ accessToken: auth.accessToken }),
      listOfficers({ accessToken: auth.accessToken })
    ])
    rawComplaints.value = complaintsData.complaints
    officers.value = officersData.officers
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  }
}

const complaints = computed(() =>
  rawComplaints.value.map((c) => ({
    id: c.id,
    category: categoryLabel(c.category),
    categoryRaw: c.category,
    status: c.status,
    location: c.location_text || 'No location recorded',
    assignedTo: c.assigned_to,
    createdAt: c.created_at
  }))
)

const categories = computed(() => ['All', ...new Set(complaints.value.map((c) => c.category))])

const unassignedCount = computed(() => complaints.value.filter((c) => !c.assignedTo).length)
const openCount = computed(() => complaints.value.filter((c) => !['resolved', 'closed', 'rejected', 'withdrawn'].includes(c.status)).length)
const resolvedCount = computed(() => complaints.value.filter((c) => c.status === 'resolved' || c.status === 'closed').length)

const filtered = computed(() =>
  complaints.value
    .filter((c) => {
      if (!searchText.value) return true
      const q = searchText.value.toLowerCase()
      return c.category.toLowerCase().includes(q) || c.location.toLowerCase().includes(q)
    })
    .filter((c) => statusFilter.value === 'All' || c.status === statusFilter.value)
    .filter((c) => categoryFilter.value === 'All' || c.category === categoryFilter.value)
    .filter((c) => !areaFilter.value || c.location.toLowerCase().includes(areaFilter.value.toLowerCase()))
    .filter((c) => !dateFilter.value || localDate(c.createdAt) === dateFilter.value)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
)

function resetFilters() {
  searchText.value = ''
  statusFilter.value = 'All'
  categoryFilter.value = 'All'
  areaFilter.value = ''
  dateFilter.value = ''
}

function officerName(id) {
  return officers.value.find((o) => o.id === id)?.name || 'Unassigned'
}

async function doApprove(id) {
  actionError.value = ''
  try {
    await approveComplaint({ id, accessToken: auth.accessToken })
    await load()
  } catch (e) {
    actionError.value = e.message
  }
}

onMounted(load)
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
          <strong>{{ complaints.length }}</strong>
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
          <strong>{{ officers.length }}</strong>
        </div>
      </div>
    </div>

    <p v-if="loadError" class="error-text">{{ loadError }}</p>
    <p v-if="actionError" class="error-text">{{ actionError }}</p>

    <div class="card">
      <div class="filter-toolbar">
        <div class="filter-group">
          <label>Status</label>
          <select v-model="statusFilter">
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
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
              <td><StatusBadge :value="c.status" /></td>
              <td>{{ officerName(c.assignedTo) }}</td>
              <td>{{ new Date(c.createdAt).toLocaleDateString() }}</td>
              <td class="row-actions">
                <button v-if="c.status === 'submitted'" class="btn secondary" @click="doApprove(c.id)">Approve</button>
                <button class="btn secondary" @click="router.push(`/admin/assign/${c.id}`)">{{ c.assignedTo ? 'Reassign' : 'Assign' }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
<style scoped>
.row-actions { display: flex; gap: 8px; }
</style>
