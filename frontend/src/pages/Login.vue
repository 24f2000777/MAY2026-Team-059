<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const phone = ref('')
const password = ref('')
const error = ref('')

function submit() {
  error.value = ''
  try {
    auth.login({ phone: phone.value, password: password.value })
    router.push('/login') // will point to role dashboards from Phase 2 onward
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <div class="auth-header">LOG IN</div>
      <div class="auth-body">
        <form @submit.prevent="submit">
          <div class="field">
            <label>Phone Number</label>
            <input v-model="phone" type="text" placeholder="10-digit phone number" required />
          </div>
          <div class="field">
            <label>Password</label>
            <input v-model="password" type="password" placeholder="Password" required />
          </div>
          <p v-if="error" class="error-text">{{ error }}</p>
          <button class="btn block" type="submit">Log In</button>
        </form>
        <p class="switch-link">
          New here? <router-link to="/register">Create an account</router-link>
        </p>
      </div>
    </div>
  </div>
</template>