<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { deleteComplaint, getComplaint, getComplaintHistory, getFeedback, listAttachments } from '../api/complaintApi'
import { API_BASE_URL } from '../api/httpClient'
import { categoryLabel } from '../constants/categories'
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
const history = ref([])
const attachments = ref([])
const feedback = ref(null)
const loadError = ref('')
const loading = ref(true)
const deleteError = ref('')
const deleting = ref(false)

const isOwner = computed(() => complaint.value && complaint.value.citizen_id === auth.user?.id)
// Deleting outright is only offered before anyone's acted on it, same
// rule the backend enforces (delete_own_complaint) - once approved,
// withdraw is the citizen's option instead.
const canDelete = computed(() => isOwner.value && complaint.value?.status === 'submitted')

// The photos filed with the complaint vs the proof-of-fix photo staff
// uploads once it's resolved, kept visually separate so it's obvious
// which is which.
const citizenPhotos = computed(() => attachments.value.filter(a => a.purpose !== 'resolution_proof'))
const resolutionPhotos = computed(() => attachments.value.filter(a => a.purpose === 'resolution_proof'))

async function removeComplaint() {
  if (!confirm('Delete this complaint permanently? This cannot be undone.')) return
  deleteError.value = ''
  deleting.value = true
  try {
    await deleteComplaint({ id: complaint.value.id, accessToken: auth.accessToken })
    router.push('/citizen')
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    deleteError.value = e.message
  } finally {
    deleting.value = false
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [detail, historyData, attachmentsData] = await Promise.all([
      getComplaint({ id: route.params.id, accessToken: auth.accessToken }),
      getComplaintHistory({ id: route.params.id, accessToken: auth.accessToken }),
      listAttachments({ id: route.params.id, accessToken: auth.accessToken })
    ])
    complaint.value = detail
    history.value = historyData.history
    attachments.value = attachmentsData.attachments

    if (detail.status === 'resolved' || detail.status === 'closed') {
      feedback.value = await getFeedback({ id: route.params.id, accessToken: auth.accessToken })
    }
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

onMounted(load)
</script>

<template>
  <div class="app-content">

    <!-- Back -->
    <button class="btn secondary back-btn" @click="router.push('/citizen')">
      ← Back to My Complaints
    </button>

    <p v-if="loading" class="page-intro">
      Loading complaint...
    </p>

    <p v-else-if="loadError" class="error-text">
      {{ loadError }}
    </p>

    <template v-else-if="complaint">

      <div class="complaint-page">

        <!-- Header -->
        <div class="complaint-header">
          <p class="complaint-eyebrow">MY COMPLAINT</p>

          <div class="detail-header-row">
            <div>
              <h2>{{ categoryLabel(complaint.category) }}</h2>

              <p class="detail-location">
                <span>⌖</span>
                {{ complaint.location_text || 'No location recorded' }}
              </p>
            </div>

            <StatusBadge :value="complaint.status" />
          </div>
        </div>


        <!-- Main content -->
        <div class="detail-layout">

          <!-- LEFT -->
          <div class="detail-main">

            <!-- Complaint -->
            <section class="detail-card">

              <div class="detail-card-header">
                <div class="detail-icon">▤</div>

                <div>
                  <h3>Complaint Details</h3>
                  <p>Information submitted by you</p>
                </div>
              </div>

              <div class="detail-description">
                {{ complaint.description }}
              </div>

              <div class="detail-info-grid">

                <div class="detail-info-item">
                  <span>Priority Score</span>
                  <strong>{{ complaint.priority_score }}</strong>
                </div>

                <div
                  v-if="complaint.department"
                  class="detail-info-item"
                >
                  <span>Department</span>
                  <strong>{{ complaint.department }}</strong>
                </div>

                <div
                  v-if="complaint.staff_details"
                  class="detail-info-item"
                >
                  <span>Assigned Officer</span>
                  <strong>{{ complaint.staff_details.name }}</strong>
                </div>

              </div>

              <!-- Rejection -->
              <div
                v-if="complaint.reject_reason"
                class="rejection-box"
              >
                <strong>Complaint rejected</strong>
                <p>{{ complaint.reject_reason }}</p>
              </div>

            </section>


            <!-- Attachments -->
            <section
              v-if="citizenPhotos.length > 0"
              class="detail-card"
            >

              <div class="detail-card-header">
                <div class="detail-icon">▧</div>

                <div>
                  <h3>Attachments</h3>
                  <p>Photos submitted with your complaint</p>
                </div>
              </div>

              <div class="attachment-grid">

                <a
                  v-for="a in citizenPhotos"
                  :key="a.id"
                  :href="attachmentUrl(a.image_url)"
                  target="_blank"
                  rel="noopener"
                  class="attachment-thumb"
                >
                  <img
                    :src="attachmentUrl(a.image_url)"
                    alt="Complaint attachment"
                  />

                  <span>View</span>
                </a>

              </div>

            </section>


            <!-- Resolution photos -->
            <section
              v-if="resolutionPhotos.length > 0"
              class="detail-card resolution-card"
            >

              <div class="detail-card-header">
                <div class="detail-icon">✓</div>

                <div>
                  <h3>Proof of Resolution</h3>
                  <p>Photos the staff member uploaded showing the fix</p>
                </div>
              </div>

              <div class="attachment-grid">

                <a
                  v-for="a in resolutionPhotos"
                  :key="a.id"
                  :href="attachmentUrl(a.image_url)"
                  target="_blank"
                  rel="noopener"
                  class="attachment-thumb"
                >
                  <img
                    :src="attachmentUrl(a.image_url)"
                    alt="Resolution photo"
                  />

                  <span>View</span>
                </a>

              </div>

            </section>

          </div>


          <!-- RIGHT -->
          <aside class="detail-side">

            <!-- Current status -->
            <section class="detail-card status-card">

              <div class="detail-card-header">
                <div class="detail-icon">●</div>

                <div>
                  <h3>Current Status</h3>
                  <p>Latest update on your complaint</p>
                </div>
              </div>

              <div class="current-status">
                <StatusBadge :value="complaint.status" />
              </div>

              <template v-if="canDelete">
                <p v-if="deleteError" class="error-text" style="margin-top: 12px;">{{ deleteError }}</p>
                <button
                  class="btn secondary danger-btn"
                  style="margin-top: 14px; width: 100%;"
                  :disabled="deleting"
                  @click="removeComplaint"
                >
                  {{ deleting ? 'Deleting...' : 'Delete Complaint' }}
                </button>
              </template>

            </section>


            <!-- History -->
            <section class="detail-card">

              <div class="detail-card-header">
                <div class="detail-icon">◷</div>

                <div>
                  <h3>Status History</h3>
                  <p>Track how your complaint has progressed</p>
                </div>
              </div>

              <ul
                v-if="history.length > 0"
                class="detail-timeline"
              >

                <li
                  v-for="(h, index) in history"
                  :key="h.id"
                  :class="{ last: index === history.length - 1 }"
                >

                  <div class="timeline-dot"></div>

                  <div class="timeline-content">

                    <strong>
                      {{ h.old_status
                        ? `${h.old_status} → ${h.new_status}`
                        : h.new_status
                      }}
                    </strong>

                    <p>
                      Updated by {{ h.changed_by.name }}
                    </p>

                    <span>
                      {{ new Date(h.created_at).toLocaleString() }}
                    </span>

                  </div>

                </li>

              </ul>

              <p
                v-else
                class="empty-history"
              >
                No status updates yet.
              </p>

            </section>

          </aside>

        </div>


        <!-- Rating -->
        <section
          v-if="isOwner && complaint.status === 'resolved'"
          class="rating-card"
        >

          <div class="rating-icon">
            ★
          </div>

          <div class="rating-content">

            <p class="rating-eyebrow">
              RESOLUTION FEEDBACK
            </p>

            <h3>
              {{ feedback
                ? 'You rated this resolution'
                : 'How was the resolution?'
              }}
            </h3>

            <p v-if="feedback">

              <span class="rating-stars">
                {{ feedback.score }} / 5 stars
              </span>

              <span v-if="feedback.feedback">
                · "{{ feedback.feedback }}"
              </span>

            </p>

            <p v-else>
              Your feedback helps us improve civic services.
            </p>

          </div>

          <button
            class="btn secondary"
            @click="router.push(`/citizen/${complaint.id}/rate`)"
          >
            {{ feedback ? 'Edit Rating' : 'Rate Resolution' }}
          </button>

        </section>

      </div>
      
    </template>

  </div>
</template>
<style scoped>
.back-btn {
  margin-bottom: 24px;
}

.danger-btn {
  border-color: rgba(192, 57, 43, .3);
  color: var(--danger);
}

.danger-btn:hover:not(:disabled) {
  background: rgba(192, 57, 43, .08);
  border-color: var(--danger);
}


/* Header */

.complaint-header {
  margin-bottom: 30px;
}

.complaint-eyebrow {
  margin: 0 0 7px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .1em;
}

.detail-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.detail-header-row h2 {
  margin: 0 0 8px;
  color: var(--ink);
  font-size: 30px;
  font-weight: 900;
  letter-spacing: -.02em;
}

.detail-location {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
}

.detail-location span {
  color: var(--accent);
  font-size: 16px;
}


/* Layout */

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, .65fr);
  gap: 20px;
  align-items: start;
}

