<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'
import StatCard from '../components/StatCard.vue'
import DonutChart from '../components/DonutChart.vue'

const auth = useAuthStore()
const store = useComplaintStore()

const myComplaints = computed(() => store.forCitizen(auth.user.id))
const resolvedCount = computed(() => myComplaints.value.filter((c) => c.status === 'Resolved').length)
const inProgressCount = computed(() => myComplaints.value.filter((c) => c.status === 'In Progress').length)
const submittedCount = computed(() => myComplaints.value.filter((c) => c.status === 'Submitted').length)

const statusSegments = computed(() => [
  { label: 'Submitted', value: submittedCount.value, color: '#B8860B' },
  { label: 'In Progress', value: inProgressCount.value, color: '#2F8F5B' },
  { label: 'Resolved', value: resolvedCount.value, color: '#2A9D8F' }
])

const resolveRate = computed(() => {
  if (myComplaints.value.length === 0) return '-'
  return Math.round((resolvedCount.value / myComplaints.value.length) * 100) + '%'
})

const categoryCounts = computed(() => {
  const counts = {}
  myComplaints.value.forEach((c) => (counts[c.category] = (counts[c.category] || 0) + 1))
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})
const maxCategoryCount = computed(() => Math.max(1, ...categoryCounts.value.map(([, n]) => n)))
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>My Activity</h2>
        <p class="page-intro">A summary of everything you've reported.</p>
      </div>
    </div>

    <div class="stat-strip">
      <StatCard label="Total Filed" :value="myComplaints.length" tone="accent" />
      <StatCard label="Submitted" :value="submittedCount" tone="warn" />
      <StatCard label="In Progress" :value="inProgressCount" tone="accent" />
      <StatCard label="Resolved" :value="resolvedCount" tone="ok" />
    </div>

    <div class="grid cols-2">
      <div class="card chart-anim" style="animation-delay: .05s;">
        <h3>Status Breakdown</h3>
        <DonutChart :segments="statusSegments" />
      </div>

      <div class="card chart-anim" style="animation-delay: .1s;">
        <h3>Category Breakdown</h3>
        <div v-if="categoryCounts.length === 0" class="empty-state">You haven't filed any complaints yet.</div>
        <div v-else class="bar-chart">
          <div v-for="[category, count] in categoryCounts" :key="category" class="bar-row">
            <span class="bar-label">{{ category }}</span>
            <div class="bar-track">
              <div class="bar-fill animated-fill" :style="{ width: (count / maxCategoryCount) * 100 + '%' }"></div>
            </div>
            <span class="bar-value">{{ count }}</span>
          </div>
        </div>
      </div>

      <div class="card chart-anim" style="animation-delay: .15s;">
        <h3>Resolution Rate</h3>
        <p class="page-intro" style="margin-top: 0;">Share of your complaints marked Resolved.</p>
        <p style="font-size: 40px; font-weight: 900; color: var(--ink); margin: 8px 0 0 0;">{{ resolveRate }}</p>
      </div>
    </div>
  </div>
</template>