<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getComplaint, getComplaintHistory, getFeedback, listAttachments } from '../api/complaintApi'
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

const isOwner = computed(() => complaint.value && complaint.value.citizen_id === auth.user?.id)

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
    <button class="btn secondary" @click="router.push('/citizen')">&larr; Back</button>

    <p v-if="loading" class="page-intro">Loading...</p>
    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>

    <template v-else-if="complaint">
      <div class="card">
        <div class="header-row">
          <div>
            <h2>{{ categoryLabel(complaint.category) }}</h2>
            <p class="location">{{ complaint.location_text || 'No location recorded' }}</p>
          </div>
          <div class="badges">
            <StatusBadge :value="complaint.status" />
          </div>
        </div>
        <p class="desc">{{ complaint.description }}</p>
        <p class="meta-line">Priority score: {{ complaint.priority_score }}</p>
        <p v-if="complaint.department" class="meta-line">Department: {{ complaint.department }}</p>
        <p v-if="complaint.staff_details" class="meta-line">Assigned to: {{ complaint.staff_details.name }}</p>
        <p v-if="complaint.reject_reason" class="meta-line error-text">Rejected: {{ complaint.reject_reason }}</p>
      </div>

      <div v-if="attachments.length > 0" class="card">
        <h3>Attachments</h3>
        <div class="attachment-grid">
          <a v-for="a in attachments" :key="a.id" :href="attachmentUrl(a.image_url)" target="_blank" rel="noopener" class="attachment-thumb">
            <img :src="attachmentUrl(a.image_url)" alt="Attachment" />
          </a>
        </div>
      </div>

      <div class="card">
        <h3>Status History</h3>
        <ul v-if="history.length > 0" class="timeline">
          <li v-for="h in history" :key="h.id">
            <strong>{{ h.old_status ? `${h.old_status} → ${h.new_status}` : h.new_status }}</strong>
            <p class="note">Changed by {{ h.changed_by.name }}</p>
            <span class="ts">{{ new Date(h.created_at).toLocaleString() }}</span>
          </li>
        </ul>
        <p v-else class="page-intro">No status changes yet.</p>
      </div>

      <div v-if="isOwner && complaint.status === 'resolved'" class="card cta-row">
        <div>
          <p class="cta-title">{{ feedback ? 'You rated this resolution' : 'How was the resolution?' }}</p>
          <p class="page-intro cta-sub">
            <template v-if="feedback">{{ feedback.score }} / 5 stars<span v-if="feedback.feedback"> - "{{ feedback.feedback }}"</span></template>
            <template v-else>Let us know how it went.</template>
          </p>
        </div>
        <button class="btn secondary" @click="router.push(`/citizen/${complaint.id}/rate`)">
          {{ feedback ? 'Edit Rating' : 'Rate Resolution' }}
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.header-row { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.location { color: var(--text-dim); font-size: 13px; margin: 4px 0 0 0; }
.badges { display: flex; gap: 8px; }
.desc { color: var(--text-dim); }
.meta-line { font-size: 13px; color: var(--text-dim); margin: 4px 0 0 0; }
.photo { max-width: 100%; max-height: 260px; border-radius: var(--radius); border: 1px solid var(--border); margin-top: 10px; }
.note { color: var(--text-dim); font-size: 13px; margin: 4px 0; }
.ts { font-size: 12px; color: var(--text-dim); }
.attachment-grid { display: flex; gap: 10px; flex-wrap: wrap; }
.attachment-thumb { display: block; width: 100px; height: 100px; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--border); }
.attachment-thumb img { width: 100%; height: 100%; object-fit: cover; }
.cta-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.cta-title { margin: 0; font-weight: 700; }
.cta-sub { margin: 4px 0 0 0; }
</style>
