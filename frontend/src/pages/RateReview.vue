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
const hoveredRating = ref(0)
const review = ref('')
const saved = ref(false)
const submitting = ref(false)
const submitError = ref('')

function setRating(n) {
  rating.value = n
}

async function submit() {
  if (rating.value === 0) return
  submitting.value = true
  submitError.value = ''
  try {
    await submitFeedback({ id: route.params.id, score: rating.value, feedback: review.value || undefined, accessToken: auth.accessToken })
    saved.value = true
    // Submitting feedback auto-closes the complaint server-side, keep
    // the badge on this page in sync rather than leaving it showing
    // the pre-submit "resolved" status until the next navigation.
    complaint.value = { ...complaint.value, status: 'closed' }
  } catch (e) {
    submitError.value = e.message
  } finally {
    submitting.value = false
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
  <div class="app-content rate-page">

    <p v-if="loading" class="page-intro">Loading...</p>

    <p v-else-if="loadError" class="error-text">{{ loadError }}</p>

    <template v-else-if="complaint">

      <button class="btn secondary back-btn" @click="router.push(`/citizen/${complaint.id}`)">
        &larr; Back
      </button>

      <!-- Header -->
      <div class="rate-header">
        <div>
          <div class="rate-eyebrow">
            <span class="rate-eyebrow-dot"></span>
            Resolution Feedback
          </div>

          <h2>Rate the Resolution</h2>

          <p class="page-intro">
            {{ categoryLabel(complaint.category) }} at {{ complaint.location_text || 'no location recorded' }}
          </p>
        </div>

        <StatusBadge :value="complaint.status" />
      </div>

      <!-- Main layout -->
      <div class="rate-layout">

        <!-- Left info panel -->
        <aside class="rate-info">

          <div class="rate-info-icon">
            ★
          </div>

          <h3>Let us know how it went.</h3>

          <p>
            Your rating confirms the issue was actually fixed, and
            helps us hold departments accountable for the work.
          </p>

          <div class="rate-points">

            <div class="rate-point">
              <span class="rate-point-icon">✓</span>
              <div>
                <strong>Confirm the fix</strong>
                <span>Tell us whether the issue was genuinely resolved.</span>
              </div>
            </div>

            <div class="rate-point">
              <span class="rate-point-icon">★</span>
              <div>
                <strong>Rate the experience</strong>
                <span>How satisfied you were with how it was handled.</span>
              </div>
            </div>

            <div class="rate-point">
              <span class="rate-point-icon">◆</span>
              <div>
                <strong>Closes the complaint</strong>
                <span>Submitting your rating marks this complaint closed.</span>
              </div>
            </div>

          </div>

          <div class="rate-info-footer">
            <span class="rate-footer-dot"></span>
            Your rating is tied to this complaint
          </div>

        </aside>

        <!-- Form card -->
        <div class="rate-card">

          <!-- Not resolved yet -->
          <div v-if="complaint.status !== 'resolved' && !saved" class="rate-empty">
            <div class="rate-empty-icon">◷</div>
            <h3>Not resolved yet</h3>
            <p>Feedback can only be submitted once this complaint is marked resolved.</p>
          </div>

          <!-- Already rated -->
          <div v-else-if="saved" class="rate-success">
            <div class="success-icon">✓</div>
            <h3>Thanks for your feedback</h3>
            <p>
              You rated this resolution {{ rating }} / 5.
              Submitting it also closed this complaint.
            </p>
            <button
              type="button"
              class="btn secondary"
              @click="router.push(`/citizen/${complaint.id}`)"
            >
              Back to Complaint
            </button>
          </div>

          <!-- Form -->
          <form v-else @submit.prevent="submit">

            <div class="form-heading">
              <div>
                <h3>Rate this resolution</h3>
                <p>Your feedback closes the loop on this complaint.</p>
              </div>
            </div>

            <p v-if="submitError" class="error-text">{{ submitError }}</p>

            <div class="rating-section">

              <div class="rating-heading">
                <label>How satisfied are you with the resolution?</label>

                <span v-if="rating" class="rating-label">
                  {{
                    rating === 1 ? 'Very poor' :
                    rating === 2 ? 'Poor' :
                    rating === 3 ? 'Okay' :
                    rating === 4 ? 'Good' :
                    'Excellent'
                  }}
                </span>
              </div>

              <div class="rating-stars" @mouseleave="hoveredRating = 0">
                <button
                  v-for="n in 5"
                  :key="n"
                  type="button"
                  class="rating-star"
                  :class="{ active: n <= (hoveredRating || rating) }"
                  :aria-label="`Rate ${n} out of 5`"
                  @mouseenter="hoveredRating = n"
                  @click="setRating(n)"
                >
                  ★
                </button>
              </div>

              <div class="rating-scale">
                <span>Not satisfied</span>
                <span>Very satisfied</span>
              </div>

            </div>

            <div class="field">
              <label for="rate-comment">
                Add a comment
                <span class="optional-note">Optional</span>
              </label>

              <textarea
                id="rate-comment"
                v-model="review"
                rows="5"
                placeholder="How did it go?"
              ></textarea>
            </div>

            <div class="form-footer">
              <p class="privacy-note">
                <span>🔒</span>
                Your rating is associated with your account.
              </p>

              <button
                class="btn rate-submit"
                type="submit"
                :disabled="rating === 0 || submitting"
              >
                {{ submitting ? 'Submitting...' : 'Submit Rating' }}
                <span v-if="!submitting" class="submit-arrow">→</span>
              </button>
            </div>

          </form>

        </div>

      </div>

    </template>

    <p v-else class="empty-state">Complaint not found.</p>

  </div>
</template>

<style scoped>

.rate-page {
  max-width: 1180px;
  padding-top: 36px;
}

.back-btn {
  margin-bottom: 24px;
}


/* Header */

.rate-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;

  margin-bottom: 28px;
}

.rate-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .09em;
}

