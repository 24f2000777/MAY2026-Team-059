<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { getAnalyticsSummary } from '../api/analyticsApi'
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

  <!-- 1. Status Breakdown -->
  <div class="card chart-anim" style="animation-delay: .05s;">
    <h3>Status Breakdown</h3>

    <div v-if="statusChartSegments.length === 0" class="empty-state">
      No assigned complaints yet.
    </div>

    <DonutChart
      v-else
      :segments="statusChartSegments"
    />
  </div>


  <!-- 2. Workload Overview -->
  <div class="card chart-anim" style="animation-delay: .1s;">
    <h3>Workload Overview</h3>

    <div v-if="totalCount === 0" class="empty-state">
      No assigned complaints yet.
    </div>

    <div v-else class="workload-chart">

      <div class="workload-row">
        <div class="workload-header">
          <span>Open</span>
          <strong>{{ openCountValue }}</strong>
        </div>

        <div class="workload-track">
          <div
            class="workload-fill open-fill"
            :style="{
              width: (openCountValue / totalCount) * 100 + '%'
            }"
          ></div>
        </div>
      </div>

      <div class="workload-row">
        <div class="workload-header">
          <span>In Progress</span>
          <strong>{{ inProgressCount }}</strong>
        </div>

        <div class="workload-track">
          <div
            class="workload-fill progress-fill"
            :style="{
              width: (inProgressCount / totalCount) * 100 + '%'
            }"
          ></div>
        </div>
      </div>

      <div class="workload-row">
        <div class="workload-header">
          <span>Resolved</span>
          <strong>{{ resolvedCount }}</strong>
        </div>

        <div class="workload-track">
          <div
            class="workload-fill resolved-fill"
            :style="{
              width: (resolvedCount / totalCount) * 100 + '%'
            }"
          ></div>
        </div>
      </div>

    </div>
  </div>


  <!-- 3. Resolution Rate -->
  <div class="card chart-anim" style="animation-delay: .15s;">
    <h3>Resolution Rate</h3>

    <p class="page-intro">
      Share of your assigned complaints marked resolved or closed.
    </p>

    <div class="resolution-chart">
      <div
        class="resolution-ring"
        :style="{
          '--progress': resolveRate === '-' ? 0 : parseInt(resolveRate)
        }"
      >
        <div class="resolution-ring-inner">
          <strong>{{ resolveRate }}</strong>
          <span>Resolved</span>
        </div>
      </div>
    </div>
  </div>


  <!-- 4. Work Status -->
  <div class="card chart-anim" style="animation-delay: .2s;">
    <h3>Work Status</h3>

    <div v-if="totalCount === 0" class="empty-state">
      No assigned complaints yet.
    </div>

    <div v-else class="status-bars">

      <div class="status-bar-row">
        <div class="status-bar-label">
          <span>Active</span>
          <strong>{{ openCountValue + inProgressCount }}</strong>
        </div>

        <div class="status-bar-track">
          <div
            class="status-bar-fill active-fill"
            :style="{
              width:
                ((openCountValue + inProgressCount) / totalCount) * 100 + '%'
            }"
          ></div>
        </div>
      </div>

      <div class="status-bar-row">
        <div class="status-bar-label">
          <span>Completed</span>
          <strong>{{ resolvedCount }}</strong>
        </div>

        <div class="status-bar-track">
          <div
            class="status-bar-fill completed-fill"
            :style="{
              width: (resolvedCount / totalCount) * 100 + '%'
            }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</div>
</div>       
</template>
