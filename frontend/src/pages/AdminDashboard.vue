<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { approveComplaint, exportComplaintsCsv, listComplaintsPage, listOfficers, rejectComplaint } from '../api/complaintApi'
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

// Assign only makes sense once a complaint has cleared the
// approve/reject decision, and the backend itself rejects assigning
// a complaint that's already terminal (COMP_003), so the button
// shouldn't offer that here either.
const TERMINAL_STATUSES = ['resolved', 'closed', 'rejected', 'withdrawn']
function canAssign(status) {
  return status !== 'submitted' && !TERMINAL_STATUSES.includes(status)
}

// approve/reject only change one complaint's status, patching it
// locally from the transition response is enough - reloading every
// page of every complaint (loadAllComplaints) just to reflect one row
// changing is what made the button feel slow, this avoids that
// entirely instead of just making the same wasted refetch cheaper.
function patchComplaint(data) {
  const target = rawComplaints.value.find((c) => c.id === data.id)
  if (target) {
    target.status = data.status
    target.assigned_to = data.assigned_to
    target.updated_at = data.updated_at
  }
}

async function doApprove(id) {
  actionError.value = ''
  try {
    const data = await approveComplaint({ id, accessToken: auth.accessToken })
    patchComplaint(data)
  } catch (e) {
    actionError.value = e.message
  }
}

