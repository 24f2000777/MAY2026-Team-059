<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getComplaint, getComplaintHistory, resolveComplaint, startComplaint } from '../api/complaintApi'
import { categoryLabel } from '../constants/categories'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const complaint = ref(null)
const history = ref([])
const notes = ref('')
const loading = ref(true)
const loadError = ref('')
const actionError = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [detail, historyData] = await Promise.all([
      getComplaint({ id: route.params.id, accessToken: auth.accessToken }),
      getComplaintHistory({ id: route.params.id, accessToken: auth.accessToken })
    ])
    complaint.value = detail
    history.value = historyData.history
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

async function doStart() {
  saving.value = true
  actionError.value = ''
  try {
    await startComplaint({ id: route.params.id, notes: notes.value || undefined, accessToken: auth.accessToken })
    notes.value = ''
    await load()
  } catch (e) {
    actionError.value = e.message
  } finally {
    saving.value = false
  }
}

async function doResolve() {
  saving.value = true
  actionError.value = ''
  try {
    await resolveComplaint({ id: route.params.id, notes: notes.value || undefined, accessToken: auth.accessToken })
    notes.value = ''
    await load()
  } catch (e) {
    actionError.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="page-state">
    <div class="state-card">
      <div class="loader"></div>
      <p>Loading complaint...</p>
    </div>
  </div>

  <!-- Error -->
  <div v-else-if="loadError" class="page-state">
    <div class="state-card error-state">
      <div class="state-icon">!</div>
      <h3>Unable to load complaint</h3>
      <p>{{ loadError }}</p>
      <button class="btn secondary" @click="load">Try Again</button>
    </div>
  </div>

  <!-- Complaint -->
  <div v-else-if="complaint" class="app-content complaint-page">

    <!-- Back -->
    <div class="top-bar">
      <button class="back-btn" @click="router.back()">
        <span>←</span>
        Back
      </button>
    </div>

    <!-- Main header -->
    <section class="complaint-hero">

      <div class="hero-main">
        <div class="category-icon">
          {{ categoryLabel(complaint.category).charAt(0) }}
        </div>

        <div class="hero-content">
          <div class="eyebrow">COMPLAINT #{{ complaint.id }}</div>

          <h1>{{ categoryLabel(complaint.category) }}</h1>

          <div class="location-row">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>

            <span>
              {{ complaint.location_text || 'No location recorded' }}
            </span>
          </div>
        </div>
      </div>

      <div class="hero-status">
        <StatusBadge :value="complaint.status" />
      </div>

    </section>


    <!-- Content grid -->
    <div class="complaint-grid">

      <!-- LEFT -->
      <main class="main-column">

        <!-- Description -->
        <section class="section-card">
          <div class="section-header">
            <div>
              <span class="section-kicker">CASE DETAILS</span>
              <h2>Complaint Description</h2>
            </div>
          </div>

          <div class="description-box">
            {{ complaint.description }}
          </div>
        </section>


        <!-- Action -->
        <section class="section-card action-card">

          <div class="section-header">
            <div>
              <span class="section-kicker">NEXT STEP</span>
              <h2>Update Complaint</h2>
            </div>

            <div
              class="action-status"
              :class="complaint.status"
            >
              <span class="status-dot"></span>
              {{ complaint.status.replaceAll('_', ' ') }}
            </div>
          </div>


          <div
            v-if="complaint.status === 'approved'"
            class="action-content"
          >
            <div class="action-message">
              <div class="action-icon">▶</div>

              <div>
                <h3>Ready to begin work</h3>
                <p>
                  Start working on this complaint to move it into
                  <strong>In Progress</strong>.
                </p>
              </div>
            </div>

            <div class="notes-field">
              <label for="start-notes">
                Work notes
                <span>Optional</span>
              </label>

              <textarea
                id="start-notes"
                v-model="notes"
                rows="3"
                placeholder="Add any notes about starting this complaint..."
              ></textarea>
            </div>

            <p v-if="actionError" class="action-error">
              {{ actionError }}
            </p>

            <button
              class="primary-action"
              :disabled="saving"
              @click="doStart"
            >
              <span v-if="!saving">Start Work</span>
              <span v-else>Saving...</span>

              <span v-if="!saving" class="action-arrow">→</span>
            </button>
          </div>


          <div
            v-else-if="complaint.status === 'in_progress'"
            class="action-content"
          >
            <div class="action-message resolve">
              <div class="action-icon">✓</div>

              <div>
                <h3>Work is in progress</h3>
                <p>
                  Once the issue has been addressed, mark this complaint
                  as <strong>Resolved</strong>.
                </p>
              </div>
            </div>

            <div class="notes-field">
              <label for="resolve-notes">
                Resolution notes
                <span>Optional</span>
              </label>

              <textarea
                id="resolve-notes"
                v-model="notes"
                rows="3"
                placeholder="Describe the work completed or resolution..."
              ></textarea>
            </div>

            <p v-if="actionError" class="action-error">
              {{ actionError }}
            </p>

            <button
              class="primary-action resolve-btn"
              :disabled="saving"
              @click="doResolve"
            >
              <span v-if="!saving">Mark as Resolved</span>
              <span v-else>Saving...</span>

              <span v-if="!saving" class="action-arrow">✓</span>
            </button>
          </div>


          <div v-else class="no-action">
            <div class="no-action-icon">✓</div>

            <div>
              <h3>No action required</h3>
              <p>
                This complaint is currently
                <strong>{{ complaint.status.replaceAll('_', ' ') }}</strong>
                and cannot be updated from this stage.
              </p>
            </div>
          </div>

        </section>


        <!-- History -->
        <section class="section-card history-card">

          <div class="section-header">
            <div>
              <span class="section-kicker">ACTIVITY</span>
              <h2>Status History</h2>
            </div>

            <span class="history-count">
              {{ history.length }}
              {{ history.length === 1 ? 'event' : 'events' }}
            </span>
          </div>


          <div v-if="history.length > 0" class="timeline">

            <div
              v-for="(h, index) in history"
              :key="h.id"
              class="timeline-item"
            >

              <div class="timeline-track">
                <div
                  class="timeline-dot"
                  :class="{
                    latest: index === 0
                  }"
                ></div>

                <div
                  v-if="index < history.length - 1"
                  class="timeline-line"
                ></div>
              </div>


              <div class="timeline-content">

                <div class="timeline-top">

                  <div class="transition">
                    <span v-if="h.old_status">
                      {{ h.old_status.replaceAll('_', ' ') }}
                    </span>

                    <span v-if="h.old_status" class="transition-arrow">
                      →
                    </span>

                    <strong>
                      {{ h.new_status.replaceAll('_', ' ') }}
                    </strong>
                  </div>

                  <time>
                    {{ new Date(h.created_at).toLocaleString() }}
                  </time>
                </div>


                <div class="changed-by">
                  <span class="person-avatar">
                    {{ (h.changed_by?.name || 'S').charAt(0).toUpperCase() }}
                  </span>

                  <span>
                    Changed by
                    <strong>
                      {{ h.changed_by?.name || 'System' }}
                    </strong>
                  </span>
                </div>

              </div>

            </div>

          </div>


          <div v-else class="empty-history">
            <div class="empty-history-icon">○</div>
            <h3>No status changes yet</h3>
            <p>
              Activity will appear here as the complaint moves through
              the workflow.
            </p>
          </div>

        </section>

      </main>


      <!-- RIGHT SIDEBAR -->
      <aside class="side-column">

        <!-- Current status -->
        <section class="info-card">

          <span class="section-kicker">CURRENT STATUS</span>

          <div class="status-display">
            <StatusBadge :value="complaint.status" />
          </div>

          <p class="status-description">
            <template v-if="complaint.status === 'approved'">
              This complaint has been approved and is waiting for a staff
              member to begin work.
            </template>

            <template v-else-if="complaint.status === 'in_progress'">
              A staff member is currently working on this complaint.
            </template>

            <template v-else-if="complaint.status === 'resolved'">
              The complaint has been marked as resolved.
            </template>

            <template v-else>
              The complaint is currently in the
              {{ complaint.status.replaceAll('_', ' ') }}
              stage.
            </template>
          </p>

        </section>


        <!-- Workflow -->
        <section class="info-card">

          <span class="section-kicker">WORKFLOW</span>

          <div class="workflow">

            <div
              class="workflow-step"
              :class="{
                active: ['approved', 'in_progress', 'resolved'].includes(complaint.status),
                current: complaint.status === 'approved'
              }"
            >
              <div class="workflow-marker">✓</div>
              <div>
                <strong>Approved</strong>
                <span>Complaint approved</span>
              </div>
            </div>


            <div
              class="workflow-step"
              :class="{
                active: ['in_progress', 'resolved'].includes(complaint.status),
                current: complaint.status === 'in_progress'
              }"
            >
              <div class="workflow-marker">
                {{ complaint.status === 'in_progress' ? '•' : '✓' }}
              </div>

              <div>
                <strong>In Progress</strong>
                <span>Staff working on issue</span>
              </div>
            </div>


            <div
              class="workflow-step"
              :class="{
                active: complaint.status === 'resolved',
                current: complaint.status === 'resolved'
              }"
            >
              <div class="workflow-marker">
                {{ complaint.status === 'resolved' ? '✓' : '3' }}
              </div>

              <div>
                <strong>Resolved</strong>
                <span>Issue addressed</span>
              </div>
            </div>

          </div>

        </section>


        <!-- Help -->
        <section class="help-card">

          <div class="help-icon">?</div>

          <div>
            <h3>Need assistance?</h3>
            <p>
              If this complaint requires escalation, contact your
              supervisor.
            </p>
          </div>

        </section>

      </aside>

    </div>

  </div>
