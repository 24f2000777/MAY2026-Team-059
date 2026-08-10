<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { approveComplaint, exportComplaintsCsv, listComplaintsPage, listOfficers } from '../api/complaintApi'
import { CATEGORIES, categoryLabel } from '../constants/categories'
import StatusBadge from '../components/StatusBadge.vue'
import NotificationBanner from '../components/NotificationBanner.vue'

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

// The backend caps a single page at 100 complaints. Fetching just
// page 1 used to silently drop everything past that, with no
// indication anything was missing. Fetches every page instead, so
// search/filter still work across the whole dataset, the table below
// paginates the (already filtered) results for display. Page 1 has to
// go first to learn total_pages, but the rest don't depend on each
// other, so they're fetched in parallel rather than one round trip at
// a time - the main reason this page used to feel slow to load.
async function loadAllComplaints() {
  const first = await listComplaintsPage({ accessToken: auth.accessToken, page: 1, perPage: 100 })
  const all = [...first.data.complaints]
  const totalPages = first.meta?.total_pages || 1
  if (totalPages > 1) {
    const rest = await Promise.all(
      Array.from({ length: totalPages - 1 }, (_, i) =>
        listComplaintsPage({ accessToken: auth.accessToken, page: i + 2, perPage: 100 })
      )
    )
    for (const { data } of rest) all.push(...data.complaints)
  }
  return all
}

async function load() {
  loadError.value = ''
  try {
    const [allComplaints, officersData] = await Promise.all([
      loadAllComplaints(),
      listOfficers({ accessToken: auth.accessToken })
    ])
    rawComplaints.value = allComplaints
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
    createdAt: c.created_at,
    priorityScore: c.priority_score
  }))
)

const categories = computed(() => ['All', ...new Set(complaints.value.map((c) => c.category))])

// The dashboard's own category filter/table both work off the
// human-readable label (categoryLabel), the export endpoint needs
// the real backend enum value, this maps one back to the other.
const categoryFilterRaw = computed(() => {
  if (categoryFilter.value === 'All') return null
  return CATEGORIES.find((c) => c.label === categoryFilter.value)?.value || null
})

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
    .sort((a, b) => b.priorityScore - a.priorityScore)
)

const PAGE_SIZE = 20
const currentPage = ref(1)

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE_SIZE)))

const paged = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filtered.value.slice(start, start + PAGE_SIZE)
})

// Any filter change can shrink the result set below the page the
// admin was looking at, land back on page 1 rather than showing an
// empty table with a stale "page 4 of 1" underneath it.
watch(filtered, () => {
  currentPage.value = 1
})

function resetFilters() {
  searchText.value = ''
  statusFilter.value = 'All'
  categoryFilter.value = 'All'
  areaFilter.value = ''
  dateFilter.value = ''
}

const exporting = ref(false)
const exportError = ref('')

// Only status/category go to the backend, the same filters GET
// /admin/export actually supports. Search text/area/date are
// client-side-only conveniences (the backend has no free-text or
// substring match), so the export can't fully guarantee "exactly
// what's on screen" once those are in play, just what the backend
// itself is able to narrow down.
async function exportCsv() {
  exportError.value = ''
  exporting.value = true
  try {
    await exportComplaintsCsv({
      accessToken: auth.accessToken,
      status: statusFilter.value === 'All' ? undefined : statusFilter.value,
      category: categoryFilterRaw.value || undefined
    })
  } catch (e) {
    exportError.value = e.message
  } finally {
    exporting.value = false
  }
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
    <NotificationBanner />
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
        <button class="btn secondary" :disabled="exporting" @click="exportCsv">{{ exporting ? 'Exporting...' : 'Export CSV' }}</button>
      </div>

      <p v-if="exportError" class="error-text">{{ exportError }}</p>

      <div v-if="filtered.length === 0" class="empty-state">No complaints match these filters.</div>
      <template v-else>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Category</th>
                <th>Location</th>
                <th>Status</th>
                <th>Assigned</th>
                <th>Filed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in paged" :key="c.id">
                <td><span class="cc-priority">{{ c.priorityScore }}</span></td>
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

        <div v-if="totalPages > 1" class="pagination">
          <button class="btn secondary" :disabled="currentPage === 1" @click="currentPage -= 1">&larr; Prev</button>
          <span class="pagination-status">Page {{ currentPage }} of {{ totalPages }} &middot; {{ filtered.length }} complaints</span>
          <button class="btn secondary" :disabled="currentPage === totalPages" @click="currentPage += 1">Next &rarr;</button>
        </div>
      </template>
    </div>
  </div>
</template>
<style scoped>
.row-actions { display: flex; gap: 8px; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 16px; }
.pagination-status { font-size: 13px; color: var(--text-dim); }
</style>
