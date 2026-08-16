<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { assignComplaint, getComplaint, listAttachments, listOfficers } from '../api/complaintApi'
import { API_BASE_URL } from '../api/httpClient'
import { categoryLabel } from '../constants/categories'
import { complaintReference } from '../constants/complaintNumber'
import StatusBadge from '../components/StatusBadge.vue'

// image_url comes back as a path relative to the backend's own
// origin (local filesystem storage in dev, see the backend's
// storage.py), not the frontend's, so it needs the API's origin
// prepended before it's usable in an <img> src.
function attachmentUrl(imageUrl) {
  return `${API_BASE_URL}${imageUrl}`
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const complaint = ref(null)
const officers = ref([])
const attachments = ref([])
const selectedStaff = ref('')
const loading = ref(true)
const loadError = ref('')
const assignError = ref('')
const saving = ref(false)

const currentOfficer = computed(() => {
  return officers.value.find(
    officer => officer.id === complaint.value?.assigned_to
  )
})

const hasAssignment = computed(() => {
  return Boolean(complaint.value?.assigned_to)
})

// Only offer staff from the department this complaint was routed to,
// so an admin assigning a drainage complaint doesn't have to pick the
// right person out of every department's officers. Falls back to
// showing everyone if the complaint somehow has no department (should
// be rare, routing always falls back to General Administration on
// its own failures, see routing_service.route_complaint).
//
// Always keeps the currently-assigned officer in the list even if
// their department no longer matches (they could have been moved to
// a different department after this complaint was assigned) -
// otherwise the dropdown would silently show no selection for them
// while selectedStaff still held their id underneath, so "Confirm
// Assignment" would resubmit an assignment the admin can't actually
// see selected.
const eligibleOfficers = computed(() => {
  if (!complaint.value?.department) return officers.value
  return officers.value.filter(
    o => o.department === complaint.value.department || o.id === complaint.value.assigned_to
  )
})

onMounted(async () => {
  try {
    const [detail, officersData, attachmentsData] = await Promise.all([
      getComplaint({
        id: route.params.id,
        accessToken: auth.accessToken
      }),
      listOfficers({
        accessToken: auth.accessToken
      }),
      listAttachments({
        id: route.params.id,
        accessToken: auth.accessToken
      })
    ])

    complaint.value = detail
    officers.value = officersData.officers
    attachments.value = attachmentsData.attachments
    selectedStaff.value = detail.assigned_to || ''
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }

    loadError.value = e.message || 'Unable to load complaint.'
  } finally {
    loading.value = false
  }
})

