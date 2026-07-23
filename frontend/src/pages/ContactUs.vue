<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const name = ref('')
const email = ref('')
const message = ref('')
const sent = ref(false)

function submit() {
  sent.value = true
  name.value = ''
  email.value = ''
  message.value = ''
}
</script>

<template>
  <div class="app-content">
    <button class="btn secondary" style="margin-bottom: 16px;" @click="router.back()">&larr; Back</button>

    <div class="grid cols-2">
      <div class="card">
        <h2>Contact Us</h2>
        <p class="page-intro" style="margin-top: 0;">Questions about the platform itself? Reach out here.</p>

        <div v-if="sent" class="empty-state" style="border-style: solid; border-color: var(--ok);">
          Message sent. We'll get back to you soon.
        </div>

        <form v-else @submit.prevent="submit">
          <div class="field"><label>Name</label><input v-model="name" type="text" required /></div>
          <div class="field"><label>Email</label><input v-model="email" type="email" required /></div>
          <div class="field"><label>Message</label><textarea v-model="message" rows="5" required></textarea></div>
          <button class="btn" type="submit">Send Message</button>
        </form>
      </div>

      <div class="card">
        <h3>Other ways to reach us</h3>
        <p class="page-intro" style="margin-top: 0;">For urgent civic issues, don't wait on email.</p>
        <div class="helpline-card" style="margin-top: 16px;">
          <div>
            <p class="helpline-label">BMC Helpline</p>
            <p class="helpline-number">1916</p>
          </div>
          <p class="helpline-note">Available for urgent civic issues, any time.</p>
        </div>
      </div>
    </div>
  </div>
</template>