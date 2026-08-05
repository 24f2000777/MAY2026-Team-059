<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { createStaffAccount, listOfficers } from '../api/complaintApi'

const auth = useAuthStore()
const router = useRouter()

const officers = ref([])
const loading = ref(true)
const loadError = ref('')

const name = ref('')
const phone = ref('')
const email = ref('')
const password = ref('')
const formError = ref('')
const successMessage = ref('')
const saving = ref(false)

const phonePattern = /^[0-9]{10}$/

async function load() {
  loadError.value = ''
  try {
    const data = await listOfficers({ accessToken: auth.accessToken })
    officers.value = data.officers
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function submit() {
  formError.value = ''
  successMessage.value = ''

  if (!phonePattern.test(phone.value)) {
    formError.value = 'Enter a valid 10-digit phone number.'
    return
  }
  if (password.value.length < 8) {
    formError.value = 'Password must be at least 8 characters.'
    return
  }

  saving.value = true
  try {
    await createStaffAccount({
      name: name.value,
      phone: phone.value,
      email: email.value,
      password: password.value,
      accessToken: auth.accessToken
    })
    successMessage.value = `${name.value} can now log in as staff.`
    name.value = ''
    phone.value = ''
    email.value = ''
    password.value = ''
    await load()
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="app-content">
    <button class="btn secondary" @click="router.push('/admin')">&larr; Back</button>

    <div class="card">
      <h2>Create Staff Account</h2>
      <p class="page-intro">
        Staff accounts can't self-register, they only ever come from here. The account is active immediately.
      </p>

      <form @submit.prevent="submit">
        <div class="field">
          <label>Full Name</label>
          <input v-model="name" type="text" placeholder="Staff member's name" required autocomplete="name" />
        </div>
        <div class="field-row">
          <div class="field">
            <label>Phone Number</label>
            <input v-model="phone" type="text" placeholder="10-digit phone number" maxlength="10" required autocomplete="tel" />
          </div>
          <div class="field">
            <label>Email</label>
            <input v-model="email" type="email" placeholder="staff@example.com" required autocomplete="email" />
          </div>
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" placeholder="At least 8 characters" required minlength="8" autocomplete="new-password" />
        </div>

        <p v-if="formError" class="error-text">{{ formError }}</p>
        <p v-if="successMessage" class="success-text">{{ successMessage }}</p>

        <button class="btn" type="submit" :disabled="saving">{{ saving ? 'Creating...' : 'Create Staff Account' }}</button>
      </form>
    </div>

    <div class="card">
      <h3>Existing Staff</h3>
      <p v-if="loadError" class="error-text">{{ loadError }}</p>
      <p v-else-if="loading" class="page-intro">Loading...</p>
      <div v-else-if="officers.length === 0" class="empty-state">No staff accounts yet, create the first one above.</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in officers" :key="o.id">
              <td>{{ o.name }}</td>
              <td>{{ o.email }}</td>
              <td>{{ o.phone }}</td>
              <td>{{ o.is_active ? 'Active' : 'Inactive' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.success-text { color: var(--success, #2f8f5b); font-size: 13px; margin: 4px 0 12px; }
</style>
