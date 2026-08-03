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
  <div class="app-content" v-if="loading">
    <p class="page-intro">Loading...</p>
  </div>

  <div class="app-content" v-else-if="loadError">
    <p class="error-text">{{ loadError }}</p>
  </div>

  <div class="app-content" v-else-if="complaint">
    <button class="btn secondary" @click="router.push('/staff')">&larr; Back</button>
    <div class="card">
      <div class="header-row"><h2>{{ categoryLabel(complaint.category) }}</h2><StatusBadge :value="complaint.status" /></div>
      <p class="location">{{ complaint.location_text || 'No location recorded' }}</p>
      <p class="desc">{{ complaint.description }}</p>
    </div>
    <div class="card">
      <h3>Update Status</h3>
      <p v-if="actionError" class="error-text">{{ actionError }}</p>
      <div class="field"><label>Notes (optional)</label><textarea v-model="notes" rows="3"></textarea></div>

      <button v-if="complaint.status === 'approved'" class="btn" :disabled="saving" @click="doStart">
        {{ saving ? 'Saving...' : 'Start Work' }}
      </button>
      <button v-else-if="complaint.status === 'in_progress'" class="btn" :disabled="saving" @click="doResolve">
        {{ saving ? 'Saving...' : 'Mark Resolved' }}
      </button>
      <p v-else class="page-intro">No action available from status "{{ complaint.status }}".</p>
    </div>
    <div class="card">
      <h3>History</h3>
      <ul v-if="history.length > 0" class="timeline">
        <li v-for="h in history" :key="h.id">
          <strong>{{ h.old_status ? `${h.old_status} → ${h.new_status}` : h.new_status }}</strong>
          <p class="note-item">Changed by {{ h.changed_by.name }}</p>
          <span class="ts">{{ new Date(h.created_at).toLocaleString() }}</span>
        </li>
      </ul>
      <p v-else class="page-intro">No status changes yet.</p>
    </div>
  </div>

  <div v-else class="card">
    <p>Complaint not found.</p>
    <router-link to="/staff" class="btn secondary">Back to my tasks</router-link>
  </div>
</template>
<style scoped>
.header-row { display: flex; justify-content: space-between; align-items: center; }
.location { color: var(--text-dim); font-size: 13px; }
.desc { color: var(--text-dim); }
.note-item { font-size: 13px; color: var(--text-dim); margin: 4px 0; }
.ts { font-size: 12px; color: var(--text-dim); }
</style>
