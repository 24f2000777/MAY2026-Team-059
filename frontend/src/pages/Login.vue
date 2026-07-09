<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref('')

const homeForRole = { citizen: '/citizen', staff: '/staff', admin: '/admin' }

function submit() {
  error.value = ''
  try {
    const user = auth.login({ email: email.value, password: password.value })
    router.push(homeForRole[user.role])
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
            <label>Email</label>
            <input v-model="email" type="email" placeholder="you@example.com" required />
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