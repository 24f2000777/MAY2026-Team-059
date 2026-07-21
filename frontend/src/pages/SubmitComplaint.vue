<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()

const category = ref('Water Leak')
const description = ref('')
const location = ref('')
const severity = ref('Medium')
const photoPreview = ref(null)
const pin = ref(null)
const error = ref('')

function onPhotoChange(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => (photoPreview.value = reader.result)
  reader.readAsDataURL(file)
}

function setPin(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  pin.value = { x: ((e.clientX - rect.left) / rect.width) * 100, y: ((e.clientY - rect.top) / rect.height) * 100 }
}

function submit() {
  error.value = ''
  if (!pin.value) { error.value = 'Tap on the map to mark the location.'; return }
  store.submit({
    citizenId: auth.user.id, citizenName: auth.user.name, category: category.value,
    description: description.value, location: location.value, severity: severity.value,
    photo: photoPreview.value, pin: pin.value
  })
  router.push('/citizen')
}
</script>

<template>
  <div class="app-content">
    <h2>Report an Issue</h2>
    <form class="card" @submit.prevent="submit">
      <div class="field">
        <label>Category</label>
        <select v-model="category">
          <option>Water Leak</option><option>Pothole</option><option>Smog / Air Quality</option>
          <option>Streetlight Outage</option><option>Garbage Collection</option><option>Other</option>
        </select>
      </div>
      <div class="field"><label>Location</label><input v-model="location" required /></div>
      <div class="field"><label>Describe the issue</label><textarea v-model="description" rows="4" required></textarea></div>
      <div class="field">
        <label>Severity</label>
        <select v-model="severity"><option>Low</option><option>Medium</option><option>High</option></select>
      </div>
      <div class="field">
        <label>Pin the location</label>
        <div class="map-pin-area" @click="setPin">
          <div v-if="pin" class="map-pin-marker" :style="{ left: pin.x + '%', top: pin.y + '%' }"></div>
        </div>
      </div>
      <div class="field">
        <label>Attach a photo (optional)</label>
        <input type="file" accept="image/*" @change="onPhotoChange" />
        <img v-if="photoPreview" :src="photoPreview" class="photo-preview" />
      </div>
      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="btn block" type="submit">Confirm &amp; Submit</button>
    </form>
  </div>
</template>
<style scoped>
.photo-preview { margin-top: 10px; max-width: 100%; max-height: 200px; border-radius: var(--radius); border: 1px solid var(--border); }
</style>