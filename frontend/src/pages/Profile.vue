<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()

const name = ref(auth.user.name)
const phone = ref(auth.user.phone)
const profileError = ref('')
const profileSaved = ref(false)

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSaved = ref(false)

function saveProfile() {
  profileError.value = ''
  try {
    auth.updateProfile({ name: name.value, phone: phone.value })
    profileSaved.value = true
    setTimeout(() => (profileSaved.value = false), 2500)
  } catch (e) {
    profileError.value = e.message
  }
}

function savePassword() {
  passwordError.value = ''
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = 'New passwords do not match.'
    return
  }
  try {
    auth.changePassword(currentPassword.value, newPassword.value)
    passwordSaved.value = true
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    setTimeout(() => (passwordSaved.value = false), 2500)
  } catch (e) {
    passwordError.value = e.message
  }
}
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>My Profile</h2>
        <p class="page-intro">Manage your account details.</p>
      </div>
    </div>

    <div class="grid cols-2">
      <div class="card">
        <h3>Account Details</h3>
        <form @submit.prevent="saveProfile">
          <div class="field"><label>Full Name</label><input v-model="name" type="text" required /></div>
          <div class="field"><label>Email</label><input :value="auth.user.email" type="email" disabled style="opacity: .6;" /></div>
          <div class="field"><label>Phone Number</label><input v-model="phone" type="text" maxlength="10" required /></div>
          <div class="field"><label>Role</label><input :value="auth.user.role" disabled style="opacity: .6; text-transform: capitalize;" /></div>

          <p v-if="profileError" class="error-text">{{ profileError }}</p>
          <p v-if="profileSaved" style="color: var(--ok); font-size: 13px; margin-top: -6px; margin-bottom: 12px;">Profile updated.</p>

          <button class="btn" type="submit">Save Changes</button>
        </form>
      </div>

      <div class="card">
        <h3>Change Password</h3>
        <form @submit.prevent="savePassword">
          <div class="field"><label>Current Password</label><input v-model="currentPassword" type="password" required /></div>
          <div class="field"><label>New Password</label><input v-model="newPassword" type="password" required minlength="6" /></div>
          <div class="field"><label>Confirm New Password</label><input v-model="confirmPassword" type="password" required minlength="6" /></div>

          <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
          <p v-if="passwordSaved" style="color: var(--ok); font-size: 13px; margin-top: -6px; margin-bottom: 12px;">Password updated.</p>

          <button class="btn secondary" type="submit">Update Password</button>
        </form>
      </div>
    </div>
  </div>
</template>