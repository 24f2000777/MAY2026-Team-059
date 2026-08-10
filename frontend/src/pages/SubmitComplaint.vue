<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useAuthStore } from '../stores/authStore'
import { getWards, createComplaint, uploadAttachment } from '../api/complaintApi'
import { CATEGORIES, categoryLabel } from '../constants/categories'

const auth = useAuthStore()
const router = useRouter()

const filedComplaint = ref(null)

const category = ref('')
const wardCode = ref('')
const description = ref('')
const address = ref('')

const coords = ref(null)
const isLocating = ref(false)
const locatingError = ref('')
const wards = ref([])
const wardsError = ref('')
const photosError = ref('')
const error = ref('')
const isSubmitting = ref(false)
const attachmentsFailed = ref(false)

// Server enforces the real limits (MAX_ATTACHMENTS_PER_COMPLAINT,
// MAX_UPLOAD_SIZE_BYTES), these just match the defaults for a nicer
// error before ever hitting the network.
const MAX_PHOTOS = 5
const MAX_PHOTO_BYTES = 5 * 1024 * 1024

const photos = ref([])
const fileInput = ref(null)

const mapContainer = ref(null)
let map = null
let marker = null

// Mumbai (BMC's jurisdiction), not the Leaflet/OSM demo default of
// New Delhi — this is where the map should open before a citizen has
// picked a real location yet.
const DEFAULT_MAP_CENTER = [19.0760, 72.8777]
const DEFAULT_MAP_ZOOM = 12

function updateLocation(lat, lng) {
  coords.value = {
    latitude: lat,
    longitude: lng
  }

  if (marker) {
    marker.setLatLng([lat, lng])
  } else {
    marker = L.marker([lat, lng], {
      draggable: true
    }).addTo(map)

    marker.on('dragend', () => {
      const position = marker.getLatLng()

      coords.value = {
        latitude: position.lat,
        longitude: position.lng
      }

      reverseGeocode(position.lat, position.lng)
    })
  }

  map.setView([lat, lng], 16)

  reverseGeocode(lat, lng)
}

