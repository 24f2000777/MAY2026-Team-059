<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()
const complaint = computed(() => store.byId(route.params.id))
const status = ref(complaint.value?.status ?? '')
const note = ref('')

function saveUpdate() {
  store.updateStatus(route.params.id, status.value, note.value || undefined)
  note.value = ''
}
</script>

<template>
  <div class="app-content" v-if="complaint">
    <button class="btn secondary" @click="router.push('/staff')">&larr; Back</button>
    <div class="card">
      <div class="header-row"><h2>{{ complaint.category }}</h2><StatusBadge :value="complaint.status" /></div>
      <p class="location">{{ complaint.location }}</p>
      <p class="desc">{{ complaint.description }}</p>
      <img v-if="complaint.photo" :src="complaint.photo" class="photo" />
    </div>
    <div class="card">
      <h3>Update Status</h3>
      <div class="field">
        <label>Status</label>
        <select v-model="status" :disabled="complaint.status === 'Resolved'"><option>Submitted</option><option>In Progress</option><option>Resolved</option></select>
      </div>
      <div class="field"><label>Notes (optional)</label><textarea v-model="note" rows="3"></textarea></div>
      <button class="btn" @click="saveUpdate" :disabled="complaint.status === 'Resolved'"> {{ complaint.status === 'Resolved' ? 'Already Resolved' : 'Save Update' }}</button>
    </div>
    <div class="card">
      <h3>History</h3>
      <ul class="timeline">
        <li v-for="(h, i) in complaint.history" :key="i">
          <strong>{{ h.status }}</strong><p class="note-item">{{ h.note }}</p>
          <span class="ts">{{ new Date(h.at).toLocaleString() }}</span>
        </li>
      </ul>
    </div>
  </div>
  <div v-else class="card">
    <p>Complaint not found.</p>
    <router-link to="/staff" class="btn secondary">Back to my tasks</router-link>
  </div>
</template>
<style scoped>
.header-row { display: flex; justify-content: space-between; align-items: center; }
.location { color: var(--text-dim); font-size: 13px; }
.desc { color: var(--text-dim); }
.photo { max-width: 100%; max-height: 220px; border-radius: var(--radius); border: 1px solid var(--border); margin-top: 10px; }
.note-item { font-size: 13px; color: var(--text-dim); margin: 4px 0; }
.ts { font-size: 12px; color: var(--text-dim); }
</style>