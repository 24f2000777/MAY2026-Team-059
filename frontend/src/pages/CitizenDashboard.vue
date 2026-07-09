<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()
const myComplaints = computed(() => store.forCitizen(auth.user.id))
</script>

<template>
  <div class="app-content">
    <h2>My Complaints</h2>
    <router-link to="/citizen/new" class="btn">+ Report Issue</router-link>
    <ul>
      <li v-for="c in myComplaints" :key="c.id">
        {{ c.category }} — {{ c.status }}
        <button class="btn secondary" @click="router.push(`/citizen/${c.id}`)">View</button>
      </li>
    </ul>
  </div>
</template>