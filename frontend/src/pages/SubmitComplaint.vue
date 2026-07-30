<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { getWards, createComplaint } from '../api/complaintApi'
import StatusBadge from '../components/StatusBadge.vue'

const auth = useAuthStore()

// Real ComplaintCategory enum values (app/schemas/complaint.py), not the
// old mock's free-text category names.
const CATEGORIES = [
  { value: 'pothole', label: 'Pothole' },
  { value: 'road', label: 'Road Damage' },
  { value: 'streetlight', label: 'Streetlight Outage' },
  { value: 'drainage', label: 'Drainage / Flooding' },
  { value: 'garbage', label: 'Garbage Collection' },
  { value: 'water_supply', label: 'Water Supply' },
  { value: 'sewage', label: 'Sewage' },
  { value: 'traffic', label: 'Traffic' },
  { value: 'electricity', label: 'Electricity' },
  { value: 'other', label: 'Other' }
]

const category = ref('pothole')
const description = ref('')
const address = ref('')
const wardCode = ref('')
const wards = ref([])
const wardsError = ref('')

const coords = ref(null) // { latitude, longitude } once the browser supplies them
const locatingError = ref('')
const isLocating = ref(false)

const error = ref('')
const isSubmitting = ref(false)
const filedComplaint = ref(null) // set on success, replaces the form with a confirmation

onMounted(async () => {
  try {
    const data = await getWards({ accessToken: auth.accessToken })
    wards.value = data.wards
  } catch (e) {
    // A citizen can still submit without picking a ward (it's optional,
    // priority scoring falls back to a dataset-average estimate), so a
    // failed wards lookup shouldn't block the whole form.
    wardsError.value = 'Could not load the ward list. You can still submit without picking one.'
  }
})

function useMyLocation() {
  locatingError.value = ''
  if (!navigator.geolocation) {
    locatingError.value = 'Your browser does not support location access.'
    return
  }
  isLocating.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      coords.value = { latitude: position.coords.latitude, longitude: position.coords.longitude }
      isLocating.value = false
    },
    () => {
      locatingError.value = 'Could not get your location. You can still type an address instead.'
      isLocating.value = false
    },
    { timeout: 10000 }
  )
}

async function submit() {
  error.value = ''

  if (!coords.value && !address.value.trim()) {
    error.value = 'Share your location or type an address.'
    return
  }
  if (description.value.trim().length < 20) {
    error.value = 'Please describe the issue in at least 20 characters.'
    return
  }

  isSubmitting.value = true
  try {
    const label = CATEGORIES.find(c => c.value === category.value)?.label || category.value
    const title = `${label} - ${description.value.trim()}`.slice(0, 100)
    const data = await createComplaint({
      title,
      description: description.value.trim(),
      category: category.value,
      location: {
        latitude: coords.value?.latitude ?? null,
        longitude: coords.value?.longitude ?? null,
        address: address.value.trim() || null
      },
      wardCode: wardCode.value || null,
      accessToken: auth.accessToken
    })
    filedComplaint.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}

function fileAnother() {
  filedComplaint.value = null
  description.value = ''
  address.value = ''
  wardCode.value = ''
  coords.value = null
}
</script>

<template>
  <div class="app-content">
    <h2>Report an Issue</h2>

    <div v-if="filedComplaint" class="card">
      <h3>Complaint filed</h3>
      <div class="row top">
        <strong>{{ CATEGORIES.find(c => c.value === filedComplaint.category)?.label || filedComplaint.category }}</strong>
        <StatusBadge :value="filedComplaint.status" />
      </div>
      <p class="priority">Priority score: {{ filedComplaint.priority_score }}</p>
      <p class="date">Filed {{ new Date(filedComplaint.created_at).toLocaleString() }}</p>
      <button class="btn block" type="button" @click="fileAnother">File another complaint</button>
    </div>

    <form v-else class="card" @submit.prevent="submit">
      <div class="field">
        <label>Category</label>
        <select v-model="category">
          <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
      </div>

      <div class="field">
        <label>Ward (optional, improves priority scoring)</label>
        <select v-model="wardCode">
          <option value="">Not sure / skip</option>
          <option v-for="w in wards" :key="w.code" :value="w.code">{{ w.area }} ({{ w.code }})</option>
        </select>
        <p v-if="wardsError" class="hint-text">{{ wardsError }}</p>
      </div>

      <div class="field">
        <label>Describe the issue</label>
        <textarea v-model="description" rows="4" required placeholder="At least 20 characters"></textarea>
      </div>

      <div class="field">
        <label>Location</label>
        <input v-model="address" placeholder="Address or landmark" />
        <button class="btn secondary" type="button" @click="useMyLocation" :disabled="isLocating">
          {{ isLocating ? 'Locating…' : coords ? 'Location shared ✓' : 'Use my current location' }}
        </button>
        <p v-if="locatingError" class="hint-text">{{ locatingError }}</p>
      </div>

      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="btn block" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? 'Submitting…' : 'Confirm & Submit' }}
      </button>
    </form>
  </div>
</template>
<style scoped>
.priority { color: var(--accent); font-weight: 700; margin: 8px 0; }
.date { font-size: 12px; color: var(--text-dim); margin-bottom: 16px; }
.hint-text { font-size: 13px; color: var(--text-dim); margin-top: 4px; }
.row.top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.btn.secondary { background: transparent; border: 1px solid var(--border); color: var(--text); margin-top: 8px; }
</style>
