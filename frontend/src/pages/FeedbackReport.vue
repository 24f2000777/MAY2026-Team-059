<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { submitFeedback } from '../api/client'

const auth = useAuthStore()

const subject = ref('')
const message = ref('')
const rating = ref(0)
const submitted = ref(false)

function setRating(n) {
  rating.value = n
}

function submit() {
  submitFeedback({
    userId: auth.user.id,
    userName: auth.user.name,
    subject: subject.value,
    message: message.value,
    rating: rating.value
  })
  submitted.value = true
  subject.value = ''
  message.value = ''
  rating.value = 0
  setTimeout(() => (submitted.value = false), 3000)
}
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>Feedback &amp; Report an Issue</h2>
        <p class="page-intro">Something not working, or an idea for the app? Tell us here.</p>
      </div>
    </div>

    <div class="card" style="max-width: 560px;">
      <div v-if="submitted" class="empty-state" style="border-style: solid; border-color: var(--ok);">
        Thanks, your feedback has been recorded.
      </div>

      <form v-else @submit.prevent="submit">
        <div class="field">
          <label>Subject</label>
          <input v-model="subject" type="text" placeholder="Brief summary" required />
        </div>
        <div class="field">
          <label>Message</label>
          <textarea v-model="message" rows="5" placeholder="Tell us what happened or what you'd like to see" required></textarea>
        </div>
        <div class="field">
          <label>How's your overall experience?</label>
          <div style="display: flex; gap: 6px;">
            <button
              v-for="n in 5" :key="n" type="button"
              @click="setRating(n)"
              :style="{
                width: '38px', height: '38px', borderRadius: '8px', border: '1px solid var(--border)',
                background: n <= rating ? 'var(--accent)' : 'var(--panel-alt)',
                color: n <= rating ? '#fff' : 'var(--text-dim)',
                fontWeight: 700, cursor: 'pointer'
              }"
            >{{ n }}</button>
          </div>
        </div>
        <button class="btn" type="submit">Submit Feedback</button>
      </form>
    </div>
  </div>
</template>