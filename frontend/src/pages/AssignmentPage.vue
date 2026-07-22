<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useComplaintStore } from '../stores/complaintStore'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const store = useComplaintStore()
const complaint = computed(() => store.byId(route.params.id))
const selectedStaff = ref(complaint.value?.assignedStaffId || '')

function confirmAssignment() {
  if (!selectedStaff.value) return
  store.assign(route.params.id, selectedStaff.value)
  router.push('/admin')
}
</script>

<template>
  <div class="app-content" v-if="complaint">
    <button class="btn secondary" @click="router.push('/admin')">&larr; Back</button>
    <div class="card">
      <div class="header-row"><h2>{{ complaint.category }}</h2><StatusBadge :value="complaint.status" /></div>
      <p class="location">{{ complaint.location }}</p>
      <p class="desc">{{ complaint.description }}</p>
      <img v-if="complaint.photo" :src="complaint.photo" class="photo" />
    </div>
    <div class="card">
      <h3>Assign a Staff Member</h3>
      <div class="field">
        <label>Staff member</label>
        <select v-model="selectedStaff">
          <option value="" disabled>Select staff</option>
          <option v-for="s in store.staffList" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <button class="btn" @click="confirmAssignment">Confirm Assignment</button>
    </div>
  </div>
</template>
<style scoped>
.header-row { display: flex; justify-content: space-between; align-items: center; }
.location { color: var(--text-dim); font-size: 13px; }
.desc { color: var(--text-dim); }
</style>