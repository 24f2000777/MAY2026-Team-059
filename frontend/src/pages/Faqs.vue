<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const openIndex = ref(0)

const faqs = [
  { q: 'How do I file a complaint?', a: "Register for an account, then click 'Report Issue' from your dashboard. Fill in the category, location, and description, pin the spot on the map, and optionally attach a photo." },
  { q: 'How long does resolution usually take?', a: 'It depends on severity and category. High-priority issues like water leaks are typically addressed faster than lower-priority ones like streetlight outages.' },
  { q: 'How do I track my complaint?', a: "Open 'My Complaints' from your dashboard and click into any complaint to see its full status timeline." },
  { q: 'Can I edit a complaint after submitting it?', a: 'Not directly, but you can add context by contacting support through the Feedback page, or ask the assigned staff member via a follow-up complaint.' },
  { q: 'Who can see my complaint?', a: 'Your complaint is visible to municipal staff and administrators handling civic issues in your ward. It is not publicly listed.' },
  { q: 'What if my issue is an emergency?', a: 'For anything urgent or dangerous, call the BMC helpline 1916 directly rather than waiting on the app.' }
]

function toggle(i) {
  openIndex.value = openIndex.value === i ? -1 : i
}
</script>

<template>
  <div class="app-content">
    <button class="btn secondary" style="margin-bottom: 16px;" @click="router.back()">&larr; Back</button>
    <div class="header-row">
      <div>
        <h2>Frequently Asked Questions</h2>
        <p class="page-intro">Common questions about filing and tracking civic complaints.</p>
      </div>
    </div>

    <div class="list-stack">
      <div v-for="(item, i) in faqs" :key="i" class="card" style="cursor: pointer;" @click="toggle(i)">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong>{{ item.q }}</strong>
          <span style="font-size: 20px; color: var(--accent); font-weight: 700;">{{ openIndex === i ? '−' : '+' }}</span>
        </div>
        <p v-if="openIndex === i" class="page-intro" style="margin: 12px 0 0 0;">{{ item.a }}</p>
      </div>
    </div>
  </div>
</template>