async function doReject(id) {
  const reason = prompt('Reason for rejecting this complaint:')
  if (!reason || !reason.trim()) return
  actionError.value = ''
  try {
    const data = await rejectComplaint({ id, reason: reason.trim(), accessToken: auth.accessToken })
    patchComplaint(data)
  } catch (e) {
    actionError.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div class="app-content admin-dashboard">
    <NotificationBanner />

    <!-- HERO -->
    <section class="ops-hero">
      <div class="ops-hero-intro">
        <div class="hero-kicker">
          <span class="hero-kicker-dot"></span>
          OPERATIONS CENTER
        </div>

        <h1 class="ops-hero-title">
          Welcome back, {{ auth.user?.name }}
        </h1>

        <p class="ops-hero-sub">
          Monitor, prioritize and manage complaints across every ward from one place.
        </p>

        <div class="ops-search">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <path d="M21 21l-4.35-4.35"></path>
          </svg>

          <input
            v-model="searchText"
            type="text"
            placeholder="Search complaints by category or location..."
          />

          <span v-if="searchText" class="search-result-hint">
            {{ filtered.length }} results
          </span>
        </div>
      </div>

      <!-- LIVE SNAPSHOT -->
      <div class="ops-summary">
        <div class="summary-header">
          <div>
            <p class="ops-summary-title">Live Snapshot</p>
            <span class="summary-subtitle">Current system overview</span>
          </div>

          <span class="live-indicator">
            <span></span>
            Live
          </span>
        </div>

        <div class="summary-grid">
          <div class="summary-stat">
            <span class="summary-label">Total</span>
            <strong>{{ complaints.length }}</strong>
          </div>

          <div class="summary-stat">
            <span class="summary-label">Open</span>
            <strong>{{ openCount }}</strong>
          </div>

          <div class="summary-stat">
            <span class="summary-label">Resolved</span>
            <strong>{{ resolvedCount }}</strong>
          </div>

          <div class="summary-stat">
            <span class="summary-label">Unassigned</span>
            <strong>{{ unassignedCount }}</strong>
          </div>

          <div class="summary-stat staff-stat">
            <span class="summary-label">Staff</span>
            <strong>{{ officers.length }}</strong>
          </div>
        </div>
      </div>
    </section>

    <!-- ERRORS -->
    <div v-if="loadError || actionError" class="dashboard-alerts">
      <p v-if="loadError" class="error-text">
        {{ loadError }}
      </p>

      <p v-if="actionError" class="error-text">
        {{ actionError }}
      </p>
    </div>

    <!-- MAIN CONTENT -->
    <section class="complaints-card card">

      <!-- CARD HEADER -->
      <div class="card-heading">
        <div>
          <div class="card-title-row">
            <h2>Complaint Management</h2>
            <span class="complaint-count">{{ filtered.length }}</span>
          </div>

          <p>
            Review, filter and take action on incoming complaints.
          </p>
        </div>

        <div class="card-heading-meta">
          <span v-if="filtered.length > 0">
            Showing
            <strong>
              {{ (currentPage - 1) * PAGE_SIZE + 1 }} - {{
                Math.min(currentPage * PAGE_SIZE, filtered.length)
              }}
            </strong>
            of
            <strong>{{ filtered.length }}</strong>
          </span>
        </div>
      </div>

      <!-- FILTER TOOLBAR -->
      <div class="filter-toolbar">

        <div class="filter-group">
          <label>Status</label>

          <div class="select-wrap">
            <select v-model="statusFilter">
              <option
                v-for="s in STATUSES"
                :key="s"
                :value="s"
              >
                {{ s }}
              </option>
            </select>

            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M6 9l6 6 6-6"></path>
            </svg>
          </div>
        </div>

        <div class="filter-group">
          <label>Category</label>

          <div class="select-wrap">
            <select v-model="categoryFilter">
              <option
                v-for="c in categories"
                :key="c"
                :value="c"
              >
                {{ c }}
              </option>
            </select>

            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M6 9l6 6 6-6"></path>
            </svg>
          </div>
        </div>

        <div class="filter-group">
          <label>Area</label>

          <div class="input-wrap">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0z"></path>
              <circle cx="12" cy="10" r="2.5"></circle>
            </svg>

            <input
              v-model="areaFilter"
              type="text"
              placeholder="e.g. Andheri"
            />
          </div>
        </div>

        <div class="filter-group">
          <label>Date Filed</label>

          <div class="input-wrap">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="3" y="4" width="18" height="18" rx="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>

            <input
              v-model="dateFilter"
              type="date"
            />
          </div>
        </div>

        <div class="filter-actions">
          <button
            class="btn secondary"
            @click="resetFilters"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M3 12a9 9 0 0 0 15.3 6.4"></path>
              <path d="M3 12V6h6"></path>
              <path d="M21 12a9 9 0 0 0-15.3-6.4"></path>
              <path d="M21 12v6h-6"></path>
            </svg>
            Reset
          </button>

          <button
            class="btn export-btn"
            :disabled="exporting"
            @click="exportCsv"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M12 3v12"></path>
              <path d="M7 10l5 5 5-5"></path>
              <path d="M5 21h14"></path>
            </svg>

            {{ exporting ? 'Exporting...' : 'Export CSV' }}
          </button>
        </div>
      </div>

      <p
        v-if="exportError"
        class="error-text export-error"
      >
        {{ exportError }}
      </p>

      <!-- EMPTY STATE -->
      <div
        v-if="filtered.length === 0"
        class="empty-state"
      >
        <div class="empty-icon">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
          >
            <circle cx="11" cy="11" r="7"></circle>
            <path d="M20 20l-4-4"></path>
          </svg>
        </div>

        <h3>No complaints found</h3>

        <p>
          Try adjusting your filters or search criteria.
        </p>

        <button
          class="btn secondary"
          @click="resetFilters"
        >
          Clear all filters
        </button>
      </div>

      <template v-else>

        <!-- TABLE -->
        <div class="table-wrap">
          <table class="data-table">

            <thead>
              <tr>
                <th class="priority-column">Priority</th>
                <th>Category</th>
                <th>Location</th>
                <th>Status</th>
                <th>Assigned Officer</th>
                <th>Filed</th>
                <th class="actions-column">Actions</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="c in paged"
                :key="c.id"
                class="complaint-row"
              >

                <!-- PRIORITY -->
                <td>
                  <div class="priority-cell">
                    <span
                      class="cc-priority"
                      :class="{
                        'priority-high': c.priorityScore >= 70,
                        'priority-medium':
                          c.priorityScore >= 40 &&
                          c.priorityScore < 70,
                        'priority-low': c.priorityScore < 40
                      }"
                    >
                      {{ c.priorityScore }}
                    </span>

                    <span class="priority-text">
                      {{
                        c.priorityScore >= 70
                          ? 'High'
                          : c.priorityScore >= 40
                            ? 'Medium'
                            : 'Low'
                      }}
                    </span>
                  </div>
                </td>

                <!-- CATEGORY -->
                <td>
                  <div class="category-cell">
                    <span>{{ c.category }}</span>
                  </div>
                </td>

                <!-- LOCATION -->
                <td>
                  <div
                    class="location-cell"
                    :title="c.location"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                    >
                      <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0z"></path>
                      <circle cx="12" cy="10" r="2.5"></circle>
                    </svg>

                    <span>{{ c.location }}</span>
                  </div>
                </td>

                <!-- STATUS -->
                <td>
                  <StatusBadge :value="c.status" />
                </td>

                <!-- ASSIGNED -->
                <td>
                  <div
                    class="officer-cell"
                    :class="{ unassigned: !c.assignedTo }"
                  >
                    <span class="officer-avatar">
                      {{
                        c.assignedTo
                          ? officerName(c.assignedTo).charAt(0).toUpperCase()
                          : '?'
                      }}
                    </span>

                    <span>
                      {{ officerName(c.assignedTo) }}
                    </span>
                  </div>
                </td>

                <!-- DATE -->
                <td>
                  <span class="date-cell">
                    {{ new Date(c.createdAt).toLocaleDateString() }}
                  </span>
                </td>

                <!-- ACTIONS -->
                <td>
                  <div class="row-actions">

                    <button
                      v-if="c.status === 'submitted'"
                      class="action-btn approve"
                      title="Approve complaint"
                      @click="doApprove(c.id)"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path d="M20 6L9 17l-5-5"></path>
                      </svg>
                      Approve
                    </button>

                    <button
                      v-if="c.status === 'submitted'"
                      class="action-btn reject"
                      title="Reject complaint"
                      @click="doReject(c.id)"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <path d="M18 6L6 18"></path>
                        <path d="M6 6l12 12"></path>
                      </svg>
                      Reject
                    </button>

                    <button
                      v-if="canAssign(c.status)"
                      class="action-btn assign"
                      :title="c.assignedTo ? 'Reassign officer' : 'Assign officer'"
                      @click="router.push(`/admin/assign/${c.id}`)"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                      >
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M3 21v-2a6 6 0 0 1 12 0v2"></path>
                        <path d="M19 8v6"></path>
                        <path d="M16 11h6"></path>
                      </svg>

                      {{ c.assignedTo ? 'Reassign' : 'Assign' }}
                    </button>

                  </div>
                </td>

              </tr>
            </tbody>

          </table>
        </div>

        <!-- PAGINATION -->
        <div
          v-if="totalPages > 1"
          class="pagination"
        >
          <button
            class="pagination-btn"
            :disabled="currentPage === 1"
            @click="currentPage -= 1"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M15 18l-6-6 6-6"></path>
            </svg>
            Previous
          </button>

          <div class="pagination-center">
            <span class="pagination-page">
              Page {{ currentPage }} of {{ totalPages }}
            </span>

            <span class="pagination-divider"></span>

            <span class="pagination-total">
              {{ filtered.length }} complaints
            </span>
          </div>

          <button
            class="pagination-btn"
            :disabled="currentPage === totalPages"
            @click="currentPage += 1"
          >
            Next
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M9 18l6-6-6-6"></path>
            </svg>
          </button>
        </div>

      </template>
    </section>
  </div>
</template>

<style scoped>
/* =========================================================
   DASHBOARD LAYOUT
   ========================================================= */

.admin-dashboard {
  padding-bottom: 40px;
}

/* =========================================================
   HERO
   ========================================================= */

.ops-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 390px;
  gap: 28px;
  margin-bottom: 24px;
}

