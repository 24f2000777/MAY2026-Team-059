<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()
const myComplaints = computed(() => store.forCitizen(auth.user.id))

function statusClass(status) {
  return status.toLowerCase().replace(/\s+/g, '-')
}
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <h2>My Complaints</h2>
      <router-link to="/citizen/new" class="btn">+ Report Issue</router-link>
    </div>

    <div v-if="myComplaints.length === 0" class="empty-state">
      You have not filed any complaints yet.
    </div>

    <div v-else class="list-stack">
      <div v-for="c in myComplaints" :key="c.id" class="card">
        <div class="card-row">
          <div>
            <div class="card-title">{{ c.category }}</div>
            <div class="card-meta">{{ c.location }}</div>
          </div>
          <span class="badge" :class="statusClass(c.status)">{{ c.status }}</span>
        </div>
        <div class="card-row" style="margin-top: 12px;">
          <span class="card-meta">Filed {{ new Date(c.createdAt).toLocaleDateString() }}</span>
          <button class="btn secondary" @click="router.push(`/citizen/${c.id}`)">View Details</button>
        </div>
      </div>
    </div>
  </div>
</template>