.detail-main,
.detail-side {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-side {
  position: sticky;
  top: 88px;
}


/* Cards */

.detail-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 3px 12px rgba(22, 48, 31, .045);
}

.detail-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 18px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border);
}

.detail-card-header h3 {
  margin: 0 0 3px;
  color: var(--ink);
  font-size: 17px;
  font-weight: 800;
}

.detail-card-header p {
  margin: 0;
  color: var(--text-dim);
  font-size: 12px;
}

.detail-icon {
  width: 38px;
  height: 38px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 10px;
  background: var(--accent-glow);
  color: var(--accent-dark);

  font-size: 17px;
  font-weight: 800;
}


/* Description */

.detail-description {
  color: var(--text);
  font-size: 15px;
  line-height: 1.7;
  margin-bottom: 22px;
}


/* Information */

.detail-info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.detail-info-item {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--panel-alt);
}

.detail-info-item span {
  display: block;
  margin-bottom: 5px;

  color: var(--text-dim);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
}

.detail-info-item strong {
  display: block;
  color: var(--ink);
  font-size: 13px;
}


/* Rejection */

.rejection-box {
  margin-top: 18px;
  padding: 14px 16px;

  border: 1px solid rgba(192, 57, 43, .2);
  border-left: 3px solid var(--danger);
  border-radius: var(--radius);

  background: rgba(192, 57, 43, .05);
}

