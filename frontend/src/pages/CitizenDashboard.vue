<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'
import ComplaintCard from '../components/ComplaintCard.vue'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()
const myComplaints = computed(() => store.forCitizen(auth.user.id).sort((a, b) => b.createdAt - a.createdAt))
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <h2>My Complaints</h2>
      <router-link to="/citizen/new" class="btn">+ Report Issue</router-link>
    </div>
    <div v-if="myComplaints.length === 0" class="empty-state">You haven't filed any complaints yet.</div>
    <div v-else class="grid cols-2">
      <ComplaintCard v-for="c in myComplaints" :key="c.id" :complaint="c">
        <template #actions>
          <button class="btn secondary" @click="router.push(`/citizen/${c.id}`)">View details</button>
        </template>
      </ComplaintCard>
    </div>
  </div>
</template>
<style scoped>
.header-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
</style>