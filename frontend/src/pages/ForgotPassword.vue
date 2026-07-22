<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const error = ref('')
const loading = ref(false)

function submit() {
  error.value = ''
  loading.value = true
  try {
    auth.requestReset(email.value)
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
        <span style="font-size: 20px; font-weight: 900;">Nagrik<span style="color: var(--accent);">AI</span></span>
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