async function confirmAssignment() {
  if (!selectedStaff.value) return

  saving.value = true
  assignError.value = ''

  try {
    await assignComplaint({
      id: route.params.id,
      assignedTo: selectedStaff.value,
      accessToken: auth.accessToken
    })

    router.push('/admin')
  } catch (e) {
    assignError.value = e.message || 'Unable to assign complaint.'
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/admin')
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="detail-page">
    <div class="loading-card">
      <div class="loading-spinner"></div>
      <p>Loading complaint details...</p>
    </div>
  </div>

  <!-- Error -->
  <div v-else-if="loadError" class="detail-page">
    <div class="error-card">
      <div class="error-icon">!</div>
      <div>
        <h3>Unable to load complaint</h3>
        <p>{{ loadError }}</p>
      </div>
      <button class="btn secondary" @click="goBack">
        Back to complaints
      </button>
    </div>
  </div>

  <!-- Main -->
  <div v-else-if="complaint" class="detail-page">

    <!-- Top navigation -->
    <div class="detail-topbar">
      <button class="back-button" @click="goBack">
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
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>

        Back to complaints
      </button>

      <span class="complaint-reference">
        Complaint {{ complaintReference(complaint.complaint_number) }}
      </span>
    </div>

    <!-- Complaint hero -->
    <section class="complaint-hero">

      <div class="hero-main">
        <div class="category-icon">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M3 17l6-6 4 4 8-8"></path>
            <path d="M14 7h7v7"></path>
          </svg>
        </div>

        <div>
          <p class="hero-eyebrow">Civic Complaint</p>
          <h1>{{ categoryLabel(complaint.category) }}</h1>
          <p class="hero-location">
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 1 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>

            {{ complaint.location_text || 'Location not provided' }}
          </p>
        </div>
      </div>

      <div class="hero-status">
        <span class="status-label">Current status</span>
        <StatusBadge :value="complaint.status" />
      </div>

    </section>

    <!-- Main grid -->
    <div class="detail-grid">

      <!-- LEFT -->
      <main class="detail-main">

        <!-- Complaint information -->
        <section class="detail-card">

          <div class="section-heading">
            <div>
              <p class="section-kicker">Complaint</p>
              <h2>Complaint details</h2>
            </div>
          </div>

          <div class="description-box">
            <p>{{ complaint.description }}</p>
          </div>

          <div class="info-grid">

            <div class="info-item">
              <span class="info-label">Category</span>
              <span class="info-value">
                {{ categoryLabel(complaint.category) }}
              </span>
            </div>

            <div class="info-item">
              <span class="info-label">Status</span>
              <span class="info-value status-value">
                <StatusBadge :value="complaint.status" />
              </span>
            </div>

            <div class="info-item full">
              <span class="info-label">Location</span>
              <span class="info-value">
                {{ complaint.location_text || 'Not provided' }}
              </span>
            </div>

          </div>

        </section>

        <!-- Attachments -->
        <section v-if="attachments.length > 0" class="detail-card">

          <div class="section-heading">
            <div>
              <p class="section-kicker">Evidence</p>
              <h2>Attachments</h2>
            </div>
          </div>

          <div class="attachment-grid">
            <a
              v-for="a in attachments"
              :key="a.id"
              :href="attachmentUrl(a.image_url)"
              target="_blank"
              rel="noopener"
              class="attachment-thumb"
            >
              <img :src="attachmentUrl(a.image_url)" alt="Attachment" />
              <span v-if="a.purpose === 'resolution_proof'" class="attachment-badge">Resolution</span>
            </a>
          </div>

        </section>

        <!-- Assignment -->
        <section class="detail-card assignment-card">

          <div class="section-heading">
            <div>
              <p class="section-kicker">Operations</p>
              <h2>Staff assignment</h2>
              <p class="section-description">
                Assign this complaint to the staff member responsible for
                resolving it.
              </p>
            </div>

            <div
              v-if="hasAssignment"
              class="assignment-status"
            >
              <span class="assignment-dot"></span>
              Assigned
            </div>
          </div>

          <!-- Current assignment -->
          <div
            v-if="hasAssignment && currentOfficer"
            class="current-assignee"
          >
            <div class="assignee-avatar">
              {{ currentOfficer.name?.charAt(0)?.toUpperCase() }}
            </div>

            <div class="assignee-info">
              <span class="assignee-label">Currently assigned to</span>
              <strong>{{ currentOfficer.name }}</strong>
            </div>

            <span class="assignee-check">
              ✓
            </span>
          </div>

          <p v-if="assignError" class="assignment-error">
            {{ assignError }}
          </p>

          <!-- No staff at all -->
          <div
            v-if="officers.length === 0"
            class="no-staff"
          >
            <div class="no-staff-icon">!</div>

            <div>
              <strong>No staff accounts available</strong>
              <p>
                Create a staff account before assigning this complaint.
              </p>
              <router-link to="/admin/staff">
                Manage staff →
              </router-link>
            </div>
          </div>

          <!-- Staff exist, but none in this complaint's department -->
          <div
            v-else-if="eligibleOfficers.length === 0"
            class="no-staff"
          >
            <div class="no-staff-icon">!</div>

            <div>
              <strong>No staff in {{ complaint.department }} yet</strong>
              <p>
                Add an officer to this department before assigning it.
              </p>
              <router-link :to="`/admin/staff?department=${encodeURIComponent(complaint.department)}`">
                Add staff to {{ complaint.department }} →
              </router-link>
            </div>
          </div>

          <!-- Staff selector -->
          <template v-else>

            <div class="assignment-form">

              <div class="field">
                <label for="staff-select">
                  Assign to staff member
                  <span v-if="complaint.department" class="field-hint">
                    ({{ complaint.department }})
                  </span>
                </label>

                <select
                  id="staff-select"
                  v-model="selectedStaff"
                >
                  <option value="" disabled>
                    Select a staff member
                  </option>

                  <option
                    v-for="o in eligibleOfficers"
                    :key="o.id"
                    :value="o.id"
                  >
                    {{ o.name }}
                  </option>
                </select>
              </div>

              <button
                class="assign-button"
                :disabled="saving || !selectedStaff"
                @click="confirmAssignment"
              >
                <svg
                  v-if="!saving"
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M20 6L9 17l-5-5"></path>
                </svg>

                <span v-if="saving" class="button-spinner"></span>

                {{ saving ? 'Assigning...' : 'Confirm Assignment' }}
              </button>

            </div>

          </template>

        </section>

      </main>

      <!-- RIGHT -->
      <aside class="detail-sidebar">

        <div class="side-card">

          <div class="side-card-heading">
            <span class="side-icon">
              <svg
                width="17"
                height="17"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="9"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </span>

            <span>Quick information</span>
          </div>

          <div class="side-stat">
            <span>Complaint ID</span>
            <strong>{{ complaintReference(complaint.complaint_number) }}</strong>
          </div>

          <div class="side-stat">
            <span>Category</span>
            <strong>{{ categoryLabel(complaint.category) }}</strong>
          </div>

          <div class="side-stat">
            <span>Status</span>
            <StatusBadge :value="complaint.status" />
          </div>

          <div class="side-stat">
            <span>Assignment</span>
            <strong>
              {{ hasAssignment ? 'Assigned' : 'Unassigned' }}
            </strong>
          </div>

        </div>

        

      </aside>

    </div>

  </div>
</template>

<style scoped>
/* =========================
   PAGE
========================= */

.detail-page {
  max-width: 1380px;
  margin: 0 auto;
  padding: 26px 28px 100px;
}

/* =========================
   TOP BAR
========================= */

.detail-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--ink);
  padding: 9px 14px;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: .2s ease;
}