</template>


<style scoped>

/* ================================
   PAGE
================================ */

.complaint-page {
  max-width: 1320px;
  margin: 0 auto;
  padding: 28px 32px 80px;
}


/* ================================
   TOP BAR
================================ */

.top-bar {
  margin-bottom: 18px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 15px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--panel);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: .18s ease;
}

.back-btn:hover {
  background: var(--panel-alt);
  border-color: var(--accent);
  color: var(--accent);
}

.back-btn span {
  font-size: 18px;
}


/* ================================
   HERO
================================ */

.complaint-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;

  padding: 26px 28px;

  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;

  box-shadow: 0 8px 25px rgba(30, 60, 40, .04);

  margin-bottom: 20px;
}

.hero-main {
  display: flex;
  align-items: center;
  gap: 17px;
  min-width: 0;
}

.category-icon {
  width: 54px;
  height: 54px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 14px;

  background: var(--accent-glow);
  color: var(--accent);

  font-size: 21px;
  font-weight: 800;
}

.hero-content {
  min-width: 0;
}

.eyebrow,
.section-kicker {
  display: block;

  font-size: 10px;
  font-weight: 800;
  letter-spacing: .09em;
  text-transform: uppercase;

  color: var(--text-dim);
}

.hero-content h1 {
  margin: 4px 0 7px;

  font-size: 27px;
  line-height: 1.15;
  font-weight: 750;
}

