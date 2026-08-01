<script setup>
defineProps({ value: String, kind: { type: String, default: 'status' } })
// Handles both the mock data's "In Progress" (space) and the real
// backend's "in_progress" (underscore) status strings, normalizing
// either to the same "in-progress" class the CSS defines.
function slug(v) { return v.toLowerCase().replace(/[\s_]+/g, '-') }
</script>
<template>
  <span class="badge" :class="kind === 'severity' ? `severity-${slug(value)}` : slug(value)">{{ value }}</span>
</template>