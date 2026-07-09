<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="app-content">
    <h2>Page not found</h2>
    <p>The page you're looking for doesn't exist.</p>
    <button class="btn" @click="router.push('/')">Go home</button>
  </div>
</template>