.back-button:hover {
  background: var(--panel-alt);
  border-color: var(--accent);
  color: var(--accent-dark);
}

.complaint-reference {
  color: var(--text-dim);
  font-size: 12px;
  font-weight: 600;
}

/* =========================
   HERO
========================= */

.complaint-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;

  padding: 26px 28px;

  background:
    linear-gradient(
      135deg,
      var(--ink) 0%,
      var(--ink-soft) 100%
    );

  color: #fff;
  border-radius: var(--radius-lg);
  margin-bottom: 20px;

  box-shadow: 0 10px 28px rgba(22, 48, 31, .12);
}

.hero-main {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.category-icon {
  width: 52px;
  height: 52px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 14px;
}

.hero-eyebrow {
  margin: 0 0 5px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: rgba(255,255,255,.55);
}

.complaint-hero h1 {
  margin: 0;
  font-size: 27px;
  font-weight: 800;
  letter-spacing: -.02em;
}

.hero-location {
  display: flex;
  align-items: center;
  gap: 6px;

  margin: 7px 0 0;

  font-size: 13px;
  color: rgba(255,255,255,.72);
}

.hero-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 7px;
}

.status-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: rgba(255,255,255,.5);
  font-weight: 700;
}

/* =========================
   GRID
========================= */

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
  align-items: start;
}

.detail-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* =========================
   CARDS
========================= */

.detail-card,
.side-card,
.workflow-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: 0 3px 12px rgba(22,48,31,.045);
}

.detail-card {
  padding: 24px;
}

.attachment-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.attachment-thumb {
  position: relative;
  display: block;
  width: 96px;
  height: 96px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.attachment-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.attachment-badge {
  position: absolute;
  left: 4px;
  bottom: 4px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(22, 48, 31, .78);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.section-kicker {
  margin: 0 0 4px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .09em;
  font-weight: 800;
  color: var(--accent);
}

.section-heading h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  color: var(--ink);
}

.section-description {
  margin: 5px 0 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.5;
}

/* =========================
   DESCRIPTION
========================= */

.description-box {
  background: var(--panel-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 17px 18px;
  margin-bottom: 20px;
}

.description-box p {
  margin: 0;
  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
}

/* =========================
   INFO
========================= */

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-top: 1px solid var(--border);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 15px 14px 4px 0;
}

.info-item:nth-child(2) {
  padding-left: 14px;
  border-left: 1px solid var(--border);
}

.info-item.full {
  grid-column: 1 / -1;
  padding-bottom: 0;
}

.info-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--text-dim);
  font-weight: 700;
}

.info-value {
  font-size: 14px;
  font-weight: 650;
  color: var(--ink);
}

.status-value {
  display: flex;
}

/* =========================
   ASSIGNMENT
========================= */

.assignment-card {
  border-top: 3px solid var(--accent);
}

.assignment-status {
  display: flex;
  align-items: center;
  gap: 6px;

  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-glow);
  padding: 6px 10px;
  border-radius: 999px;
}

.assignment-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

.current-assignee {
  display: flex;
  align-items: center;
  gap: 12px;

  padding: 13px;
  margin-bottom: 18px;

  border: 1px solid var(--border);
  background: var(--panel-alt);
  border-radius: var(--radius);
}

.assignee-avatar {
  width: 38px;
  height: 38px;
  border-radius: 10px;

  display: flex;
  align-items: center;
  justify-content: center;

  background: var(--accent);
  color: #fff;
  font-weight: 800;
}

.assignee-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.assignee-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--text-dim);
  font-weight: 700;
}

.assignee-info strong {
  font-size: 14px;
  color: var(--ink);
}

.assignee-check {
  width: 25px;
  height: 25px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;

  background: var(--accent-glow);
  color: var(--accent);
  font-weight: 800;
}

.assignment-form {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.assignment-form .field {
  flex: 1;
  margin: 0;
}

.field label {
  display: block;
  margin-bottom: 7px;

  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--text-dim);
}

