<script setup>
import StatusBadge from './StatusBadge.vue'
defineProps({ complaint: Object, showPriority: { type: Boolean, default: false } })
</script>
<template>
  <div class="card complaint-card">
    <div class="row top">
      <strong>{{ complaint.category }}</strong>
      <StatusBadge :value="complaint.status" />
    </div>
    <p class="desc">{{ complaint.description }}</p>
    <div class="row meta">
      <span>{{ complaint.location }}</span>
      <StatusBadge v-if="complaint.severity" :value="complaint.severity" kind="severity" />
      <span v-if="showPriority" class="priority">Priority: {{ complaint.priorityScore }}</span>
    </div>
    <div class="row bottom">
      <span class="date">Filed {{ new Date(complaint.createdAt).toLocaleDateString() }}</span>
      <slot name="actions" />
    </div>
  </div>
</template>
<style scoped>
.complaint-card .row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.row.top { justify-content: space-between; margin-bottom: 8px; }
.desc { color: var(--text-dim); font-size: 14px; margin: 8px 0; }
.row.meta { font-size: 13px; color: var(--text-dim); margin-bottom: 10px; }
.priority { color: var(--accent); font-weight: 700; }
.row.bottom { justify-content: space-between; border-top: 1px solid var(--border); padding-top: 10px; }
.date { font-size: 12px; color: var(--text-dim); }
</style>