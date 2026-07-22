<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'
import ComplaintCard from '../components/ComplaintCard.vue'

const auth = useAuthStore()
const store = useComplaintStore()
const router = useRouter()
const myTasks = computed(() => store.forStaff(auth.user.id).sort((a, b) => b.priorityScore - a.priorityScore))
</script>

<template>
  <div class="app-content">
    <h2>My Assigned Tasks</h2>
    <div v-if="myTasks.length === 0" class="empty-state">No complaints assigned to you right now.</div>
    <div v-else class="grid cols-2">
      <ComplaintCard v-for="c in myTasks" :key="c.id" :complaint="c" show-priority>
        <template #actions><button class="btn secondary" @click="router.push(`/staff/${c.id}`)">Update task</button></template>
      </ComplaintCard>
    </div>
  </div>
</template>