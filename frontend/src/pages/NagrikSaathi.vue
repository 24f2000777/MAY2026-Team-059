<script setup>
import { ref, nextTick, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { getMyComplaints } from '../api/complaintApi'
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
// The big centered greeting + quick-reply chips only make sense on a
// fresh conversation (nothing but the seeded greeting so far), a
// conversation already underway shows the normal message list instead.
const showHero = computed(() => chat.messages.length <= 1)

const draft = ref('')
const chatBody = ref(null)
const fileInput = ref(null)

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

const quickActions = isStaff
  ? [
      { label: 'My Tasks', to: '/staff', icon: 'tasks' },
      { label: 'Analytics', to: '/staff/analytics', icon: 'search' }
    ]
  : [
      { label: 'Report Issue', to: '/citizen/new', icon: 'plus' },
      { label: 'Track Complaint', to: '/citizen', icon: 'search' }
    ]

const recentComplaints = ref([])
const recentLoading = ref(true)

const STATUS_DOT = {
  submitted: 'var(--warn)',
  pending_approval: 'var(--warn)',
  approved: 'var(--accent)',
  in_progress: 'var(--accent)',
  resolved: 'var(--ok)',
  closed: 'var(--text-dim)',
  rejected: 'var(--danger)',
  withdrawn: 'var(--text-dim)'
}

function statusDot(status) {
  return STATUS_DOT[status] || 'var(--text-dim)'
}

function statusLabel(status) {
  return status.replace(/_/g, ' ')
}

function relativeTime(iso) {
  // The backend serializes created_at as a naive datetime string with
  // no timezone marker (it's really UTC), and without one some
  // browsers parse it as local time instead, so a complaint filed
  // seconds ago in IST could read as "5h ago". Force UTC parsing when
  // the string doesn't already carry an offset of its own.
  const hasOffset = /[Zz]|[+-]\d\d:\d\d$/.test(iso)
  const minutes = Math.floor((Date.now() - new Date(hasOffset ? iso : `${iso}Z`).getTime()) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

async function loadRecent() {
  // Staff don't file complaints themselves, there's nothing of their
  // own to show here, the sidebar just skips this section for them.
  if (isStaff) {
    recentLoading.value = false
    return
  }
  try {
    const data = await getMyComplaints({ accessToken: auth.accessToken })
    recentComplaints.value = [...data.complaints]
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 3)
  } catch (e) {
    // Secondary to the chat itself, fail silently rather than blocking
    // or cluttering the page with an error banner for a sidebar list.
  } finally {
    recentLoading.value = false
  }
}

onMounted(() => {
  // Always a fresh conversation, a returning citizen should land on a
  // blank chat ready to file something new, not their last transcript.
  // No network call needed here, sendMessage's own 401 handling below
  // covers an expired token once they actually try to chat.
  chat.startNewConversation()
  chat.seedGreetingIfEmpty(greeting)
  loadRecent()
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

function triggerFilePicker() {
  fileInput.value?.click()
}

function onFilesPicked(e) {
  const files = Array.from(e.target.files || [])
  if (files.length > 0) chat.addPendingImages(files)
  // Reset so picking the exact same file again still fires @change.
  e.target.value = ''
}

function shareLocation() {
  chat.error = null
  if (!navigator.geolocation) {
    chat.error = 'Location is not supported by this browser.'
    return
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      chat.setLocation({ latitude: position.coords.latitude, longitude: position.coords.longitude })
    },
    () => {
      chat.error = 'Could not get your location. You can still describe it in your message.'
    }
  )
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
  <div class="app-content full-width saathi-page">
    <div class="saathi-layout">
      <aside class="saathi-sidebar">
        <p class="sidebar-heading">Quick Actions</p>
        <nav class="quick-actions">
          <router-link v-for="a in quickActions" :key="a.to" :to="a.to" class="quick-action">
            <svg v-if="a.icon === 'plus'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            <svg v-else-if="a.icon === 'search'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="M21 21l-4.35-4.35"></path></svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
            {{ a.label }}
          </router-link>
          <a href="tel:1916" class="quick-action emergency">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            Emergency
          </a>
        </nav>

        <template v-if="!isStaff">
          <div class="sidebar-heading-row">
            <p class="sidebar-heading">Recent</p>
            <router-link to="/citizen/new" class="new-link">+ New</router-link>
          </div>
          <div class="recent-list">
            <p v-if="recentLoading" class="recent-empty">Loading...</p>
            <p v-else-if="recentComplaints.length === 0" class="recent-empty">No complaints yet.</p>
            <router-link
              v-for="c in recentComplaints"
              :key="c.id"
              :to="`/citizen/${c.id}`"
              class="recent-item"
            >
              <span class="recent-dot" :style="{ background: statusDot(c.status) }"></span>
              <span class="recent-body">
                <span class="recent-title">{{ c.title }}</span>
                <span class="recent-meta">{{ statusLabel(c.status) }} &middot; {{ relativeTime(c.created_at) }}</span>
              </span>
            </router-link>
          </div>
        </template>
      </aside>

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
          <div v-if="showHero" class="chat-hero">
            <div class="chat-hero-avatar">NS</div>
            <h2>Hi, I'm Nagrik Saathi</h2>
            <p>
              I can help you file, track, or ask about civic complaints with BMC,
              pick a quick action below or just tell me what's going on.
            </p>
            <div class="chat-suggestions hero">
              <button
                v-for="s in suggestions"
                :key="s"
                class="chat-chip"
                @click="quickPrompt(s)"
              >
                {{ s }}
              </button>
              <button class="chat-chip" @click="quickPrompt(`I'd like to talk to a human representative.`)">
                Talk to a human
              </button>
            </div>
          </div>

          <template v-else>
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
                <div v-if="m.images && m.images.length > 0" class="bubble-images">
                  <img v-for="(src, i) in m.images" :key="i" :src="src" alt="Attached photo" />
                </div>

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
          </template>
        </div>

        <p v-if="chat.error" class="error-text" style="margin: 0 16px 8px;">
          {{ chat.error }}
        </p>

        <div class="helpline-banner inline">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
          Need human assistance? BMC Helpline <a href="tel:1916">1916</a>
        </div>

        <div v-if="chat.pendingImages.length > 0 || chat.location" class="composer-attachments">
          <div v-for="(img, i) in chat.pendingImages" :key="i" class="attachment-thumb">
            <img :src="img.previewUrl" alt="Photo to attach" />
            <button type="button" class="attachment-remove" @click="chat.removePendingImage(i)">&times;</button>
          </div>
          <div v-if="chat.location" class="location-chip">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
            Location shared
            <button type="button" class="attachment-remove" @click="chat.clearLocation()">&times;</button>
          </div>
        </div>

        <form
          class="chat-input"
          @submit.prevent="send"
        >
          <input ref="fileInput" type="file" accept="image/*" multiple class="hidden-file-input" @change="onFilesPicked" />

          <button type="button" class="composer-icon-btn" title="Attach a photo" @click="triggerFilePicker">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
          </button>

          <button type="button" class="composer-icon-btn" :class="{ active: chat.location }" title="Share your location" @click="shareLocation">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
          </button>

          <input
            v-model="draft"
            :placeholder="isStaff ? 'Ask about assignment, workflow or complaint management...' : 'Message Nagrik Saathi...'"
          >

          <button
            class="composer-send"
            type="submit"
            title="Send"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>

        </form>

      </div>
    </div>
  </div>
</template>

<style scoped>
.saathi-page { padding-top: 20px; padding-bottom: 20px; }

.saathi-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
  align-items: start;
}

.saathi-sidebar {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.sidebar-heading {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--text-dim);
  margin: 0 0 10px;
}

.sidebar-heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 22px;
}
.sidebar-heading-row .sidebar-heading { margin: 0; }
.new-link { font-size: 12px; font-weight: 700; color: var(--accent); text-decoration: none; }

.quick-actions { display: flex; flex-direction: column; gap: 4px; }

.quick-action {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: var(--radius);
  color: var(--text);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}
.quick-action:hover { background: var(--panel-alt); }
.quick-action.emergency { color: var(--warn); }
.quick-action.emergency:hover { background: rgba(184,134,11,.1); }

.recent-list { display: flex; flex-direction: column; gap: 2px; margin-top: 10px; }
.recent-empty { font-size: 13px; color: var(--text-dim); margin: 4px 0; }

.recent-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius);
  text-decoration: none;
  color: var(--text);
}
.recent-item:hover { background: var(--panel-alt); }
.recent-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
.recent-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.recent-title { font-size: 13px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.recent-meta { font-size: 12px; color: var(--text-dim); text-transform: capitalize; }

.chat-shell {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  min-height: 640px;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.chat-avatar {
  width: 40px; height: 40px; border-radius: 10px;
  background: var(--ink); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px;
}
.chat-title { font-weight: 700; }
.chat-online { font-size: 12px; color: var(--ok); display: flex; align-items: center; gap: 5px; }
.online-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); }