.rejection-box strong {
  color: var(--danger);
  font-size: 12px;
}

.rejection-box p {
  margin: 5px 0 0;

  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.5;
}


/* Status */

.current-status {
  padding: 8px 0 2px;
}


/* Resolution photos */

.resolution-card {
  border-top: 3px solid var(--ok);
}

/* Attachments */

.attachment-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.attachment-thumb {
  position: relative;
  overflow: hidden;

  display: block;
  aspect-ratio: 1.15;

  border: 1px solid var(--border);
  border-radius: var(--radius);

  background: var(--panel-alt);
}

.attachment-thumb img {
  width: 100%;
  height: 100%;
  display: block;

  object-fit: cover;

  transition: transform .25s ease;
}

.attachment-thumb:hover img {
  transform: scale(1.05);
}

.attachment-thumb span {
  position: absolute;
  left: 7px;
  bottom: 7px;

  padding: 5px 8px;

  border-radius: 6px;
  background: rgba(22, 48, 31, .78);

  color: #fff;
  font-size: 10px;
  font-weight: 700;
}


/* Timeline */

.detail-timeline {
  list-style: none;
  padding: 0;
  margin: 0;
}

.detail-timeline li {
  position: relative;

  display: flex;
  gap: 13px;

  min-height: 76px;
}

.timeline-dot {
  position: relative;
  z-index: 2;

  width: 10px;
  height: 10px;
  flex-shrink: 0;

  margin-top: 5px;

  border-radius: 50%;
  background: var(--accent);

  box-shadow: 0 0 0 4px var(--accent-glow);
}

.detail-timeline li:not(.last)::after {
  content: '';

  position: absolute;

  left: 4px;
  top: 15px;
  bottom: 0;

  width: 2px;

  background: var(--border);
}

.timeline-content {
  padding-bottom: 18px;
}

.timeline-content strong {
  display: block;

  color: var(--ink);
  font-size: 13px;
  font-weight: 800;
}

.timeline-content p {
  margin: 4px 0;

  color: var(--text-dim);
  font-size: 11px;
}

.timeline-content span {
  color: var(--text-dim);
  font-size: 10px;
}

.empty-history {
  margin: 0;
  padding: 20px 0;

  color: var(--text-dim);
  font-size: 13px;
}


/* Rating */

.rating-card {
  display: flex;
  align-items: center;
  gap: 16px;

  margin-top: 20px;
  padding: 20px 22px;

  background: var(--panel);
  border: 1px solid var(--border);
  border-top: 3px solid var(--ok);
  border-radius: var(--radius-lg);

  box-shadow: 0 3px 12px rgba(22, 48, 31, .045);
}

.rating-icon {
  width: 44px;
  height: 44px;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;
  background: rgba(42, 157, 143, .12);

  color: var(--ok);
  font-size: 20px;
}

.rating-content {
  flex: 1;
  min-width: 0;
}

.rating-eyebrow {
  margin: 0 0 3px;

  color: var(--ok);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .08em;
}

.rating-content h3 {
  margin: 0 0 4px;

  color: var(--ink);
  font-size: 16px;
}

.rating-content p {
  margin: 0;

  color: var(--text-dim);
  font-size: 12px;
  line-height: 1.5;
}

.rating-stars {
  color: var(--warn);
  font-weight: 700;
}


/* Responsive */

@media (max-width: 900px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }

  .detail-side {
    position: static;
  }
}

@media (max-width: 620px) {
  .back-btn {
    width: 100%;
    margin-bottom: 20px;
  }

  .detail-header-row {
    flex-direction: column;
    gap: 12px;
  }

  .detail-header-row h2 {
    font-size: 25px;
  }

  .detail-card {
    padding: 18px;
  }

  .detail-info-grid {
    grid-template-columns: 1fr;
  }

  .attachment-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .rating-card {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .rating-content {
    min-width: calc(100% - 60px);
  }

  .rating-card .btn {
    width: 100%;
  }
}
</style>