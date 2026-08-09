<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getWards, createComplaint, uploadAttachment } from '../api/complaintApi'
import { CATEGORIES, categoryLabel } from '../constants/categories'
import StatusBadge from '../components/StatusBadge.vue'

const auth = useAuthStore()
const router = useRouter()

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

// Server enforces the real limits (MAX_ATTACHMENTS_PER_COMPLAINT,
// MAX_UPLOAD_SIZE_BYTES), these just match the defaults for a nicer
// error before ever hitting the network.
const MAX_PHOTOS = 5
const MAX_PHOTO_BYTES = 5 * 1024 * 1024

const photos = ref([]) // [{ file, previewUrl }]
const photosError = ref('')
const attachmentsFailed = ref(false)
const fileInput = ref(null)

onMounted(async () => {
  try {
    const data = await getWards({ accessToken: auth.accessToken })
    wards.value = data.wards
  } catch (e) {
    if (e.status === 401) {
      // Same reasoning as NagrikSaathi.vue's onMounted: isLoggedIn only
      // checks that a token is present, not that it's still valid, so
      // clear the stale session before redirecting or the guest-route
      // guard would just bounce back here.
      await auth.logout()
      router.push('/login')
      return
    }
    // A citizen can still submit without picking a ward (it's optional,
    // priority scoring falls back to a dataset-average estimate), so any
    // other failure shouldn't block the whole form.
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

function triggerFilePicker() {
  fileInput.value?.click()
}

function onPhotosPicked(e) {
  photosError.value = ''
  const files = Array.from(e.target.files || [])
  e.target.value = '' // allow picking the exact same file again later

  if (photos.value.length + files.length > MAX_PHOTOS) {
    photosError.value = `You can attach up to ${MAX_PHOTOS} photos.`
    return
  }
  const oversized = files.find((f) => f.size > MAX_PHOTO_BYTES)
  if (oversized) {
    photosError.value = `${oversized.name} is over 5MB.`
    return
  }

  for (const file of files) {
    photos.value.push({ file, previewUrl: URL.createObjectURL(file) })
  }
}

function removePhoto(index) {
  URL.revokeObjectURL(photos.value[index].previewUrl)
  photos.value.splice(index, 1)
}

function clearPhotos() {
  for (const p of photos.value) URL.revokeObjectURL(p.previewUrl)
  photos.value = []
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
    const title = `${categoryLabel(category.value)} - ${description.value.trim()}`.slice(0, 100)
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

    // Best-effort: the complaint is already real at this point, a
    // failed photo upload shouldn't undo the filing or block the
    // confirmation, just surface that something didn't attach.
    if (photos.value.length > 0) {
      const results = await Promise.allSettled(
        photos.value.map((p) => uploadAttachment({ id: data.id, file: p.file, accessToken: auth.accessToken }))
      )
      attachmentsFailed.value = results.some((r) => r.status === 'rejected')
      clearPhotos()
    }
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}

function fileAnother() {
  filedComplaint.value = null
  attachmentsFailed.value = false
  description.value = ''
  address.value = ''
  wardCode.value = ''
  coords.value = null
  clearPhotos()
}
</script>

<template>
  <div class="app-content">
    <h2>Report an Issue</h2>

    <div v-if="filedComplaint" class="card">
      <h3>Complaint filed</h3>
      <div class="row top">
        <strong>{{ categoryLabel(filedComplaint.category) }}</strong>
        <StatusBadge :value="filedComplaint.status" />
      </div>
      <p class="priority">Priority score: {{ filedComplaint.priority_score }}</p>
      <p class="date">Filed {{ new Date(filedComplaint.created_at).toLocaleString() }}</p>
      <p v-if="attachmentsFailed" class="hint-text">Your complaint was filed, but one or more photos couldn't be attached. Please try again later or mention it if you follow up.</p>
      <button class="btn block" type="button" @click="fileAnother">File another complaint</button>
    </div>

    <form v-else class="card" @submit.prevent="submit">
      <div class="field">
        <label for="complaint-category">Category</label>
        <select id="complaint-category" v-model="category">
          <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
      </div>

      <div class="field">
        <label for="complaint-ward">Ward (optional, improves priority scoring)</label>
        <select id="complaint-ward" v-model="wardCode">
          <option value="">Not sure / skip</option>
          <option v-for="w in wards" :key="w.code" :value="w.code">{{ w.area }} ({{ w.code }})</option>
        </select>
        <p v-if="wardsError" class="hint-text">{{ wardsError }}</p>
      </div>

      <div class="field">
        <label for="complaint-description">Describe the issue</label>
        <textarea id="complaint-description" v-model="description" rows="4" required maxlength="1000" placeholder="At least 20 characters"></textarea>
      </div>

      <div class="field">
        <label for="complaint-address">Location</label>
        <input id="complaint-address" v-model="address" placeholder="Address or landmark" />
        <button class="btn secondary" type="button" @click="useMyLocation" :disabled="isLocating">
          {{ isLocating ? 'Locating…' : coords ? 'Location shared ✓' : 'Use my current location' }}
        </button>
        <p v-if="locatingError" class="hint-text">{{ locatingError }}</p>
      </div>

      <div class="field">
        <label id="complaint-photos-label">Photos (optional)</label>
        <input ref="fileInput" type="file" accept="image/*" multiple class="hidden-file-input" aria-labelledby="complaint-photos-label" @change="onPhotosPicked" />
        <button class="btn secondary" type="button" @click="triggerFilePicker">
          Add photos
        </button>
        <p v-if="photosError" class="hint-text">{{ photosError }}</p>
        <div v-if="photos.length > 0" class="photo-grid">
          <div v-for="(p, i) in photos" :key="i" class="photo-thumb">
            <img :src="p.previewUrl" alt="Photo to attach" />
            <button type="button" class="photo-remove" @click="removePhoto(i)">&times;</button>
          </div>
        </div>
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
.hidden-file-input { display: none; }
.photo-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.photo-thumb { position: relative; width: 72px; height: 72px; }
.photo-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: var(--radius); border: 1px solid var(--border); }
.photo-remove {
  position: absolute; top: -6px; right: -6px;
  width: 20px; height: 20px; border-radius: 50%;
  border: none; background: var(--ink); color: #fff;
  font-size: 13px; line-height: 1; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
</style>