.field-hint {
  text-transform: none;
  letter-spacing: normal;
  font-weight: 600;
  color: var(--accent);
}

.field select {
  height: 45px;
}

.assign-button {
  height: 45px;

  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;

  padding: 0 18px;

  border: none;
  border-radius: var(--radius);

  background: var(--accent);
  color: #fff;

  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .03em;

  cursor: pointer;
  white-space: nowrap;

  transition: .2s ease;
}

.assign-button:hover:not(:disabled) {
  background: var(--accent-dark);
  transform: translateY(-1px);
  box-shadow: 0 5px 14px var(--accent-glow);
}

.assign-button:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.assignment-error {
  margin: 0 0 15px;
  padding: 10px 12px;

  border-radius: var(--radius);
  background: rgba(192,57,43,.08);
  color: var(--danger);

  font-size: 13px;
}

/* =========================
   NO STAFF
========================= */

.no-staff {
  display: flex;
  align-items: center;
  gap: 12px;

  padding: 15px;

  background: rgba(184,134,11,.08);
  border: 1px solid rgba(184,134,11,.25);
  border-radius: var(--radius);
}

.no-staff-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;
  background: rgba(184,134,11,.15);
  color: var(--warn);
  font-weight: 800;
}

.no-staff strong {
  display: block;
  font-size: 13px;
}

.no-staff p {
  margin: 3px 0;
  color: var(--text-dim);
  font-size: 12px;
}

.no-staff a {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

/* =========================
   SIDEBAR
========================= */

.detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.side-card {
  padding: 19px;
}

.side-card-heading {
  display: flex;
  align-items: center;
  gap: 9px;

  padding-bottom: 15px;
  margin-bottom: 4px;

  border-bottom: 1px solid var(--border);

  font-size: 12px;
  font-weight: 800;
  color: var(--ink);
  text-transform: uppercase;
  letter-spacing: .05em;
}

.side-icon {
  width: 28px;
  height: 28px;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 8px;
  background: var(--accent-glow);
  color: var(--accent);
}

.side-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;

  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}

.side-stat:last-child {
  border-bottom: none;
  padding-bottom: 3px;
}

.side-stat span {
  font-size: 12px;
  color: var(--text-dim);
}

.side-stat strong {
  max-width: 150px;
  text-align: right;
  font-size: 12px;
  color: var(--ink);
  text-transform: capitalize;
}

.workflow-card {
  display: flex;
  gap: 11px;
  padding: 17px;

  background: var(--panel-alt);
}

.workflow-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 9px;

  background: var(--accent-glow);
  color: var(--accent);
  font-weight: 800;
}

.workflow-card h3 {
  margin: 2px 0 5px;
  font-size: 13px;
  color: var(--ink);
}

.workflow-card p {
  margin: 0;
  color: var(--text-dim);
  font-size: 12px;
  line-height: 1.55;
}

/* =========================
   LOADING / ERROR
========================= */

.loading-card,
.error-card {
  max-width: 600px;
  margin: 80px auto;
  padding: 30px;

  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);

  display: flex;
  align-items: center;
  gap: 15px;
}

.loading-card p {
  margin: 0;
  color: var(--text-dim);
}

.loading-spinner,
.button-spinner {
  border: 2px solid rgba(47,143,91,.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

.loading-spinner {
  width: 24px;
  height: 24px;
}

.button-spinner {
  width: 14px;
  height: 14px;
  border-color: rgba(255,255,255,.3);
  border-top-color: #fff;
}

.error-card {
  align-items: flex-start;
}

.error-icon {
  width: 38px;
  height: 38px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;
  background: rgba(192,57,43,.1);
  color: var(--danger);
  font-weight: 800;
}

.error-card h3 {
  margin: 0 0 4px;
  font-size: 16px;
}

.error-card p {
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
}

.error-card .btn {
  margin-left: auto;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* =========================
   RESPONSIVE
========================= */

@media (max-width: 950px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .detail-sidebar {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 680px) {
  .detail-page {
    padding: 18px 14px 80px;
  }

  .detail-topbar {
    align-items: flex-start;
  }

  .complaint-reference {
    display: none;
  }

  .complaint-hero {
    align-items: flex-start;
    flex-direction: column;
    padding: 22px;
  }

  .hero-status {
    align-items: flex-start;
  }

  .detail-card {
    padding: 18px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-item:nth-child(2) {
    padding-left: 0;
    border-left: none;
  }

  .assignment-form {
    flex-direction: column;
    align-items: stretch;
  }

  .assign-button {
    width: 100%;
  }

  .detail-sidebar {
    display: flex;
  }

  .error-card {
    flex-direction: column;
  }

  .error-card .btn {
    margin-left: 0;
  }
}
</style>