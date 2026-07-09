<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()

const category = ref('Water Leak')
const description = ref('')
const location = ref('')
const severity = ref('Medium')

function submit() {
  store.submit({
    citizenId: auth.user.id, citizenName: auth.user.name,
    category: category.value, description: description.value,
    location: location.value, severity: severity.value, pin: { x: 50, y: 50 }
  })
  router.push('/citizen')
}
</script>

<template>
  <div class="app-content">
    <h2>Report an Issue</h2>
    <form @submit.prevent="submit">
      <select v-model="category">
        <option>Water Leak</option><option>Pothole</option><option>Smog / Air Quality</option>
      </select>
      <input v-model="location" placeholder="Location" required />
      <textarea v-model="description" placeholder="Describe the issue" required></textarea>
      <select v-model="severity"><option>Low</option><option>Medium</option><option>High</option></select>
      <button class="btn" type="submit">Submit</button>
    </form>
  </div>
</template>