.location-row {
  display: flex;
  align-items: center;
  gap: 6px;

  color: var(--text-dim);
  font-size: 13px;
}

.location-row svg {
  color: var(--accent);
  flex-shrink: 0;
}

.hero-status {
  flex-shrink: 0;
}


/* ================================
   GRID
================================ */

.complaint-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  gap: 20px;
  align-items: start;
}

.main-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}


/* ================================
   CARDS
================================ */

.section-card,
.info-card,
.help-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 15px;
}

.section-card {
  padding: 25px 27px;
}

.info-card {
  padding: 22px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 15px;

  margin-bottom: 20px;
}

.section-header h2 {
  margin: 4px 0 0;

  font-size: 18px;
  font-weight: 750;
}

.description-box {
  padding: 17px 18px;

  background: var(--panel-alt);
  border: 1px solid var(--border);
  border-radius: 10px;

  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
}


/* ================================
   ACTION CARD
================================ */

.action-card {
  border-color: rgba(45, 145, 95, .25);
}

.action-message {
  display: flex;
  align-items: flex-start;
  gap: 13px;

  padding: 15px;

  background: var(--accent-glow);
  border-radius: 11px;

  margin-bottom: 20px;
}

.action-message.resolve {
  background: rgba(50, 150, 95, .08);
}

