<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()
const complaint = computed(() => store.byId(route.params.id))
</script>

<template>
  <div class="app-content">
  <div v-if="complaint">
    <button class="btn secondary" @click="router.push('/citizen')">&larr; Back</button>
    <div class="card">
      <div class="header-row">
        <div><h2>{{ complaint.category }}</h2><p class="location">{{ complaint.location }}</p></div>
        <div class="badges"><StatusBadge :value="complaint.status" /><StatusBadge :value="complaint.severity" kind="severity" /></div>
      </div>
      <p class="desc">{{ complaint.description }}</p>
      <img v-if="complaint.photo" :src="complaint.photo" class="photo" />
    </div>
    <div class="card">
      <h3>Status History</h3>
      <ul class="timeline">
        <li v-for="(h, i) in complaint.history" :key="i">
          <strong>{{ h.status }}</strong>
          <p class="note">{{ h.note }}</p>
          <span class="ts">{{ new Date(h.at).toLocaleString() }}</span>
        </li>
      </ul>
    </div>
  </div>
  <div v-if="complaint && complaint.status === 'Resolved'" class="card" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
  <div>
    <p style="margin: 0; font-weight: 700;">{{ complaint.rating ? 'You rated this resolution' : 'How was the resolution?' }}</p>
    <p class="page-intro" style="margin: 4px 0 0 0;">
      <template v-if="complaint.rating">{{ complaint.rating }} / 5 stars<span v-if="complaint.review"> - "{{ complaint.review }}"</span></template>
      <template v-else>Let us know how it went.</template>
    </p>
  </div>
  <button class="btn secondary" @click="router.push(`/citizen/${complaint.id}/rate`)">
    {{ complaint.rating ? 'Edit Rating' : 'Rate Resolution' }}
  </button>
  </div>
  <div v-if="!complaint" class="card">
    <p>This complaint isn't available here yet. Full details for complaints filed since the recent backend update aren't wired up on this page yet.</p>
    <button class="btn secondary" @click="router.push('/citizen')">&larr; Back to My Complaints</button>
  </div>
  </div>
</template>
<style scoped>
.header-row { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.location { color: var(--text-dim); font-size: 13px; margin: 4px 0 0 0; }
.badges { display: flex; gap: 8px; }
.desc { color: var(--text-dim); }
.photo { max-width: 100%; max-height: 260px; border-radius: var(--radius); border: 1px solid var(--border); margin-top: 10px; }
.note { color: var(--text-dim); font-size: 13px; margin: 4px 0; }
.ts { font-size: 12px; color: var(--text-dim); }
</style>