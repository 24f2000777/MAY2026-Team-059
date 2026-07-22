<script setup>
/*Mock reset flow */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref(route.query.email || '')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref(false)

function submit() {
  error.value = ''
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Passwords do not match.'
    return
  }
  try {
    auth.completeReset(email.value, newPassword.value)
    success.value = true
    setTimeout(() => router.push('/login'), 1800)
  } catch (e) {
    error.value = e.message
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
        <h1>Almost there.</h1>
        <p>Choose a new password for {{ email || 'your account' }}.</p>
      </div>
    </div>

    <div class="auth-panel-right">
      <div class="auth-card-new">
        <p class="auth-eyebrow">Account recovery</p>
        <h2 class="auth-title">Set New Password</h2>

        <div v-if="success" class="empty-state" style="padding: 24px;">
          Password updated. Redirecting to log in...
        </div>

        <form v-else @submit.prevent="submit">
          <div class="field">
            <label>Email</label>
            <input v-model="email" type="email" placeholder="you@example.com" required />
          </div>
          <div class="field">
            <label>New Password</label>
            <input v-model="newPassword" type="password" placeholder="New password" required minlength="6" />
          </div>
          <div class="field">
            <label>Confirm New Password</label>
            <input v-model="confirmPassword" type="password" placeholder="Re-enter new password" required minlength="6" />
          </div>

          <p v-if="error" class="error-text">{{ error }}</p>

          <button class="btn block" type="submit">Update Password</button>
        </form>

        <p class="switch-link">
          <router-link to="/login">Back to log in</router-link>
        </p>
      </div>
    </div>
  </div>
</template>