<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const router = useRouter()
const auth = useAuthStore()

const pending = ref(null)
const code = ref('')
const error = ref('')
const loading = ref(false)
const resent = ref(false)

onMounted(() => {
  const raw = sessionStorage.getItem('cr_pending_registration')
  if (!raw) {
    router.push('/register')
    return
  }
  pending.value = JSON.parse(raw)
})

function verify() {
  error.value = ''
  if (code.value !== pending.value.otp) {
    error.value = 'Incorrect code. Please try again.'
    return
  }
  loading.value = true
  try {
    auth.register({
      name: pending.value.name,
      email: pending.value.email,
      phone: pending.value.phone,
      password: pending.value.password
    })
    sessionStorage.removeItem('cr_pending_registration')
    router.push('/citizen')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function resend() {
  if (!pending.value) return
  const otp = String(Math.floor(100000 + Math.random() * 900000))
  pending.value.otp = otp
  sessionStorage.setItem('cr_pending_registration', JSON.stringify(pending.value))
  resent.value = true
  setTimeout(() => (resent.value = false), 2500)
}
</script>

<template>
  <div class="auth-shell" v-if="pending">
    <div class="auth-panel-left">
      <router-link to="/" class="auth-logo">
        <svg width="30" height="30" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="1" width="30" height="30" rx="9" fill="#16301F" />
        <circle cx="16" cy="12.5" r="5" fill="white" />
        <path d="M7 26c0-5.5 4-9 9-9s9 3.5 9 9" fill="white" />
        <circle cx="24.5" cy="8" r="3" fill="#2F8F5B" stroke="#16301F" stroke-width="1.5" />
        </svg>
        <span>NAGRIK AI</span>
      </router-link>
      <div class="auth-panel-copy">
        <h1>Verify it's you.</h1>
        <p>We've sent a 6-digit code to {{ pending.email }}.</p>
      </div>
    </div>

    <div class="auth-panel-right">
      <div class="auth-card-new">
        <p class="auth-eyebrow">Step 2 of 2</p>
        <h2 class="auth-title">Enter Verification Code</h2>

        <div class="card" style="background: var(--panel-alt); border-style: dashed; margin-bottom: 20px;">
          <p style="font-size: 12px; color: var(--text-dim); margin: 0 0 4px 0;">Demo mode -- no real SMS is sent. Your code is:</p>
          <p style="font-size: 24px; font-weight: 900; letter-spacing: .1em; color: var(--ink); margin: 0;">{{ pending.otp }}</p>
        </div>

        <form @submit.prevent="verify">
          <div class="field">
            <label>6-Digit Code</label>
            <input v-model="code" type="text" maxlength="6" placeholder="000000" required autocomplete="one-time-code" />
          </div>

          <p v-if="error" class="error-text">{{ error }}</p>
          <p v-if="resent" style="color: var(--ok); font-size: 13px; margin-top: -6px; margin-bottom: 12px;">New code sent.</p>

          <button class="btn block" type="submit" :disabled="loading">
            {{ loading ? 'Verifying...' : 'Verify & Create Account' }}
          </button>
        </form>

        <p class="switch-link">
          Didn't get it? <a href="#" @click.prevent="resend" style="color: var(--accent); font-weight: 600;">Resend code</a>
        </p>
      </div>
    </div>
  </div>
</template>