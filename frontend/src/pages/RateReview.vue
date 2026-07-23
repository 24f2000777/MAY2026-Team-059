<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()

const complaint = computed(() => store.byId(route.params.id))
const rating = ref(complaint.value?.rating || 0)
const review = ref(complaint.value?.review || '')
const saved = ref(false)

function setRating(n) {
  rating.value = n
}

function submit() {
  if (rating.value === 0) return
  store.rate(route.params.id, rating.value, review.value)
  saved.value = true
}
</script>

<template>
  <div class="app-content" v-if="complaint">
    <button class="btn secondary" @click="router.push(`/citizen/${complaint.id}`)">&larr; Back</button>

    <div class="card" style="max-width: 560px;">
      <div class="header-row" style="margin-bottom: 12px;">
        <h2>Rate the Resolution</h2>
        <StatusBadge :value="complaint.status" />
      </div>
      <p class="page-intro" style="margin-top: 0;">{{ complaint.category }} at {{ complaint.location }}</p>

      <div v-if="saved" class="empty-state" style="border-style: solid; border-color: var(--ok);">
        Thanks for your feedback.
      </div>

      <form v-else @submit.prevent="submit">
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