.rate-eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-glow);
}

.rate-header h2 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: -.02em;
  color: var(--ink);
}

.rate-header .page-intro {
  margin: 0;
  max-width: 650px;
  line-height: 1.6;
}


/* Main layout */

.rate-layout {
  display: grid;
  grid-template-columns: 0.82fr 1.35fr;
  gap: 20px;
  align-items: stretch;
}


/* Left panel */

.rate-info {
  position: relative;
  overflow: hidden;

  display: flex;
  flex-direction: column;

  min-height: 560px;
  padding: 32px;

  color: #fff;

  background:
    radial-gradient(
      circle at 100% 0%,
      rgba(255,255,255,.09),
      transparent 34%
    ),
    linear-gradient(
      145deg,
      var(--ink) 0%,
      var(--ink-soft) 100%
    );

  border-radius: var(--radius-lg);
  box-shadow: 0 10px 28px rgba(22, 48, 31, .10);
}

.rate-info::after {
  content: '';
  position: absolute;

  width: 180px;
  height: 180px;

  right: -80px;
  bottom: -80px;

  border-radius: 50%;

  border: 35px solid rgba(255,255,255,.035);
}

.rate-info-icon {
  width: 58px;
  height: 58px;

  display: flex;
  align-items: center;
  justify-content: center;

  margin-bottom: 26px;

  background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 16px;

  font-size: 25px;
}

.rate-info h3 {
  margin: 0 0 12px;

  font-size: 27px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: -.02em;
}

.rate-info > p {
  margin: 0;

  max-width: 350px;

  color: rgba(255,255,255,.68);
  font-size: 14px;
  line-height: 1.7;
}


/* Points */

.rate-points {
  display: flex;
  flex-direction: column;
  gap: 20px;

  margin-top: 34px;
}

.rate-point {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.rate-point-icon {
  width: 30px;
  height: 30px;

  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 9px;

  background: rgba(255,255,255,.10);
  color: #fff;

  font-size: 14px;
  font-weight: 800;
}

.rate-point div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.rate-point strong {
  font-size: 13px;
  font-weight: 750;
}

.rate-point span:not(.rate-point-icon) {
  color: rgba(255,255,255,.58);
  font-size: 12px;
  line-height: 1.45;
}


/* Footer */

.rate-info-footer {
  display: flex;
  align-items: center;
  gap: 8px;

  margin-top: auto;
  padding-top: 28px;

  color: rgba(255,255,255,.48);

  font-size: 11px;
  font-weight: 600;
}

.rate-footer-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 4px rgba(42,157,143,.14);
}


/* Form card */

.rate-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);

  padding: 32px;

  box-shadow: 0 8px 26px rgba(22, 48, 31, .06);
}


/* Form heading */

