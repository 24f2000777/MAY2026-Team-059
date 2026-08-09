<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getAnalyticsSummary } from '../api/analyticsApi'
import { categoryBreakdown } from '../constants/categories'
import { doneCount, openCount, statusSegments } from '../constants/statuses'
import StatCard from '../components/StatCard.vue'
import DonutChart from '../components/DonutChart.vue'

const auth = useAuthStore()
const router = useRouter()

const summary = ref(null)
const loadError = ref('')

async function load() {
  loadError.value = ''
  try {
    summary.value = await getAnalyticsSummary({ accessToken: auth.accessToken })
  } catch (e) {
    if (e.status === 401) {
      await auth.logout()
      router.push('/login')
      return
    }
    loadError.value = e.message
  }
}

onMounted(load)

const totalCount = computed(() => summary.value?.total ?? 0)
const openCountValue = computed(() => (summary.value ? openCount(summary.value.total, summary.value.status_counts) : 0))
const inProgressCount = computed(() => summary.value?.status_counts.in_progress ?? 0)
const resolvedCount = computed(() => (summary.value ? doneCount(summary.value.status_counts) : 0))

const statusChartSegments = computed(() => (summary.value ? statusSegments(summary.value.status_counts) : []))
const categoryCounts = computed(() => (summary.value ? categoryBreakdown(summary.value.category_counts) : []))
const maxCategoryCount = computed(() => Math.max(1, ...categoryCounts.value.map((c) => c.count)))

const resolveRate = computed(() => {
  if (!summary.value || summary.value.total === 0) return '-'
  return Math.round((resolvedCount.value / summary.value.total) * 100) + '%'
})
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>My Performance</h2>
        <p class="page-intro">A snapshot of the complaints assigned to you.</p>
      </div>
    </div>

    <p v-if="loadError" class="error-text">{{ loadError }}</p>

    <div class="stat-strip">
      <StatCard label="Assigned to Me" :value="totalCount" tone="accent" />
      <StatCard label="Open" :value="openCountValue" tone="warn" />
      <StatCard label="In Progress" :value="inProgressCount" tone="accent" />
      <StatCard label="Resolved" :value="resolvedCount" tone="ok" />
    </div>

    <div class="grid cols-2">
      <div class="card chart-anim" style="animation-delay: .05s;">
        <h3>Status Breakdown</h3>
        <div v-if="statusChartSegments.length === 0" class="empty-state">No assigned complaints yet.</div>
        <DonutChart v-else :segments="statusChartSegments" />
      </div>

      <div class="card chart-anim" style="animation-delay: .1s;">
        <h3>Category Breakdown</h3>
        <div v-if="categoryCounts.length === 0" class="empty-state">No assigned complaints yet.</div>
        <div v-else class="bar-chart">
          <div v-for="c in categoryCounts" :key="c.label" class="bar-row">
            <span class="bar-label">{{ c.label }}</span>
            <div class="bar-track">
              <div class="bar-fill animated-fill" :style="{ width: (c.count / maxCategoryCount) * 100 + '%' }"></div>
            </div>
            <span class="bar-value">{{ c.count }}</span>
          </div>
        </div>
      </div>

      <div class="card chart-anim" style="animation-delay: .15s;">
        <h3>Resolution Rate</h3>
        <p class="page-intro" style="margin-top: 0;">Share of your assigned complaints marked resolved or closed.</p>
        <p style="font-size: 40px; font-weight: 900; color: var(--ink); margin: 8px 0 0 0;">{{ resolveRate }}</p>
      </div>
    </div>
  </div>
</template>
