<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="app-content">
    <button class="btn secondary" style="margin-bottom: 16px;" @click="router.back()">&larr; Back</button>
    <div class="card" style="max-width: 720px;">
      <h2>Terms of Service</h2>
      <p class="page-intro" style="margin-top: 0;">Last updated July 2026</p>

      <h3>Fair use</h3>
      <p class="desc-text">This platform is for reporting genuine civic issues. Filing false or duplicate complaints to game priority scoring may result in account suspension.</p>

      <h3>Accuracy</h3>
      <p class="desc-text">You're responsible for providing accurate location and description details so staff can act on your report correctly.</p>

      <h3>No guaranteed timelines</h3>
      <p class="desc-text">Resolution times depend on department capacity and issue severity. The platform surfaces status and priority but does not guarantee a fixed turnaround.</p>

      <h3>Emergencies</h3>
      <p class="desc-text">This app is not a substitute for emergency services. For anything dangerous or urgent, call the BMC helpline 1916 directly.</p>
    </div>
  </div>
</template>

<style scoped>
h3 { margin-top: 20px; margin-bottom: 6px; font-size: 15px; }
.desc-text { color: var(--text-dim); font-size: 14px; line-height: 1.6; margin: 0; }
</style>