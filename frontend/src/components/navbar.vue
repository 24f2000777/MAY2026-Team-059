<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()
const router = useRouter()
function logout() { auth.logout(); router.push('/login') }
</script>

<template>
  <nav class="navbar">
    <router-link to="/" class="navbar-logo">
      <span class="lg-nagrik">Nagrik</span><span class="lg-ai">AI</span>
    </router-link>

    <router-link v-if="auth.role === 'citizen'" to="/citizen">My Complaints</router-link>
    <router-link v-if="auth.role === 'citizen'" to="/citizen/new">Report Issue</router-link>
    <router-link v-if="auth.role === 'citizen'" to="/citizen/analytics">Analytics</router-link>
    <router-link v-if="auth.role === 'citizen'" to="/nagrik-saathi">Nagrik Saathi</router-link>

    <router-link v-if="auth.role === 'staff'" to="/staff">My Tasks</router-link>
    <router-link v-if="auth.role === 'staff'" to="/staff/analytics">Analytics</router-link>
    <router-link v-if="auth.role === 'staff'" to="/nagrik-saathi">Nagrik Saathi</router-link>

    <router-link v-if="auth.role === 'admin'" to="/admin">Dashboard</router-link>
    <router-link v-if="auth.role === 'admin'" to="/admin/analytics">Analytics</router-link>

    <span class="spacer"></span>

    <router-link to="/notifications" class="icon-link" title="Notifications">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
      </svg>
    </router-link>
    <router-link to="/feedback" class="icon-link" title="Feedback">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    </router-link>
    <router-link to="/profile" class="user-pill">{{ auth.user?.name }}</router-link>
    <button class="btn secondary" @click="logout">Log out</button>
  </nav>
</template>

<style scoped>
.spacer { flex: 1; }
.user-pill {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  background: var(--panel-alt);
  border: 1px solid var(--border);
  padding: 8px 14px;
  border-radius: 999px;
  text-decoration: none;
}
.icon-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  color: var(--text-dim);
  background: var(--panel-alt);
  border: 1px solid var(--border);
}
.icon-link:hover { color: var(--accent); }
</style>