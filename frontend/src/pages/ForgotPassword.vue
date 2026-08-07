<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.requestReset(email.value)
    router.push({ path: '/reset-password', query: { email: email.value } })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-shell">
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
        <h1>Forgot your password?</h1>
        <p>No problem. Enter the email on your account and we'll walk you through resetting it.</p>
      </div>
    </div>

    <div class="auth-panel-right">
      <div class="auth-card-new">
        <p class="auth-eyebrow">Account recovery</p>
        <h2 class="auth-title">Reset Password</h2>

        <form @submit.prevent="submit">
          <div class="field">
            <label>Email</label>
            <input v-model="email" type="email" placeholder="you@example.com" required autocomplete="email" />
          </div>

          <p v-if="error" class="error-text">{{ error }}</p>

          <button class="btn block" type="submit" :disabled="loading">
            {{ loading ? 'Checking...' : 'Continue' }}
          </button>
        </form>

        <p class="switch-link">
          Remembered it? <router-link to="/login">Back to log in</router-link>
        </p>
      </div>
    </div>
  </div>
</template>