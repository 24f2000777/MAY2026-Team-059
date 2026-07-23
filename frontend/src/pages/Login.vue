<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const homeForRole = { citizen: '/citizen', staff: '/staff', admin: '/admin' }

function submit() {
  error.value = ''
  loading.value = true
  try {
    const user = auth.login({ email: email.value, password: password.value })
    router.push(homeForRole[user.role])
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
        <h1>Welcome back!</h1>
        <p>Track every complaint you have filed, see live status updates, and know exactly when your issue gets resolved.</p>
      </div>

      <ul class="auth-feature-list">
        <li><span class="auth-feature-dot"></span> Real-time status on every complaint</li>
        <li><span class="auth-feature-dot"></span> Direct routing to the right department</li>
        <li><span class="auth-feature-dot"></span> A record you can point to, always</li>
      </ul>
    </div>

    <div class="auth-panel-right">
      <div class="auth-card-new">
        <p class="auth-eyebrow">Sign in to your account</p>
        <h2 class="auth-title">Log In</h2>

        <form @submit.prevent="submit">
          <div class="field">
            <label>Email</label>
            <input v-model="email" type="email" placeholder="you@example.com" required autocomplete="email" />
          </div>
          <div class="field">
            <label>Password</label>
            <input v-model="password" type="password" placeholder="Password" required autocomplete="current-password" />
          </div>
          <p style="text-align: right; margin: -8px 0 16px 0;">
          <router-link to="/forgot-password" style="font-size: 12px; color: var(--accent); text-decoration: none; font-weight: 600;">Forgot password?</router-link>
          </p>
          <p v-if="error" class="error-text">{{ error }}</p>

          <button class="btn block" type="submit" :disabled="loading">
            {{ loading ? 'Logging in...' : 'Log In' }}
          </button>
        </form>

        <p class="switch-link">
          New here? <router-link to="/register">Create an account</router-link>
        </p>
      </div>
    </div>
  </div>
</template>