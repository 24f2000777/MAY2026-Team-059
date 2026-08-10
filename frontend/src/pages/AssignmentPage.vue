<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { assignComplaint, getComplaint, listAttachments, listOfficers } from '../api/complaintApi'
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
const officers = ref([])
const attachments = ref([])
const selectedStaff = ref('')
const loading = ref(true)
const loadError = ref('')
const assignError = ref('')
const saving = ref(false)

onMounted(async () => {
  try {
    const [detail, officersData, attachmentsData] = await Promise.all([
      getComplaint({ id: route.params.id, accessToken: auth.accessToken }),
      listOfficers({ accessToken: auth.accessToken }),
      listAttachments({ id: route.params.id, accessToken: auth.accessToken })
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
    loadError.value = e.message
  } finally {
    loading.value = false
  }
})

async function confirmAssignment() {
  if (!selectedStaff.value) return
  saving.value = true
  assignError.value = ''
  try {
    await assignComplaint({ id: route.params.id, assignedTo: selectedStaff.value, accessToken: auth.accessToken })
    router.push('/admin')
  } catch (e) {
    assignError.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="app-content" v-if="loading">
    <p class="page-intro">Loading...</p>
  </div>

  <div class="app-content" v-else-if="loadError">
    <p class="error-text">{{ loadError }}</p>
  </div>

  <div class="app-content" v-else-if="complaint">
    <button class="btn secondary" @click="router.push('/admin')">&larr; Back</button>
    <div class="card">
      <div class="header-row"><h2>{{ categoryLabel(complaint.category) }}</h2><StatusBadge :value="complaint.status" /></div>
      <p class="location">{{ complaint.location_text || 'No location recorded' }}</p>
      <p class="desc">{{ complaint.description }}</p>
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
      <h3>Assign a Staff Member</h3>
      <p v-if="assignError" class="error-text">{{ assignError }}</p>
      <div v-if="officers.length === 0" class="empty-state">
        No staff accounts exist yet. <router-link to="/admin/staff">Create one here</router-link>.
      </div>
      <template v-else>
        <div class="field">
          <label>Staff member</label>
          <select v-model="selectedStaff">
            <option value="" disabled>Select staff</option>
            <option v-for="o in officers" :key="o.id" :value="o.id">{{ o.name }}</option>
          </select>
        </div>
        <button class="btn" :disabled="saving" @click="confirmAssignment">{{ saving ? 'Assigning...' : 'Confirm Assignment' }}</button>
      </template>
    </div>
  </div>
</template>
<style scoped>
.header-row { display: flex; justify-content: space-between; align-items: center; }
.location { color: var(--text-dim); font-size: 13px; }
.desc { color: var(--text-dim); }
.attachment-grid { display: flex; gap: 10px; flex-wrap: wrap; }
.attachment-thumb { display: block; width: 100px; height: 100px; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--border); }
.attachment-thumb img { width: 100%; height: 100%; object-fit: cover; }
</style>
