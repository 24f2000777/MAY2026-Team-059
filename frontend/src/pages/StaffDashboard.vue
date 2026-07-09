<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()
const myTasks = computed(() => store.forStaff(auth.user.id))
</script>

<template>
  <div class="app-content">
    <h2>My Assigned Tasks</h2>
    <ul>
      <li v-for="c in myTasks" :key="c.id">
        {{ c.category }} — Priority {{ c.priorityScore }}
        <button class="btn secondary" @click="router.push(`/staff/${c.id}`)">Update</button>
      </li>
    </ul>
  </div>
</template>