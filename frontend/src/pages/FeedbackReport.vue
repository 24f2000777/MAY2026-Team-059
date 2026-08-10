<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { submitFeedback } from '../api/client'

const auth = useAuthStore()

const subject = ref('')
const message = ref('')
const rating = ref(0)
const submitted = ref(false)
const hoveredRating = ref(0)

const messageLength = computed(() => message.value.length)

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

  setTimeout(() => {
    submitted.value = false
  }, 4000)
}
</script>

<template>
  <div class="app-content feedback-page">

    <!-- Page Header -->
    <div class="feedback-header">
      <div>
        <div class="feedback-eyebrow">
          <span class="feedback-eyebrow-dot"></span>
          Citizen Support
        </div>

        <h2>Feedback &amp; Report an Issue</h2>

        <p class="page-intro">
          Help us improve your experience. Tell us what went wrong,
          share an idea, or simply let us know how we're doing.
        </p>
      </div>
    </div>

    <!-- Main Feedback Layout -->
    <div class="feedback-layout">

      <!-- Left Information Panel -->
      <aside class="feedback-info">

        <div class="feedback-info-icon">
          💬
        </div>

        <h3>Your voice matters.</h3>

        <p>
          Every piece of feedback helps us make Nagrik Saathi
          more useful, accessible and reliable for citizens.
        </p>

        <div class="feedback-points">

          <div class="feedback-point">
            <span class="feedback-point-icon">✓</span>
            <div>
              <strong>Report problems</strong>
              <span>Tell us when something isn't working.</span>
            </div>
          </div>

          <div class="feedback-point">
            <span class="feedback-point-icon">＋</span>
            <div>
              <strong>Share ideas</strong>
              <span>Suggest features that could help citizens.</span>
            </div>
          </div>

          <div class="feedback-point">
            <span class="feedback-point-icon">★</span>
            <div>
              <strong>Rate your experience</strong>
              <span>Let us know how we're doing.</span>
            </div>
          </div>

        </div>

        <div class="feedback-info-footer">
          <span class="feedback-footer-dot"></span>
          Your feedback is securely recorded
        </div>

      </aside>

      <!-- Form Card -->
      <div class="feedback-card">

        <!-- Success State -->
        <div v-if="submitted" class="feedback-success">

          <div class="success-icon">
            ✓
          </div>

          <h3>Thank you for your feedback!</h3>

          <p>
            Your response has been recorded successfully.
            We'll use it to make the experience better.
          </p>

          <button
            type="button"
            class="btn secondary success-button"
            @click="submitted = false"
          >
            Submit another response
          </button>

        </div>

        <!-- Form -->
        <form v-else @submit.prevent="submit">

          <div class="form-heading">
            <div>
              <h3>Send us your feedback</h3>
              <p>It only takes a minute.</p>
            </div>

            <span class="required-note">
              * Required
            </span>
          </div>

          <!-- Subject -->
          <div class="field">
            <label for="feedback-subject">
              Subject <span>*</span>
            </label>

            <input
              id="feedback-subject"
              v-model="subject"
              type="text"
              placeholder="e.g. Unable to track my complaint"
              required
            />
          </div>

          <!-- Message -->
          <div class="field">
            <div class="field-label-row">
              <label for="feedback-message">
                Message <span>*</span>
              </label>

              <span class="character-count">
                {{ messageLength }}/1000
              </span>
            </div>

            <textarea
              id="feedback-message"
              v-model="message"
              rows="6"
              maxlength="1000"
              placeholder="Tell us what happened, what you expected, or what you'd like to see..."
              required
            ></textarea>
          </div>

          <!-- Rating -->
          <div class="rating-section">

            <div class="rating-heading">
              <label>Overall experience</label>

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

            <div
              class="rating-stars"
              @mouseleave="hoveredRating = 0"
            >
              <button
                v-for="n in 5"
                :key="n"
                type="button"
                class="rating-star"
                :class="{
                  active: n <= (hoveredRating || rating)
                }"
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

          <!-- Submit -->
          <div class="form-footer">

            <p class="privacy-note">
              <span>🔒</span>
              Your feedback is associated with your account.
            </p>

            <button
              class="btn feedback-submit"
              type="submit"
              :disabled="!subject || !message"
            >
              Submit Feedback
              <span class="submit-arrow">→</span>
            </button>

          </div>

        </form>

      </div>

    </div>

  </div>
</template>

<style scoped>

.feedback-page {
  max-width: 1180px;
  padding-top: 36px;
}