.action-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 9px;

  background: var(--accent);
  color: white;

  font-size: 13px;
  font-weight: 800;
}

.action-message h3 {
  margin: 1px 0 4px;
  font-size: 14px;
}

.action-message p {
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.5;
}

.notes-field {
  margin-bottom: 14px;
}

.notes-field label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 7px;

  font-size: 11px;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: .05em;
}

.notes-field label span {
  color: var(--text-dim);
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
}

.notes-field textarea {
  width: 100%;
  box-sizing: border-box;

  min-height: 88px;
  resize: vertical;

  padding: 12px 14px;

  border: 1px solid var(--border);
  border-radius: 10px;

  background: var(--panel-alt);
  color: var(--text);

  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;

  outline: none;
  transition: .18s ease;
}

.notes-field textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.primary-action {
  width: 100%;
  min-height: 45px;

  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;

  border: none;
  border-radius: 10px;

  background: var(--accent);
  color: white;

  font-size: 13px;
  font-weight: 750;

  cursor: pointer;
  transition: .18s ease;
}

.primary-action:hover:not(:disabled) {
  background: var(--accent-dark);
  transform: translateY(-1px);
}

.primary-action:disabled {
  opacity: .6;
  cursor: not-allowed;
}

.resolve-btn {
  background: var(--ok);
}

.action-arrow {
  font-size: 17px;
}

.action-error {
  margin: 0 0 12px;
  padding: 10px 12px;

  border-radius: 8px;

  background: rgba(190, 60, 60, .08);
  color: var(--danger);

  font-size: 12px;
}

.action-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;

  padding: 6px 9px;

  border-radius: 999px;

  background: var(--panel-alt);

  color: var(--text-dim);

  font-size: 10px;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: .04em;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.action-status.approved {
  color: var(--accent);
}

.action-status.in_progress {
  color: var(--accent);
}

.action-status.resolved {
  color: var(--ok);
}

.no-action {
  display: flex;
  align-items: center;
  gap: 14px;

  padding: 16px;

  background: var(--panel-alt);
  border-radius: 10px;
}

.no-action-icon {
  width: 34px;
  height: 34px;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: rgba(60, 150, 100, .1);
  color: var(--ok);

  font-weight: 800;
}

.no-action h3 {
  margin: 0 0 3px;
  font-size: 14px;
}

.no-action p {
  margin: 0;
  color: var(--text-dim);
  font-size: 12px;
}


/* ================================
   HISTORY
================================ */

.history-count {
  padding: 5px 9px;
  border-radius: 999px;

  background: var(--panel-alt);

  color: var(--text-dim);

  font-size: 11px;
  font-weight: 700;
}

.timeline {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: grid;
  grid-template-columns: 25px 1fr;
}

.timeline-track {
  position: relative;
  display: flex;
  justify-content: center;
}

.timeline-dot {
  width: 10px;
  height: 10px;

  margin-top: 5px;

  border-radius: 50%;

  background: var(--border);

  border: 2px solid var(--panel);

  box-shadow: 0 0 0 1px var(--border);

  z-index: 2;
}

.timeline-dot.latest {
  background: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.timeline-line {
  position: absolute;

  top: 16px;
  bottom: -5px;

  width: 1px;

  background: var(--border);
}

.timeline-content {
  padding: 0 0 24px 12px;
}

.timeline-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 15px;
}

.transition {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;

  font-size: 13px;
  text-transform: capitalize;
}

.transition > span:first-child {
  color: var(--text-dim);
}

.transition-arrow {
  color: var(--text-dim);
}

.transition strong {
  color: var(--text);
}

.timeline-top time {
  color: var(--text-dim);
  font-size: 11px;
  white-space: nowrap;
}

