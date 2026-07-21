<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const name = ref('')
const email = ref('')
const phone = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

const phonePattern = /^[0-9]{10}$/

function submit() {
  error.value = ''

  if (!phonePattern.test(phone.value)) {
    error.value = 'Enter a valid 10-digit phone number.'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match.'
    return
  }

  loading.value = true
  try {
    auth.register({ name: name.value, email: email.value, phone: phone.value, password: password.value })
    router.push('/login')
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
        <h1>File it once. Track it always!</h1>
        <p>Create an account to report civic issues with a photo and location, and follow every one through to resolution.</p>
      </div>

      <ul class="auth-feature-list">
        <li><span class="auth-feature-dot"></span> Takes under a minute to sign up</li>
        <li><span class="auth-feature-dot"></span> AI priority scoring on every report</li>
        <li><span class="auth-feature-dot"></span> Full history, always visible to you</li>
      </ul>
    </div>

    <div class="auth-panel-right">
      <div class="auth-card-new">
        <p class="auth-eyebrow">Get started</p>
        <h2 class="auth-title">Create Account</h2>

        <form @submit.prevent="submit">
          <div class="field">
            <label>Full Name</label>
            <input v-model="name" type="text" placeholder="Your name" required autocomplete="name" />
          </div>
          <div class="field">
            <label>Email</label>
            <input v-model="email" type="email" placeholder="you@example.com" required autocomplete="email" />
          </div>
          <div class="field">
            <label>Phone Number</label>
            <input v-model="phone" type="text" placeholder="10-digit phone number" maxlength="10" required autocomplete="tel" />
          </div>
          <div class="field-row">
            <div class="field">
              <label>Password</label>
              <input v-model="password" type="password" placeholder="Choose a password" required minlength="6" autocomplete="new-password" />
            </div>
            <div class="field">
              <label>Confirm Password</label>
              <input v-model="confirmPassword" type="password" placeholder="Re-enter password" required minlength="6" autocomplete="new-password" />
            </div>
          </div>

          <p v-if="error" class="error-text">{{ error }}</p>

          <button class="btn block" type="submit" :disabled="loading">
            {{ loading ? 'Creating account...' : 'Register' }}
          </button>
        </form>

        <p class="switch-link">
          Already have an account? <router-link to="/login">Log in</router-link>
        </p>
      </div>
    </div>
  </div>
</template>