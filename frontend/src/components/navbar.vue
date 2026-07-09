<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()
function logout() { auth.logout(); router.push('/login') }
</script>

<template>
  <nav class="navbar">
    <span class="brand">Nagrik AI</span>
    <router-link v-if="auth.role === 'citizen'" to="/citizen">My Complaints</router-link>
    <router-link v-if="auth.role === 'citizen'" to="/citizen/new">Report Issue</router-link>
    <router-link v-if="auth.role === 'staff'" to="/staff">My Tasks</router-link>
    <router-link v-if="auth.role === 'admin'" to="/admin">Dashboard</router-link>
    <span class="spacer"></span>
    <span>{{ auth.user?.name }}</span>
    <button class="btn secondary" @click="logout">Log out</button>
  </nav>
</template>

<style scoped>
.navbar { display: flex; align-items: center; gap: 16px; padding: 12px 16px; background: #fff; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.brand { font-weight: 800; }
.spacer { flex: 1; }
</style>