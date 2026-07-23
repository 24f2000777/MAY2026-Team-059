<script setup>
defineProps({
  label: { type: String, required: true },
  sublabel: { type: String, default: '' },
  to: { type: String, default: null }
})
</script>

<template>
  <component :is="to ? 'router-link' : 'button'" :to="to" class="dash-action-tile">
    <span class="dash-action-icon"><slot name="icon" /></span>
    <span class="dash-action-text">
      <strong>{{ label }}</strong>
      <span v-if="sublabel">{{ sublabel }}</span>
    </span>
  </component>
</template>