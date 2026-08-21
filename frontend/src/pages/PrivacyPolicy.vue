<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="app-content">
    <button class="btn secondary" style="margin-bottom: 16px;" @click="router.back()">&larr; Back</button>
    <div class="card" style="max-width: 720px;">
      <h2>Privacy Policy</h2>
      <p class="page-intro" style="margin-top: 0;">Last updated July 2026</p>

      <h3>What we collect</h3>
      <p class="desc-text">Your name, email, and phone number when you register; the details, photo, and location you provide when filing a complaint.</p>

      <h3>How it's used</h3>
      <p class="desc-text">Solely to route your complaint to the right municipal department, notify you of status changes, and let staff and admins coordinate a resolution.</p>

      <h3>Who can see it</h3>
      <p class="desc-text">Municipal staff and admins handling complaints in your ward. Your complaint is never made public or shared with third parties.</p>

      <h3>Data retention</h3>
      <p class="desc-text">Complaint records are kept for as long as your account is active, so you retain a full history of what you've reported and how it was resolved.</p>
    </div>
  </div>
</template>

<style scoped>
h3 { margin-top: 20px; margin-bottom: 6px; font-size: 15px; }
.desc-text { color: var(--text-dim); font-size: 14px; line-height: 1.6; margin: 0; }
</style>