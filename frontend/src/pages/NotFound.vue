<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="app-content">
    <h4 style="text-align: center; font-size: 28px;">NAGRIK AI</h4>
    <div class="card empty-state">
      <h2>Page not found</h2>
      <p>The page you're looking for doesn't exist.</p>
      <button class="btn" style="margin-top: 12px;" @click="router.push('/')">Go home</button>
    </div>
  </div>
</template>