.chat-body { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 14px; }

.chat-hero {
  margin: auto 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  padding: 20px;
}
.chat-hero-avatar {
  width: 64px; height: 64px; border-radius: 16px;
  background: var(--ink); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 20px;
  margin-bottom: 8px;
}
.chat-hero h2 { margin: 0; font-size: 24px; }
.chat-hero p { margin: 0; max-width: 480px; color: var(--text-dim); }

.chat-suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.chat-suggestions.hero { margin-top: 10px; }
.chat-chip {
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 999px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.chat-chip:hover { background: var(--panel-alt); }

.chat-row { display: flex; }
.chat-row.user { justify-content: flex-end; }
.chat-bubble {
  max-width: 70%;
  padding: 12px 14px;
  border-radius: var(--radius-lg);
  font-size: 14px;
  line-height: 1.5;
}
.chat-bubble.bot { background: var(--panel-alt); border: 1px solid var(--border); }
.chat-bubble.user { background: var(--accent); color: #fff; }

.bubble-images { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.bubble-images img { width: 72px; height: 72px; object-fit: cover; border-radius: 8px; }

.filed-complaint { margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,.3); font-size: 13px; }
.chat-bubble.bot .filed-complaint { border-top-color: var(--border); }
.filed-complaint-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }

.typing { display: flex; gap: 4px; padding: 16px 14px; }
.typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim); opacity: .5; animation: blink 1.2s infinite; }
.typing span:nth-child(2) { animation-delay: .2s; }
.typing span:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 80%, 100% { opacity: .3; } 40% { opacity: 1; } }