.form-heading {
  padding-bottom: 22px;
  margin-bottom: 24px;

  border-bottom: 1px solid var(--border);
}

.form-heading h3 {
  margin: 0 0 4px;

  color: var(--ink);

  font-size: 20px;
  font-weight: 850;
}

.form-heading p {
  margin: 0;

  color: var(--text-dim);
  font-size: 13px;
}


/* Fields */

.rate-card .field {
  margin: 22px 0 0;
}

.rate-card .field label {
  display: flex;
  align-items: center;
  gap: 8px;

  color: var(--ink);
  font-size: 11px;
}

.optional-note {
  color: var(--text-dim);
  font-weight: 500;
  text-transform: none;
}

.rate-card textarea {
  background: var(--bg-soft);
  resize: vertical;
  min-height: 110px;
  line-height: 1.55;
}

.rate-card textarea::placeholder {
  color: #8A9586;
}


/* Rating */

.rating-section {
  margin-top: 6px;
  padding: 20px;

  background: var(--panel-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.rating-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rating-heading label {
  margin: 0;
  color: var(--ink);
  font-size: 12px;
  font-weight: 750;
}

.rating-label {
  color: var(--accent);
  font-size: 12px;
  font-weight: 750;
}

.rating-stars {
  display: flex;
  gap: 4px;
  margin-top: 10px;
}

.rating-star {
  width: 40px;
  height: 40px;

  padding: 0;

  border: 1px solid var(--border);
  border-radius: 9px;

  background: var(--panel);

  color: #C7D2C4;

  font-size: 22px;
  line-height: 1;

  cursor: pointer;

  transition:
    transform .15s ease,
    background .15s ease,
    color .15s ease,
    border-color .15s ease;
}

.rating-star:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
}

.rating-star.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;

  box-shadow: 0 4px 10px var(--accent-glow);
}

.rating-scale {
  display: flex;
  justify-content: space-between;

  margin-top: 7px;

  color: var(--text-dim);
  font-size: 10px;
}


/* Footer */

.form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  margin-top: 24px;
  padding-top: 20px;

  border-top: 1px solid var(--border);
}

.privacy-note {
  display: flex;
  align-items: center;
  gap: 6px;

  margin: 0;

  color: var(--text-dim);
  font-size: 11px;
}

.privacy-note span {
  font-size: 12px;
}

.rate-submit {
  min-width: 170px;
}

.submit-arrow {
  font-size: 17px;
  transition: transform .15s ease;
}

.rate-submit:hover .submit-arrow {
  transform: translateX(3px);
}


/* Empty / success states */

.rate-empty,
.rate-success {
  min-height: 480px;

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  text-align: center;

  padding: 40px;
}

.rate-empty-icon {
  width: 60px;
  height: 60px;

  display: flex;
  align-items: center;
  justify-content: center;

  margin-bottom: 18px;

  border-radius: 50%;

  background: var(--panel-alt);
  border: 1px solid var(--border);

  color: var(--text-dim);

  font-size: 26px;
}

.rate-empty h3,
.rate-success h3 {
  margin: 0 0 8px;

  color: var(--ink);

  font-size: 23px;
  font-weight: 850;
}

.rate-empty p,
.rate-success p {
  max-width: 400px;

  margin: 0 0 24px;

  color: var(--text-dim);

  font-size: 14px;
  line-height: 1.6;
}

.success-icon {
  width: 72px;
  height: 72px;

  display: flex;
  align-items: center;
  justify-content: center;

  margin-bottom: 20px;

  border-radius: 50%;

  background: rgba(42,157,143,.12);
  border: 1px solid rgba(42,157,143,.22);

  color: var(--ok);

  font-size: 30px;
  font-weight: 800;
}


/* Responsive */

@media (max-width: 820px) {

  .rate-layout {
    grid-template-columns: 1fr;
  }

  .rate-info {
    min-height: auto;
    padding: 26px;
  }

  .rate-info-footer {
    margin-top: 28px;
  }

}

@media (max-width: 600px) {

  .rate-page {
    padding: 22px 16px;
  }

  .rate-header {
    flex-direction: column;
    gap: 12px;
  }

  .rate-header h2 {
    font-size: 25px;
  }

  .rate-card {
    padding: 22px 18px;
  }

  .form-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .rate-submit {
    width: 100%;
  }

  .rating-star {
    width: 38px;
    height: 38px;
  }

}
</style>