async function reverseGeocode(lat, lng) {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`
    )

    if (!response.ok) return

    const data = await response.json()

    if (data.display_name) {
      address.value = data.display_name
    }
  } catch {
    /* Keep coordinates even if address lookup fails */
  }
}

function useMyLocation() {
  if (!navigator.geolocation) {
    locatingError.value = 'Location services are not supported by this browser.'
    return
  }

  isLocating.value = true
  locatingError.value = ''

  navigator.geolocation.getCurrentPosition(
    position => {
      updateLocation(
        position.coords.latitude,
        position.coords.longitude
      )

      isLocating.value = false
    },
    () => {
      locatingError.value =
        'Unable to access your location. Please select it directly on the map.'

      isLocating.value = false
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0
    }
  )
}

function handleMapClick(event) {
  updateLocation(event.latlng.lat, event.latlng.lng)
}

function triggerFilePicker() {
  fileInput.value?.click()
}

function onPhotosPicked(event) {
  photosError.value = ''

  const files = Array.from(event.target.files || [])
  if (fileInput.value) fileInput.value.value = '' // allow picking the exact same file again later

  if (files.length === 0) return

  if (photos.value.length + files.length > MAX_PHOTOS) {
    photosError.value = `You can attach up to ${MAX_PHOTOS} photos.`
    return
  }

  const validFiles = files.filter(file => {
    if (!file.type.startsWith('image/')) {
      return false
    }

    if (file.size > MAX_PHOTO_BYTES) {
      return false
    }

    return true
  })

  if (validFiles.length !== files.length) {
    photosError.value =
      'Only image files up to 5 MB each can be attached.'
  }

  validFiles.forEach(file => {
    photos.value.push({
      file,
      previewUrl: URL.createObjectURL(file)
    })
  })
}

function removePhoto(index) {
  const photo = photos.value[index]

  if (photo?.previewUrl) {
    URL.revokeObjectURL(photo.previewUrl)
  }

  photos.value.splice(index, 1)
}

function fileAnother() {
  filedComplaint.value = null
  attachmentsFailed.value = false

  category.value = ''
  wardCode.value = ''
  description.value = ''
  address.value = ''
  coords.value = null
  error.value = ''
  locatingError.value = ''

  photos.value.forEach(photo => {
    if (photo.previewUrl) {
      URL.revokeObjectURL(photo.previewUrl)
    }
  })

  photos.value = []

  if (marker) {
    map.removeLayer(marker)
    marker = null
  }

  if (map) {
    map.setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)
  }
}

async function submit() {
  error.value = ''

  if (!category.value) {
    error.value = 'Please select a category.'
    return
  }

  if (description.value.trim().length < 20) {
    error.value = 'Please describe the issue in at least 20 characters.'
    return
  }

  if (!coords.value && !address.value.trim()) {
    error.value = 'Please select the complaint location on the map, or type an address.'
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
        photos.value.map(p => uploadAttachment({ id: data.id, file: p.file, accessToken: auth.accessToken }))
      )
      attachmentsFailed.value = results.some(r => r.status === 'rejected')
    }
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    error.value = e.message || 'Unable to submit the complaint. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(async () => {
  map = L.map(mapContainer.value, {
    zoomControl: true
  }).setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)

  L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }
  ).addTo(map)

  map.on('click', handleMapClick)

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

onBeforeUnmount(() => {
  photos.value.forEach(photo => {
    if (photo.previewUrl) {
      URL.revokeObjectURL(photo.previewUrl)
    }
  })

  if (map) {
    map.remove()
  }
})
</script>

<template>
  <div class="app-content complaint-page">

    <div class="header-row complaint-header">
      <div>
        <p class="complaint-eyebrow">CITIZEN SERVICES</p>
        <h2>Report a Civic Issue</h2>
        <p class="page-intro">
          Help your local administration understand and resolve problems in your area.
        </p>
      </div>
    </div>

    <div v-if="filedComplaint" class="complaint-success card">

      <div class="success-icon">
        ✓
      </div>

      <div class="success-content">
        <p class="success-eyebrow">SUBMISSION COMPLETE</p>

        <h3>Complaint filed successfully</h3>

        <div class="success-row">
          <strong>
            {{ categoryLabel(filedComplaint.category) }}
          </strong>

          <StatusBadge :value="filedComplaint.status" />
        </div>

        <div class="success-details">
          <div>
            <span>Priority score</span>
            <strong>{{ filedComplaint.priority_score }}</strong>
          </div>

          <div>
            <span>Filed</span>
            <strong>
              {{ new Date(filedComplaint.created_at).toLocaleString() }}
            </strong>
          </div>
        </div>

        <p v-if="attachmentsFailed" class="hint-text">
          Your complaint was filed, but one or more photos couldn't be attached.
          Please try again later or mention it if you follow up.
        </p>

        <button
          class="btn"
          type="button"
          @click="fileAnother"
        >
          File another complaint
        </button>
      </div>
    </div>

    <form
      v-else
      class="complaint-form"
      @submit.prevent="submit"
    >

      <div class="complaint-layout">

        <div class="complaint-main">

          <section class="form-card card">

            <div class="form-card-header">
              <div class="form-step">01</div>

              <div>
                <h3>Issue details</h3>
                <p>
                  Tell us what needs attention.
                </p>
              </div>
            </div>

            <div class="field">
              <label>Category</label>

              <select v-model="category" required>
                <option value="" disabled>
                  Select an issue category
                </option>

                <option
                  v-for="c in CATEGORIES"
                  :key="c.value"
                  :value="c.value"
                >
                  {{ c.label }}
                </option>
              </select>
            </div>

            <div class="field">
              <label>Ward</label>

              <select v-model="wardCode">
                <option value="">
                  Not sure / skip
                </option>

                <option
                  v-for="w in wards"
                  :key="w.code"
                  :value="w.code"
                >
                  {{ w.area }} ({{ w.code }})
                </option>
              </select>

              <p v-if="wardsError" class="hint-text">
                {{ wardsError }}
              </p>

              <p class="field-help">
                Selecting your ward can improve priority scoring.
              </p>
            </div>

            <div class="field">
              <label>Describe the issue</label>

              <textarea
                v-model="description"
                rows="5"
                required
                maxlength="1000"
                placeholder="Describe what happened, where it happened, and anything that may help the administration..."
              ></textarea>

              <div class="character-count">
                {{ description.length }}/1000
              </div>
            </div>

          </section>

          <section class="form-card card">

            <div class="form-card-header">
              <div class="form-step">02</div>

              <div>
                <h3>Attach evidence</h3>
                <p>
                  Photos can help verify and resolve the issue faster.
                </p>
              </div>
            </div>

            <div class="field">

              <label>Photos <span>(optional)</span></label>

              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                multiple
                class="hidden-file-input"
                @change="onPhotosPicked"
              />

              <button
                class="upload-button"
                type="button"
                @click="triggerFilePicker"
              >
                <span class="upload-icon">+</span>

                <span>
                  <strong>Add photos</strong>
                  <small>PNG, JPG or WEBP up to 5 MB</small>
                </span>
              </button>

              <p v-if="photosError" class="hint-text">
                {{ photosError }}
              </p>

              <div
                v-if="photos.length > 0"
                class="photo-grid"
              >
                <div
                  v-for="(p, i) in photos"
                  :key="i"
                  class="photo-thumb"
                >
                  <img
                    :src="p.previewUrl"
                    alt="Photo to attach"
                  />

                  <button
                    type="button"
                    class="photo-remove"
                    @click="removePhoto(i)"
                    aria-label="Remove photo"
                  >
                    ×
                  </button>
                </div>
              </div>

            </div>

          </section>

        </div>

        <aside class="complaint-side">

          <section class="location-card card">

            <div class="location-header">

              <div>
                <div class="form-step">03</div>

                <h3>Pin the location</h3>

                <p>
                  Click anywhere on the map or use your current location.
                </p>
              </div>

            </div>

            <div class="map-wrapper">

              <div
                ref="mapContainer"
                class="complaint-map"
              ></div>

              <div class="map-instruction">
                <span>⌖</span>
                Click the map to place the marker
              </div>

            </div>

            <button
              class="btn secondary location-button"
              type="button"
              @click="useMyLocation"
              :disabled="isLocating"
            >
              <span>
                {{ isLocating
                  ? 'Locating…'
                  : coords
                    ? 'Location selected ✓'
                    : 'Use my current location'
                }}
              </span>
            </button>

            <p v-if="locatingError" class="hint-text">
              {{ locatingError }}
            </p>

            <div
              v-if="coords"
              class="coordinates-box"
            >
              <div class="coordinate-icon">
                ✓
              </div>

              <div>
                <strong>Location selected</strong>

                <span>
                  {{ coords.latitude.toFixed(6) }},
                  {{ coords.longitude.toFixed(6) }}
                </span>
              </div>
            </div>

            <div class="field location-address-field">

              <label>Location / Address</label>

              <input
                v-model="address"
                placeholder="Address or landmark"
              />

              <p class="field-help">
                This is automatically filled when you select a point on the map.
              </p>

            </div>

          </section>

        </aside>

      </div>

      <div class="complaint-submit-area">

        <p v-if="error" class="error-text">
          {{ error }}
        </p>

        <div class="submit-info">
          <span class="submit-lock">✓</span>

          <span>
            Your location and complaint details will be securely submitted
            for review.
          </span>
        </div>

        <button
          class="btn complaint-submit"
          type="submit"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? 'Submitting…' : 'Confirm & Submit Complaint' }}
        </button>

      </div>

    </form>

  </div>
</template>