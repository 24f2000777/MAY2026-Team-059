<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getAnalyticsSummary, getFeedbackSummary } from '../api/analyticsApi'
import { categoryBreakdown } from '../constants/categories'
import { doneCount, openCount, statusSegments } from '../constants/statuses'
import StatCard from '../components/StatCard.vue'
import DonutChart from '../components/DonutChart.vue'
import LineChart from '../components/LineChart.vue'

const auth = useAuthStore()
const router = useRouter()

const summary = ref(null)
const feedbackSummary = ref(null)
const loadError = ref('')

async function load() {
  loadError.value = ''
  try {
    const [analytics, feedback] = await Promise.all([
      getAnalyticsSummary({ accessToken: auth.accessToken }),
      getFeedbackSummary({ accessToken: auth.accessToken })
    ])
    summary.value = analytics
    feedbackSummary.value = feedback
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
const resolvedCount = computed(() => (summary.value ? doneCount(summary.value.status_counts) : 0))
const resolutionRate = computed(() => {
  if (!summary.value || summary.value.total === 0) return '-'
  return Math.round((resolvedCount.value / summary.value.total) * 100) + '%'
})

const statusChartSegments = computed(() => (summary.value ? statusSegments(summary.value.status_counts) : []))
const categoryCounts = computed(() => (summary.value ? categoryBreakdown(summary.value.category_counts) : []))
const maxCategoryCount = computed(() => Math.max(1, ...categoryCounts.value.map((c) => c.count)))

const filingTrend = computed(() => {
  if (!summary.value) return []
  return summary.value.filing_trend.map((point) => ({
    label: new Date(point.date).toLocaleDateString(undefined, { day: 'numeric', month: 'short', timeZone: 'UTC' }),
    value: point.count
  }))
})

const averageRatingLabel = computed(() => {
  const avg = feedbackSummary.value?.average_score
  return avg == null ? '-' : `${avg.toFixed(1)} / 5`
})

// score_distribution comes back keyed 1-5, JSON object keys are always
// strings so look them up as such. Highest rating shown first.
const ratingDistribution = computed(() => {
  const dist = feedbackSummary.value?.score_distribution || {}
  return [5, 4, 3, 2, 1].map((stars) => ({ stars, count: dist[stars] ?? dist[String(stars)] ?? 0 }))
})
const maxRatingCount = computed(() => Math.max(1, ...ratingDistribution.value.map((r) => r.count)))
</script>

<template>
  <div class="app-content">
    <div class="header-row">
      <div>
        <h2>Analytics</h2>
        <p class="page-intro">A live view of complaint volume and status across every ward.</p>
      </div>
    </div>

    <p v-if="loadError" class="error-text">{{ loadError }}</p>

    <div class="stat-strip">
      <StatCard label="Total Complaints" :value="totalCount" tone="accent" />
      <StatCard label="Open" :value="openCountValue" tone="warn" />
      <StatCard label="Resolved" :value="resolvedCount" tone="ok" />
      <StatCard label="Resolution Rate" :value="resolutionRate" tone="danger" />
    </div>

    <div class="card chart-anim" style="animation-delay: .05s;">
      <h3>Complaints Filed - Last 14 Days</h3>
      <LineChart :points="filingTrend" />
    </div>

    <div class="grid cols-2">
      <div class="card chart-anim" style="animation-delay: .1s;">
        <h3>Status Distribution</h3>
        <div v-if="statusChartSegments.length === 0" class="empty-state">No data yet.</div>
        <DonutChart v-else :segments="statusChartSegments" />
      </div>

      <div class="card chart-anim" style="animation-delay: .15s;">
        <h3>Category Distribution</h3>
        <div v-if="categoryCounts.length === 0" class="empty-state">No data yet.</div>
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
    </div>

    <div class="card chart-anim" style="animation-delay: .2s;">
      <h3>Citizen Feedback</h3>
      <div v-if="!feedbackSummary || feedbackSummary.total_ratings === 0" class="empty-state">No feedback yet.</div>
      <template v-else>
        <div class="stat-strip">
          <StatCard label="Average Rating" :value="averageRatingLabel" tone="accent" />
          <StatCard label="Total Ratings" :value="feedbackSummary.total_ratings" tone="ok" />
        </div>
        <div class="bar-chart">
          <div v-for="r in ratingDistribution" :key="r.stars" class="bar-row">
            <span class="bar-label">{{ r.stars }} star{{ r.stars === 1 ? '' : 's' }}</span>
            <div class="bar-track">
              <div class="bar-fill animated-fill" :style="{ width: (r.count / maxRatingCount) * 100 + '%' }"></div>
            </div>
            <span class="bar-value">{{ r.count }}</span>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
