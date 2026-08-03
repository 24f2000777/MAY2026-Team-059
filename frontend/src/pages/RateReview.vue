<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getComplaint, getFeedback, submitFeedback } from '../api/complaintApi'
import { categoryLabel } from '../constants/categories'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const complaint = ref(null)
const existingFeedback = ref(null)
const loading = ref(true)
const loadError = ref('')

const rating = ref(0)
const review = ref('')
const saved = ref(false)
const submitError = ref('')

function setRating(n) {
  rating.value = n
}

async function submit() {
  if (rating.value === 0) return
  submitError.value = ''
  try {
    await submitFeedback({ id: route.params.id, score: rating.value, feedback: review.value || undefined, accessToken: auth.accessToken })
    saved.value = true
  } catch (e) {
    submitError.value = e.message
  }
}

onMounted(async () => {
  try {
    complaint.value = await getComplaint({ id: route.params.id, accessToken: auth.accessToken })
    if (complaint.value.status === 'resolved' || complaint.value.status === 'closed') {
      existingFeedback.value = await getFeedback({ id: route.params.id, accessToken: auth.accessToken })
      if (existingFeedback.value) {
        rating.value = existingFeedback.value.score
        review.value = existingFeedback.value.feedback || ''
        saved.value = true
      }
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
})
</script>

<template>
  <div class="app-content" v-if="loading">
    <p class="page-intro">Loading...</p>
  </div>

  <div class="app-content" v-else-if="loadError">
    <p class="error-text">{{ loadError }}</p>
  </div>

  <div class="app-content" v-else-if="complaint">
    <button class="btn secondary" @click="router.push(`/citizen/${complaint.id}`)">&larr; Back</button>

    <div class="card" style="max-width: 560px;">
      <div class="header-row" style="margin-bottom: 12px;">
        <h2>Rate the Resolution</h2>
        <StatusBadge :value="complaint.status" />
      </div>
      <p class="page-intro" style="margin-top: 0;">{{ categoryLabel(complaint.category) }} at {{ complaint.location_text || 'no location recorded' }}</p>

      <div v-if="complaint.status !== 'resolved' && !saved" class="empty-state">
        Feedback can only be submitted once a complaint is resolved.
      </div>

      <div v-else-if="saved" class="empty-state" style="border-style: solid; border-color: var(--ok);">
        Thanks for your feedback. Submitting it also closed this complaint.
      </div>

      <form v-else @submit.prevent="submit">
        <p v-if="submitError" class="error-text">{{ submitError }}</p>
        <div class="field">
          <label>How satisfied are you with the resolution?</label>
          <div style="display: flex; gap: 8px;">
            <button
              v-for="n in 5" :key="n" type="button"
              @click="setRating(n)"
              :style="{
                width: '42px', height: '42px', borderRadius: '50%', border: '1px solid var(--border)',
                background: n <= rating ? 'var(--warn)' : 'var(--panel-alt)',
                color: n <= rating ? '#fff' : 'var(--text-dim)',
                fontWeight: 700, cursor: 'pointer', fontSize: '16px'
              }"
            >&#9733;</button>
          </div>
        </div>

        <div class="field">
          <label>Add a comment (optional)</label>
          <textarea v-model="review" rows="4" placeholder="How did it go?"></textarea>
        </div>

        <button class="btn" type="submit" :disabled="rating === 0">Submit Rating</button>
      </form>
    </div>
  </div>

  <div v-else class="empty-state">Complaint not found.</div>
</template>
