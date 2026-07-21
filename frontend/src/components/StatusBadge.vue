<script setup>
defineProps({ value: String, kind: { type: String, default: 'status' } })
function slug(v) { return v.toLowerCase().replace(/\s+/g, '-') }
</script>
<template>
  <span class="badge" :class="kind === 'severity' ? `severity-${slug(value)}` : slug(value)">{{ value }}</span>
</template>