.changed-by {
  display: flex;
  align-items: center;
  gap: 7px;

  margin-top: 8px;

  color: var(--text-dim);
  font-size: 11px;
}

.changed-by strong {
  color: var(--text);
}

.person-avatar {
  width: 22px;
  height: 22px;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: var(--panel-alt);
  border: 1px solid var(--border);

  color: var(--accent);

  font-size: 9px;
  font-weight: 800;
}

.empty-history {
  padding: 25px;
  text-align: center;

  background: var(--panel-alt);
  border-radius: 10px;
}

.empty-history-icon {
  font-size: 25px;
  color: var(--text-dim);
}

.empty-history h3 {
  margin: 7px 0 3px;
  font-size: 14px;
}

.empty-history p {
  margin: 0;
  color: var(--text-dim);
  font-size: 12px;
}


/* ================================
   SIDEBAR
================================ */

.status-display {
  margin: 12px 0;
}

.status-description {
  margin: 0;

  color: var(--text-dim);

  font-size: 12px;
  line-height: 1.6;
}


/* Workflow */

.workflow {
  margin-top: 17px;
}

.workflow-step {
  position: relative;

  display: flex;
  align-items: flex-start;
  gap: 11px;

  padding-bottom: 20px;
}

.workflow-step:last-child {
  padding-bottom: 0;
}

.workflow-step:not(:last-child)::after {
  content: '';

  position: absolute;

  left: 11px;
  top: 24px;
  bottom: 2px;

  width: 1px;

  background: var(--border);
}

.workflow-marker {
  position: relative;
  z-index: 1;

  width: 23px;
  height: 23px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: var(--panel-alt);
  border: 1px solid var(--border);

  color: var(--text-dim);

  font-size: 10px;
  font-weight: 800;
}

.workflow-step.active .workflow-marker {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.workflow-step.current .workflow-marker {
  box-shadow: 0 0 0 4px var(--accent-glow);
}

.workflow-step strong {
  display: block;

  margin-top: 2px;

  font-size: 12px;
  text-transform: capitalize;
}

.workflow-step span {
  display: block;

  margin-top: 3px;

  color: var(--text-dim);
  font-size: 10px;
}


/* Help */

.help-card {
  display: flex;
  align-items: flex-start;
  gap: 11px;

  padding: 17px;

  background: var(--panel-alt);
}

.help-icon {
  width: 27px;
  height: 27px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: var(--accent-glow);
  color: var(--accent);

  font-size: 12px;
  font-weight: 800;
}

.help-card h3 {
  margin: 0 0 4px;
  font-size: 12px;
}

.help-card p {
  margin: 0;

  color: var(--text-dim);

  font-size: 11px;
  line-height: 1.5;
}


/* ================================
   LOADING / ERROR
================================ */

.page-state {
  min-height: 65vh;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 40px;
}

.state-card {
  width: min(400px, 100%);
  padding: 35px;

  text-align: center;

  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 15px;
}

.state-card p {
  color: var(--text-dim);
  font-size: 13px;
}

.error-state h3 {
  margin: 10px 0 5px;
}

.state-icon {
  width: 40px;
  height: 40px;

  margin: 0 auto;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: rgba(190, 60, 60, .1);
  color: var(--danger);

  font-weight: 800;
}

.loader {
  width: 28px;
  height: 28px;

  margin: 0 auto 12px;

  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;

  animation: spin .8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}


/* ================================
   RESPONSIVE
================================ */

@media (max-width: 1050px) {
  .complaint-grid {
    grid-template-columns: 1fr;
  }

  .side-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .help-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 700px) {
  .complaint-page {
    padding: 18px 15px 60px;
  }

  .complaint-hero {
    align-items: flex-start;
    flex-direction: column;
    padding: 20px;
  }

  .hero-status {
    align-self: flex-start;
  }

  .hero-content h1 {
    font-size: 23px;
  }

  .section-card,
  .info-card {
    padding: 19px;
  }

  .side-column {
    display: flex;
  }

  .section-header {
    flex-direction: column;
  }

  .timeline-top {
    flex-direction: column;
    gap: 4px;
  }
}

</style>