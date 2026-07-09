<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()
const complaint = computed(() => store.byId(route.params.id))
</script>

<template>
  <div class="app-content" v-if="complaint">
    <button class="btn secondary" @click="router.push('/citizen')">Back</button>
    <h2>{{ complaint.category }}</h2>
    <p>{{ complaint.description }}</p>
    <p>Status: {{ complaint.status }}</p>
    <ul>
      <li v-for="(h, i) in complaint.history" :key="i">{{ h.status }} - {{ h.note }}</li>
    </ul>
  </div>
</template>