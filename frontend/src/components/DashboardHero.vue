<script setup>
defineProps({
  name: { type: String, required: true },
  subtitle: { type: String, required: true }
})

const hour = new Date().getHours()
const timeGreeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
</script>

<template>
  <div class="dash-hero">
    <p class="dash-hero-eyebrow">{{ timeGreeting }}</p>
    <h1 class="dash-hero-greeting">{{ name }}.</h1>
    <p class="dash-hero-sub">{{ subtitle }}</p>
  </div>

  <div class="dash-actions">
    <slot name="actions" />
  </div>
</template>