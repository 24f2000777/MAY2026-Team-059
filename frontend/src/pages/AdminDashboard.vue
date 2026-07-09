<script setup>
import { useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'

const store = useComplaintStore()
const router = useRouter()
</script>

<template>
  <div class="app-content">
    <h2>All Complaints</h2>
    <ul>
      <li v-for="c in store.complaints" :key="c.id">
        {{ c.category }} — {{ c.location }} — {{ c.status }}
        <button class="btn secondary" @click="router.push(`/admin/assign/${c.id}`)">Assign</button>
      </li>
    </ul>
  </div>
</template>