.helpline-banner.inline {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 16px 10px;
  padding: 10px 14px;
  background: rgba(184,134,11,.1);
  color: var(--warn);
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 600;
}
.helpline-banner.inline a { color: var(--warn); font-weight: 700; }

.composer-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 16px 10px;
}
.attachment-thumb { position: relative; width: 56px; height: 56px; }
.attachment-thumb img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; border: 1px solid var(--border); }
.attachment-remove {
  position: absolute; top: -6px; right: -6px;
  width: 18px; height: 18px; border-radius: 50%;
  border: none; background: var(--ink); color: #fff;
  font-size: 12px; line-height: 1; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.location-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px;
  background: var(--panel-alt);
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
}
.location-chip .attachment-remove { position: static; background: transparent; color: var(--text-dim); }

.chat-input {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-top: 1px solid var(--border);
}
.chat-input input[type="text"], .chat-input input:not([type]) {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 12px 18px;
  font-size: 14px;
  background: var(--panel-alt);
}
.hidden-file-input { display: none; }

.composer-icon-btn {
  width: 40px; height: 40px; flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: #fff;
  color: var(--text-dim);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.composer-icon-btn:hover { background: var(--panel-alt); }
.composer-icon-btn.active { color: var(--accent); border-color: var(--accent); background: var(--accent-glow); }

.composer-send {
  width: 44px; height: 44px; flex-shrink: 0;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.composer-send:hover { background: var(--accent-dark); }

@media (max-width: 900px) {
  .saathi-layout { grid-template-columns: 1fr; }
  .saathi-sidebar { order: 2; }
}
</style>
