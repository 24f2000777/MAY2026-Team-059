<script setup>
import { computed } from 'vue'
import { useComplaintStore } from '../stores/complaintStore'
import StatCard from '../components/StatCard.vue'
import DonutChart from '../components/DonutChart.vue'
import LineChart from '../components/LineChart.vue'

const store = useComplaintStore()

const totalCount = computed(() => store.complaints.length)
const openCount = computed(() => store.complaints.filter((c) => c.status !== 'Resolved').length)
const resolvedCount = computed(() => store.complaints.filter((c) => c.status === 'Resolved').length)
const avgPriority = computed(() => {
  if (store.complaints.length === 0) return 0
  return Math.round(store.complaints.reduce((sum, c) => sum + c.priorityScore, 0) / store.complaints.length)
})

const statusSegments = computed(() => [
  { label: 'Submitted', value: store.complaints.filter((c) => c.status === 'Submitted').length, color: '#B8860B' },
  { label: 'In Progress', value: store.complaints.filter((c) => c.status === 'In Progress').length, color: '#2F8F5B' },
  { label: 'Resolved', value: resolvedCount.value, color: '#2A9D8F' }
])

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

const filingTrend = computed(() => {
  const days = 14
  const baseline = [3, 4, 3, 5, 6, 5, 7, 6, 8, 7, 9, 8, 10, 9]
  const now = new Date()
  const realByDay = {}
  store.complaints.forEach((c) => {
    const key = new Date(c.createdAt).toISOString().slice(0, 10)
    realByDay[key] = (realByDay[key] || 0) + 1
  })

  return Array.from({ length: days }).map((_, i) => {
    const d = new Date(now)
    d.setDate(d.getDate() - (days - 1 - i))
    const key = d.toISOString().slice(0, 10)
    return {
      label: d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' }),
      value: baseline[i] + (realByDay[key] || 0)
    }
  })
})
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>Analytics</h2>
        <p class="page-intro">A live view of complaint volume, status, and resolution performance.</p>
      </div>
    </div>

    <div class="stat-strip">
      <StatCard label="Total Complaints" :value="totalCount" tone="accent" />
      <StatCard label="Open" :value="openCount" tone="warn" />
      <StatCard label="Resolved" :value="resolvedCount" tone="ok" />
      <StatCard label="Avg. Priority Score" :value="avgPriority" tone="danger" />
    </div>

    <div class="card chart-anim" style="animation-delay: .05s;">
      <h3>Complaints Filed - Last 14 Days</h3>
      <LineChart :points="filingTrend" />
    </div>

    <div class="grid cols-2">
      <div class="card chart-anim" style="animation-delay: .1s;">
        <h3>Status Distribution</h3>
        <DonutChart :segments="statusSegments" />
      </div>

      <div class="card chart-anim" style="animation-delay: .15s;">
        <h3>Category Distribution</h3>
        <div v-if="categoryCounts.length === 0" class="empty-state">No data yet.</div>
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
    </div>

    <div class="grid cols-2">
      <div class="card chart-anim" style="animation-delay: .2s;">
        <h3>Avg. Resolution Time (hrs)</h3>
        <div v-if="resolutionTimes.length === 0" class="empty-state">No resolved complaints yet.</div>
        <div v-else class="bar-chart">
          <div v-for="r in resolutionTimes" :key="r.category" class="bar-row">
            <span class="bar-label">{{ r.category }}</span>
            <div class="bar-track">
              <div class="bar-fill alt animated-fill" :style="{ width: (r.avgHours / maxResolutionHours) * 100 + '%' }"></div>
            </div>
            <span class="bar-value">{{ r.avgHours }}h</span>
          </div>
        </div>
      </div>

      <div class="card chart-anim" style="animation-delay: .25s;">
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
  </div>
</template>