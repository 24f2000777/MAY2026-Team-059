<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()
const complaint = computed(() => store.byId(route.params.id))
const status = ref(complaint.value.status)
const note = ref('')

function save() {
  store.updateStatus(route.params.id, status.value, note.value)
}
</script>

<template>
  <div class="app-content" v-if="complaint">
    <button class="btn secondary" @click="router.push('/staff')">Back</button>
    <h2>{{ complaint.category }}</h2>
    <select v-model="status">
      <option>Submitted</option><option>In Progress</option><option>Resolved</option>
    </select>
    <textarea v-model="note" placeholder="Add a note"></textarea>
    <button class="btn" @click="save">Save</button>
  </div>
</template>