.ops-hero-intro {
  min-width: 0;
  padding: 42px 42px 38px 48px;
}

.hero-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .12em;
  color: var(--text-dim);
}

.hero-kicker-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: .75;
}

.ops-hero-title {
  font-size: clamp(38px, 3.5vw, 52px);
  line-height: 1.1;
  letter-spacing: -.035em;
  font-weight: 750;
}

.ops-hero-sub {
  max-width: 620px;
  margin: 12px 0 22px;
  color: var(--text-dim);
  font-size: 15px;
  line-height: 1.6;
}

/* SEARCH */

.ops-search {
  width: min(680px, 100%);
  height: 48px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 15px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text-dim);
  box-shadow: 0 3px 14px rgba(0, 0, 0, .035);
  transition: border-color .18s ease, box-shadow .18s ease;
}

.ops-search:focus-within {
  border-color: var(--accent, currentColor);
  box-shadow: 0 0 0 3px rgba(0, 0, 0, .035);
}

.ops-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font-size: 15px;
}

.ops-search input::placeholder {
  color: var(--text-dim);
  opacity: .75;
}

.search-result-hint {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--surface-alt, rgba(0, 0, 0, .04));
  font-size: 13px;
  color: var(--text-dim);
}

/* =========================================================
   LIVE SNAPSHOT
   ========================================================= */

