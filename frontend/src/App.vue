<script setup>
import { useAuthStore } from './stores/authStore'
import Navbar from './components/navbar.vue'
const auth = useAuthStore()
</script>

<template>
  <div class="app-shell">
    <Navbar v-if="auth.isLoggedIn" />
    <main>
      <router-view />
    </main>
  </div>
</template>