<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

const name = ref('')
const phone = ref('')
const password = ref('')
const error = ref('')

function submit() {
  error.value = ''
  try {
    auth.register({ name: name.value, phone: phone.value, password: password.value })
    router.push('/login')
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <div class="auth-header">CREATE ACCOUNT</div>
      <div class="auth-body">
        <form @submit.prevent="submit">
          <div class="field">
            <label>Full Name</label>
            <input v-model="name" type="text" placeholder="Your name" required />
          </div>
          <div class="field">
            <label>Phone Number</label>
            <input v-model="phone" type="text" placeholder="10-digit phone number" required />
          </div>
          <div class="field">
            <label>Password</label>
            <input v-model="password" type="password" placeholder="Choose a password" required minlength="6" />
          </div>
          <p v-if="error" class="error-text">{{ error }}</p>
          <button class="btn block" type="submit">Register</button>
        </form>
        <p class="switch-link">
          Already have an account? <router-link to="/login">Log in</router-link>
        </p>
      </div>
    </div>
  </div>
</template>