/* Header */

.feedback-header {
  margin-bottom: 28px;
}

.feedback-eyebrow {
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

.feedback-eyebrow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px var(--accent-glow);
}

.feedback-header h2 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: -.02em;
  color: var(--ink);
}

.feedback-header .page-intro {
  margin: 0;
  max-width: 650px;
  line-height: 1.6;
}


/* Main layout */

.feedback-layout {
  display: grid;
  grid-template-columns: 0.82fr 1.35fr;
  gap: 20px;
  align-items: stretch;
}


/* left panel */

.feedback-info {
  position: relative;
  overflow: hidden;

  display: flex;
  flex-direction: column;

  min-height: 590px;
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

.feedback-info::after {
  content: '';
  position: absolute;

  width: 180px;
  height: 180px;

  right: -80px;
  bottom: -80px;

  border-radius: 50%;

  border: 35px solid rgba(255,255,255,.035);
}

.feedback-info-icon {
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

.feedback-info h3 {
  margin: 0 0 12px;

  font-size: 27px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: -.02em;
}

.feedback-info > p {
  margin: 0;

  max-width: 350px;

  color: rgba(255,255,255,.68);
  font-size: 14px;
  line-height: 1.7;
}


/* Points */

.feedback-points {
  display: flex;
  flex-direction: column;
  gap: 20px;

  margin-top: 34px;
}

.feedback-point {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.feedback-point-icon {
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

.feedback-point div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.feedback-point strong {
  font-size: 13px;
  font-weight: 750;
}

.feedback-point span:not(.feedback-point-icon) {
  color: rgba(255,255,255,.58);
  font-size: 12px;
  line-height: 1.45;
}


/* Footer */

.feedback-info-footer {
  display: flex;
  align-items: center;
  gap: 8px;

  margin-top: auto;
  padding-top: 28px;

  color: rgba(255,255,255,.48);

  font-size: 11px;
  font-weight: 600;
}

.feedback-footer-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 4px rgba(42,157,143,.14);
}


/* Form Card */

.feedback-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);

  padding: 32px;

  box-shadow: 0 8px 26px rgba(22, 48, 31, .06);
}


/* Form heading */

.form-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

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

.required-note {
  padding-top: 3px;

  color: var(--text-dim);

  font-size: 11px;
}


/* Form fields */

.feedback-card .field {
  margin-bottom: 22px;
}

.feedback-card .field label {
  color: var(--ink);
  font-size: 11px;
}

.feedback-card .field label span {
  color: var(--danger);
}

.feedback-card input,
.feedback-card textarea {
  background: var(--bg-soft);
}

.feedback-card textarea {
  resize: vertical;
  min-height: 145px;
  line-height: 1.55;
}

.feedback-card input::placeholder,
.feedback-card textarea::placeholder {
  color: #8A9586;
}


/* Character count */

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  margin-bottom: 6px;
}

.field-label-row label {
  margin-bottom: 0 !important;
}

.character-count {
  color: var(--text-dim);
  font-size: 11px;
}


/* rating */

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


/* footer */

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

.feedback-submit {
  min-width: 170px;
}

.submit-arrow {
  font-size: 17px;
  transition: transform .15s ease;
}

.feedback-submit:hover .submit-arrow {
  transform: translateX(3px);
}


/* success */

.feedback-success {
  min-height: 520px;

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  text-align: center;

  padding: 40px;
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

.feedback-success h3 {
  margin: 0 0 8px;

  color: var(--ink);

  font-size: 23px;
  font-weight: 850;
}

.feedback-success p {
  max-width: 400px;

  margin: 0 0 24px;

  color: var(--text-dim);

  font-size: 14px;
  line-height: 1.6;
}

.success-button {
  text-transform: none;
  letter-spacing: 0;
}


/* Responsive */

@media (max-width: 820px) {

  .feedback-layout {
    grid-template-columns: 1fr;
  }

  .feedback-info {
    min-height: auto;
    padding: 26px;
  }

  .feedback-info-footer {
    margin-top: 28px;
  }

}

@media (max-width: 600px) {

  .feedback-page {
    padding: 22px 16px;
  }

  .feedback-header h2 {
    font-size: 25px;
  }

  .feedback-card {
    padding: 22px 18px;
  }

  .form-heading {
    flex-direction: column;
    gap: 6px;
  }

  .form-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .feedback-submit {
    width: 100%;
  }

  .rating-star {
    width: 38px;
    height: 38px;
  }

}
</style>