.ops-summary {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: 0 5px 24px rgba(0, 0, 0, .045);
}

.summary-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 17px;
}

.ops-summary-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.summary-subtitle {
  display: block;
  margin-top: 3px;
  font-size: 13px;
  color: var(--text-dim);
}

.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  color: var(--text-dim);
}

.live-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.summary-stat {
  min-width: 0;
  padding: 12px;
  border-radius: 10px;
  background: var(--surface-alt, rgba(0, 0, 0, .035));
}

.summary-label {
  display: block;
  margin-bottom: 5px;
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .06em;
}

.summary-stat strong {
  font-size: 23px;
  line-height: 1;
  letter-spacing: -.02em;
}

.staff-stat {
  grid-column: span 2;
}

/* =========================================================
   ALERTS
   ========================================================= */

.dashboard-alerts {
  margin-bottom: 16px;
}

.error-text {
  margin: 8px 0;
}

/* =========================================================
   MAIN CARD
   ========================================================= */

.complaints-card {
  overflow: hidden;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 22px 18px;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 9px;
}

.card-title-row h2 {
  margin: 0;
  font-size: 19px;
  letter-spacing: -.015em;
}

.card-heading p {
  margin: 5px 0 0;
  color: var(--text-dim);
  font-size: 15px;
}

.complaint-count {
  min-width: 24px;
  height: 21px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--surface-alt, rgba(0, 0, 0, .05));
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 700;
}

.card-heading-meta {
  padding-top: 2px;
  color: var(--text-dim);
  font-size: 14px;
  white-space: nowrap;
}

.card-heading-meta strong {
  color: var(--text);
}

/* =========================================================
   FILTERS
   ========================================================= */

.filter-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 16px 22px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: var(--surface-alt, rgba(0, 0, 0, .018));
}

.filter-group {
  min-width: 135px;
  flex: 1;
}

.filter-group label {
  display: block;
  margin: 0 0 6px 1px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: .055em;
}

.filter-group select,
.filter-group input {
  width: 100%;
  height: 37px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: border-color .15s ease, box-shadow .15s ease;
}

.filter-group select:focus,
.filter-group input:focus {
  border-color: var(--accent, currentColor);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, .025);
}

.select-wrap,
.input-wrap {
  position: relative;
}

.select-wrap select {
  appearance: none;
  padding-right: 32px;
}

.select-wrap svg {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--text-dim);
}

.input-wrap svg {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--text-dim);
}

.input-wrap input {
  padding-left: 33px;
}

