<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useComplaintStore } from '../stores/complaintStore'
import StatCard from '../components/StatCard.vue'
import DonutChart from '../components/DonutChart.vue'

const auth = useAuthStore()
const store = useComplaintStore()

const myTasks = computed(() => store.forStaff(auth.user.id))
const resolvedCount = computed(() => myTasks.value.filter((c) => c.status === 'Resolved').length)
const inProgressCount = computed(() => myTasks.value.filter((c) => c.status === 'In Progress').length)
const highPriorityCount = computed(() => myTasks.value.filter((c) => c.severity === 'High').length)
const submittedCount = computed(() => myTasks.value.filter((c) => c.status === 'Submitted').length)

const statusSegments = computed(() => [
  { label: 'Submitted', value: submittedCount.value, color: '#B8860B' },
  { label: 'In Progress', value: inProgressCount.value, color: '#2F8F5B' },
  { label: 'Resolved', value: resolvedCount.value, color: '#2A9D8F' }
])

const avgResolutionHours = computed(() => {
  const hours = []
  myTasks.value.forEach((c) => {
    if (c.status !== 'Resolved') return
    const entry = [...c.history].reverse().find((h) => h.status === 'Resolved')
    if (!entry) return
    hours.push((entry.at - c.createdAt) / (1000 * 60 * 60))
  })
  if (hours.length === 0) return '—'
  return Math.round(hours.reduce((a, b) => a + b, 0) / hours.length) + 'h'
})

const categoryCounts = computed(() => {
  const counts = {}
  myTasks.value.forEach((c) => (counts[c.category] = (counts[c.category] || 0) + 1))
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})
const maxCategoryCount = computed(() => Math.max(1, ...categoryCounts.value.map(([, n]) => n)))
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>My Performance</h2>
        <p class="page-intro">A snapshot of the complaints assigned to you.</p>
      </div>
    </div>

    <div class="stat-strip">
      <StatCard label="Assigned to Me" :value="myTasks.length" tone="accent" />
      <StatCard label="High Priority" :value="highPriorityCount" tone="danger" />
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
        <div v-if="categoryCounts.length === 0" class="empty-state">No assigned complaints yet.</div>
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
        <h3>Avg. Resolution Time</h3>
        <p class="page-intro" style="margin-top: 0;">Across complaints you've personally resolved.</p>
        <p style="font-size: 40px; font-weight: 900; color: var(--ink); margin: 8px 0 0 0;">{{ avgResolutionHours }}</p>
      </div>
    </div>
  </div>
</template>