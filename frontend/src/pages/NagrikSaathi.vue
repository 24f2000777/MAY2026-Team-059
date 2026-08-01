<script setup>
import { ref, nextTick, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import StatusBadge from '../components/StatusBadge.vue'

const auth = useAuthStore()
const chat = useChatStore()
const router = useRouter()

const isStaff =
  auth.user?.role === 'staff'

const greeting = isStaff
  ? "Hello! I'm Nagrik Saathi. I can help you manage assigned complaints, understand workflows, and answer staff-related questions."
  : "Hi! I'm Nagrik Saathi. I can help you report civic issues or track your complaints."

const messages = computed(() => chat.messages)
const isTyping = computed(() => chat.isTyping)
// Only offer quick-reply chips on a fresh conversation (nothing but the
// greeting so far), a returning user with real history already knows
// what to ask.
const showSuggestions = computed(() => chat.messages.length <= 1)

const draft = ref('')
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

onMounted(async () => {
  chat.initSession(auth.user.id)
  try {
    await chat.loadHistory({ accessToken: auth.accessToken })
  } catch (e) {
    if (e.status === 401) {
      // Same reasoning as send()'s 401 handling below: isLoggedIn only
      // checks that a token is present, not that it's still valid, so
      // clear the stale session before redirecting or the guest-route
      // guard would just bounce back here.
      await auth.logout()
      router.push('/login')
      return
    }
  }
  chat.seedGreetingIfEmpty(greeting)
})

async function scrollBottom() {
  await nextTick()

  if (chatBody.value) {
    chatBody.value.scrollTop = chatBody.value.scrollHeight
  }
}

// Scroll whenever a message is added, whether that's the user's own
// bubble appearing immediately or the reply arriving after the API call.
watch(() => chat.messages.length, scrollBottom)

function quickPrompt(text) {
  draft.value = text
  send()
}

async function send() {
  const text = draft.value.trim()

  if (!text) return

  draft.value = ''

  try {
    await chat.sendMessage({ text, accessToken: auth.accessToken })
  } catch (e) {
    if (e.status === 401) {
      // isLoggedIn only checks that a token is present, not that it's
      // still valid, so pushing straight to /login would get bounced
      // right back home by the guest-route guard unless the stale auth
      // state is cleared first.
      await auth.logout()
      router.push('/login')
    }
    // Any other failure is already reflected in chat.error and rendered
    // below, nothing further to do here.
  }
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

            <div v-if="m.complaint" class="filed-complaint">
              <div class="filed-complaint-row">
                <strong>{{ m.complaint.category }}</strong>
                <StatusBadge :value="m.complaint.status" />
              </div>
              <div class="filed-complaint-row">
                <span class="priority">Priority score: {{ m.complaint.priority_score }}</span>
              </div>
            </div>
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

      <p v-if="chat.error" class="error-text" style="margin: 0 16px 8px;">
        {{ chat.error }}
      </p>

      <div v-if="showSuggestions" class="chat-suggestions">

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
