<script setup>
import { computed } from 'vue'
import { useComplaintStore } from '../stores/complaintStore'

const store = useComplaintStore()

const categoryCounts = computed(() => {
  const counts = {}
  store.complaints.forEach((c) => (counts[c.category] = (counts[c.category] || 0) + 1))
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})
const maxCategoryCount = computed(() => Math.max(1, ...categoryCounts.value.map(([, n]) => n)))

const resolutionTimes = computed(() => {
  const byCategory = {}
  store.complaints.forEach((c) => {
    if (c.status !== 'Resolved') return
    const entry = [...c.history].reverse().find((h) => h.status === 'Resolved')
    if (!entry) return
    const hours = (entry.at - c.createdAt) / (1000 * 60 * 60)
    if (!byCategory[c.category]) byCategory[c.category] = []
    byCategory[c.category].push(hours)
  })
  return Object.entries(byCategory).map(([category, list]) => ({
    category,
    avgHours: Math.round(list.reduce((a, b) => a + b, 0) / list.length)
  }))
})
const maxResolutionHours = computed(() => Math.max(1, ...resolutionTimes.value.map((r) => r.avgHours)))

const areaCounts = computed(() => {
  const counts = {}
  store.complaints.forEach((c) => (counts[c.location] = (counts[c.location] || 0) + 1))
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
})
const maxAreaCount = computed(() => Math.max(1, ...areaCounts.value.map(([, n]) => n)))

function heatColor(count) {
  const intensity = count / maxAreaCount.value
  return `rgba(47, 143, 91, ${0.12 + intensity * 0.5})`
}
</script>

<template>
  <div class="app-content">
    <h2>Analytics</h2>

    <div class="grid cols-2">
      <div class="card">
        <h3>Category Distribution</h3>
        <div v-if="categoryCounts.length === 0" class="empty-state">No data yet.</div>
        <div v-else class="bar-chart">
          <div v-for="[category, count] in categoryCounts" :key="category" class="bar-row">
            <span class="bar-label">{{ category }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: (count / maxCategoryCount) * 100 + '%' }"></div>
            </div>
            <span class="bar-value">{{ count }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Avg. Resolution Time (hrs)</h3>
        <div v-if="resolutionTimes.length === 0" class="empty-state">No resolved complaints yet.</div>
        <div v-else class="bar-chart">
          <div v-for="r in resolutionTimes" :key="r.category" class="bar-row">
            <span class="bar-label">{{ r.category }}</span>
            <div class="bar-track">
              <div class="bar-fill alt" :style="{ width: (r.avgHours / maxResolutionHours) * 100 + '%' }"></div>
            </div>
            <span class="bar-value">{{ r.avgHours }}h</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Complaint Density by Area</h3>
      <div v-if="areaCounts.length === 0" class="empty-state">No data yet.</div>
      <div v-else class="heatmap">
        <div v-for="[area, count] in areaCounts" :key="area" class="heat-cell" :style="{ background: heatColor(count) }">
          <strong>{{ area }}</strong>
          <span>{{ count }} report{{ count === 1 ? '' : 's' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>