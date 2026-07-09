<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()
const complaint = computed(() => store.byId(route.params.id))
const selectedStaff = ref('')

function confirm() {
  store.assign(route.params.id, selectedStaff.value)
  router.push('/admin')
}
</script>

<template>
  <div class="app-content" v-if="complaint">
    <button class="btn secondary" @click="router.push('/admin')">Back</button>
    <h2>{{ complaint.category }}</h2>
    <select v-model="selectedStaff">
      <option value="" disabled>Select staff</option>
      <option v-for="s in store.staffList" :key="s.id" :value="s.id">{{ s.name }}</option>
    </select>
    <button class="btn" @click="confirm">Confirm</button>
  </div>
</template>