<script setup>
import { ref, nextTick } from 'vue'
import { useAuthStore } from '../stores/authStore'

const auth = useAuthStore()

const isStaff =
  auth.user?.role === 'staff'

const messages = ref([
  {
    from: 'bot',
    text: isStaff ? "Hello! I'm Nagrik Saathi. I can help you manage assigned complaints, understand workflows, and answer staff-related questions."
      : "Hi! I'm Nagrik Saathi. I can help you report civic issues or track your complaints."
  }
])

const draft = ref('')
const isTyping = ref(false)
const chatBody = ref(null)

const suggestions = isStaff ? [
      'Update status',
      'High priority',
      'Check Assigned Complaints'
    ]
  : [
      'Report pothole',
      'Track complaint',
      'Water leak',
      'Garbage'
    ]

function botReplyFor(text) {

  const t = text.toLowerCase()

  if (isStaff) {

    if (t.includes('status') || t.includes('update')) {
      return "Staff can update complaint progress to Submitted, In Progress or Resolved after completing field verification."
    }

    if (t.includes('priority') || t.includes('high')) {
      return "High severity complaints such as water leaks or public safety hazards should be attended first according to departmental guidelines."
    }

    if (t.includes('check assigned complaints') || t.includes('assigned')) {
      return "Open 'Assigned Complaints' from the staff dashboard to view all complaints allocated to you. You can filter them by status or update their progress."
    }

    if (t.includes('hello') || t.includes('hi') || t.includes('hey')) {
      return "Hello! I can help with complaint assignment, workflow, priorities and status updates."
    }

    return "I can answer questions related to complaint management, assignment, workflow and status updates."
  }

  // citizen

  if (t.includes('pothole') || t.includes('road')) {
    return "Report the pothole using the 'Pothole' category and pin its exact location. Adding a photo helps the road department prioritise repairs."
  }

  if (t.includes('water') || t.includes('leak') || t.includes('pipe')) {
    return "Water leak complaints are treated as high priority. Choose 'Water Leak', attach a photo if possible, and pin the location."
  }

  if (t.includes('garbage') || t.includes('waste')) {
    return "Select 'Garbage Collection', provide the location, and our sanitation team will be notified."
  }

  if (t.includes('track') || t.includes('status')) {
    return "Open 'My Complaints' from your dashboard. Every status update appears in the complaint timeline."
  }

  if (t.includes('hello') || t.includes('hi') || t.includes('hey')) {
    return "Hello! You can ask me how to report potholes, water leaks, garbage issues or track an existing complaint."
  }

  if (t.includes('thank')) {
    return "Happy to help. Stay safe!"
  }

  return "I can help you file complaints or explain complaint tracking. For emergencies, contact the BMC helpline (1916)."
}

async function scrollBottom() {
  await nextTick()

  if (chatBody.value) {
    chatBody.value.scrollTop = chatBody.value.scrollHeight
  }
}

function quickPrompt(text) {
  draft.value = text
  send()
}

async function send() {
  const text = draft.value.trim()

  if (!text) return

  messages.value.push({
    from: 'user',
    text
  })

  draft.value = ''

  await scrollBottom()

  isTyping.value = true

  setTimeout(async () => {
    messages.value.push({
      from: 'bot',
      text: botReplyFor(text)
    })

    isTyping.value = false

    await scrollBottom()
  }, 700)
}
</script>

<template>
  <div class="app-content">
    <div class="chat-shell">
      <div class="chat-header">
        <div class="chat-avatar">
          NS
        </div>
        <div>
          <div class="chat-title">
            Nagrik Saathi
          </div>
          <div class="chat-online">
            <span class="online-dot"></span>
            Online
          </div>
        </div>
      </div>

      <div ref="chatBody" class="chat-body">

        <div
          v-for="(m,index) in messages"
          :key="index"
          class="chat-row"
          :class="m.from"
        >

          <div
            class="chat-bubble"
            :class="m.from"
          >
            {{ m.text }}
          </div>

        </div>

        <div
          v-if="isTyping"
          class="chat-row bot"
        >

          <div class="chat-bubble bot typing">

            <span></span>
            <span></span>
            <span></span>

          </div>

        </div>

      </div>

      <div class="chat-suggestions">

        <button
          v-for="s in suggestions"
          :key="s"
          class="chat-chip"
          @click="quickPrompt(s)"
        >
          {{ s }}
        </button>

      </div>

      <form
        class="chat-input"
        @submit.prevent="send"
      >

        <input
          v-model="draft"
          :placeholder="isStaff ? 'Ask about assignment, workflow or complaint management...' : 'Ask about reporting or tracking complaints...'"
        >

        <button
          class="btn"
          type="submit"
        >
          Send
        </button>

      </form>

    </div>

    <div class="helpline-banner">

      <div>

        <p class="help-small">
          NEED HUMAN ASSISTANCE?
        </p>

        <h3>BMC Helpline 1916</h3>

      </div>

      <p>
        Call directly for emergencies or issues outside this demo assistant.
      </p>

    </div>

  </div>
</template>