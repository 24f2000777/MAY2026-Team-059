<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar">
    <span class="brand"> NagrikAI </span>

    <router-link v-if="auth.role === 'citizen'" to="/citizen">
      My Complaints
    </router-link>

    <router-link v-if="auth.role === 'citizen'" to="/citizen/new">
      Report Issue
    </router-link>

    <router-link v-if="auth.role === 'staff'" to="/staff">
      My Tasks
    </router-link>

    <router-link v-if="auth.role === 'admin'" to="/admin">
      Dashboard
    </router-link>

    <span class="spacer"></span>

    <span class="user-name">
      {{ auth.user?.name }}
    </span>

    <button class="btn secondary" @click="logout">
      Log out
    </button>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 24px;
  background: #fff;
  border-bottom: 1px solid var(--border);
  box-shadow: 0 2px 8px rgba(0,0,0,.04);
  flex-wrap: wrap;
}

.brand {
  text-decoration: none;
  color: var(--text);
  font-weight: 800;
  font-size: 1.2rem;
  margin-right: 8px;
}

.navbar a {
  text-decoration: none;
  color: var(--text-dim);
  font-weight: 600;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all .2s ease;
}

.navbar a:hover {
  color: var(--accent);
  background: rgba(232,117,44,.08);
}

.navbar .router-link-active {
  color: var(--accent);
  background: rgba(232,117,44,.14);
}

.spacer {
  flex: 1;
}

.user-name {
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel-alt);
  color: var(--text);
  font-weight: 600;
  font-size: 14px;
}
</style>