.filter-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.filter-actions .btn {
  height: 37px;
  white-space: nowrap;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.export-error {
  margin: 12px 22px;
}

/* =========================================================
   TABLE
   ========================================================= */

.table-wrap {
  width: 100%;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  min-width: 1040px;
  border-collapse: collapse;
}

.data-table thead {
  background: var(--surface-alt, rgba(0, 0, 0, .018));
}

.data-table th {
  height: 42px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 700;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: .055em;
  white-space: nowrap;
}

.data-table th:first-child,
.data-table td:first-child {
  padding-left: 22px;
}

.data-table th:last-child,
.data-table td:last-child {
  padding-right: 22px;
}

.data-table td {
  height: 70px;
  padding: 12px 15px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  font-size: 15px;
  vertical-align: middle;
}

.complaint-row {
  transition: background .14s ease;
}

.complaint-row:hover {
  background: var(--surface-alt, rgba(0, 0, 0, .025));
}

.complaint-row:nth-child(even) {
  background: #fafbfa;
}

.complaint-row:last-child td {
  border-bottom: 0;
}

/* test */


/* =========================================================
   PRIORITY
   ========================================================= */

.priority-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cc-priority {
  min-width: 30px;
  height: 27px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  font-size: 14px;
  font-weight: 800;
}

.priority-high {
  background: rgba(192, 57, 43, .11);
  color: var(--danger, #c0392b);
}

.priority-medium {
  background: rgba(211, 150, 35, .11);
  color: var(--warning, #a66a00);
}

.priority-low {
  background: rgba(39, 125, 85, .10);
  color: var(--success, #277d55);
}

.priority-text {
  color: var(--text-dim);
  font-size: 13px;
}

/* =========================================================
   CATEGORY / LOCATION
   ========================================================= */

.category-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}

.location-cell {
  display: flex;
  align-items: center;
  gap: 7px;
  max-width: 230px;
  color: var(--text-dim);
}

.location-cell svg {
  flex-shrink: 0;
}

.location-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* =========================================================
   OFFICER
   ========================================================= */

.officer-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.officer-avatar {
  width: 27px;
  height: 27px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface-alt, rgba(0, 0, 0, .035));
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 700;
}

.officer-cell.unassigned {
  color: var(--text-dim);
  font-style: italic;
}

.date-cell {
  color: var(--text-dim);
  white-space: nowrap;
}

/* =========================================================
   ACTIONS
   ========================================================= */

.actions-column {
  text-align: right !important;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
  white-space: nowrap;
}

.action-btn {
  height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 9px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--surface);
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background .15s ease,
    border-color .15s ease,
    color .15s ease,
    transform .12s ease;
}

.action-btn:hover {
  transform: translateY(-1px);
}

.action-btn.approve:hover {
  color: var(--success, #277d55);
  border-color: rgba(39, 125, 85, .35);
  background: rgba(39, 125, 85, .06);
}

.action-btn.reject:hover {
  color: var(--danger);
  border-color: rgba(192, 57, 43, .35);
  background: rgba(192, 57, 43, .06);
}

.action-btn.assign:hover {
  color: var(--text);
  border-color: var(--text-dim);
  background: var(--surface-alt, rgba(0, 0, 0, .04));
}

/* =========================================================
   EMPTY STATE
   ========================================================= */

.empty-state {
  min-height: 290px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  width: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  border: 1px solid var(--border);
  border-radius: 15px;
  background: var(--surface-alt, rgba(0, 0, 0, .03));
  color: var(--text-dim);
}

.empty-state h3 {
  margin: 0;
  font-size: 15px;
}

.empty-state p {
  margin: 6px 0 16px;
  color: var(--text-dim);
  font-size: 12px;
}

/* =========================================================
   PAGINATION
   ========================================================= */

.pagination {
  min-height: 67px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 22px;
  border-top: 1px solid var(--border);
}

.pagination-btn {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--surface-alt, rgba(0, 0, 0, .035));
  border-color: var(--text-dim);
}

.pagination-btn:disabled {
  cursor: not-allowed;
  opacity: .4;
}

.pagination-center {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-dim);
  font-size: 11px;
}

.pagination-page {
  color: var(--text);
  font-weight: 650;
}

.pagination-divider {
  width: 1px;
  height: 13px;
  background: var(--border);
}

.pagination-total {
  color: var(--text-dim);
}

/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 1100px) {
  .ops-hero {
    grid-template-columns: 1fr;
  }

  .ops-summary {
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: repeat(5, 1fr);
  }

  .staff-stat {
    grid-column: auto;
  }

  .filter-toolbar {
    flex-wrap: wrap;
  }

  .filter-group {
    min-width: 180px;
  }

  .filter-actions {
    margin-left: auto;
  }
}

@media (max-width: 720px) {
  .ops-hero {
    gap: 18px;
  }

  .ops-hero-title {
    font-size: 28px;
  }

  .ops-hero-sub {
    font-size: 13px;
  }

  .ops-search {
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .staff-stat {
    grid-column: span 2;
  }

  .card-heading {
    flex-direction: column;
    gap: 10px;
  }

  .card-heading-meta {
    white-space: normal;
  }

  .filter-toolbar {
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: stretch;
  }

  .filter-group {
    min-width: 0;
  }

  .filter-actions {
    grid-column: span 2;
    margin-left: 0;
  }

  .filter-actions .btn {
    flex: 1;
  }

  .pagination {
    padding: 12px 16px;
  }

  .pagination-center {
    flex-direction: column;
    gap: 3px;
  }

  .pagination-divider {
    display: none;
  }
}

@media (max-width: 480px) {
  .filter-toolbar {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    grid-column: auto;
  }

  .summary-grid {
    gap: 6px;
  }

  .summary-stat {
    padding: 10px;
  }

  .summary-stat strong {
    font-size: 18px;
  }

  .pagination-total {
    display: none;
  }
}
</style>