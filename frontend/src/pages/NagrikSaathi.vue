<script setup>
import { ref, nextTick, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useChatStore } from '../stores/chatStore'
import { getMyComplaints } from '../api/complaintApi'
import { reverseGeocode } from '../utils/geocode'
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
    async (position) => {
      const { latitude, longitude } = position.coords
      // Reverse geocoded here so the bot gets a real address instead of
      // having to guess one from whatever's typed - see conversation_graph.py,
      // a shared GPS pin skips its usual "is this specific enough" checks
      // entirely and trusts this address outright. Still set the coords even
      // if geocoding itself fails (address stays null), so the backend can
      // fall back to the ordinary typed-text flow for that turn instead of
      // silently trusting an address it doesn't actually have.
      const address = await reverseGeocode(latitude, longitude)
      chat.setLocation({ latitude, longitude, address })
    },
    () => {
      chat.error = 'Could not get your location. You can still describe it in your message.'
    }
  )
}

async function send() {
  let text = draft.value.trim()

  // A photo or a shared location on their own are valid messages (the
  // citizen may just want to show/point at something), the backend
  // still needs some non-empty text though, so fall back to a
  // placeholder rather than blocking send entirely when there's
  // nothing typed but a photo or location is attached.
  if (!text && chat.pendingImages.length > 0) {
    text = 'Sharing a photo.'
  } else if (!text && chat.location) {
    text = 'Sharing my location.'
  }

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
                  <router-link :to="`/citizen/${m.complaint.id}`" class="filed-complaint-view">
                    View Complaint
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                  </router-link>
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
/* Saathi page */

.saathi-page {
  min-height: calc(100vh - 80px);
  padding: 18px 24px 90px;
  background:
    radial-gradient(circle at 85% 10%, rgba(47, 143, 91, .06), transparent 28%),
    var(--bg);
}

.saathi-layout {
  width: min(1480px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 235px minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
  min-height: calc(100vh - 116px);
}

/* Sidebar */

.saathi-sidebar {
  background: rgba(255, 255, 255, .88);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px 12px;
  box-shadow: 0 8px 28px rgba(22, 48, 31, .05);
  backdrop-filter: blur(8px);
}

.sidebar-heading {
  margin: 6px 10px 9px;
  color: var(--text-dim);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .1em;
  text-transform: uppercase;
}

.sidebar-heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 24px;
  padding-right: 10px;
}

.sidebar-heading-row .sidebar-heading {
  margin-bottom: 0;
}

.new-link {
  color: var(--accent);
  text-decoration: none;
  font-size: 12px;
  font-weight: 800;
}

.new-link:hover {
  color: var(--accent-dark);
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.quick-action {
  position: relative;
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 42px;
  padding: 10px 11px;
  border-radius: 11px;
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  font-weight: 650;
  transition:
    background .18s ease,
    color .18s ease,
    transform .18s ease;
}

.quick-action svg {
  flex-shrink: 0;
  color: var(--text-dim);
  transition: color .18s ease;
}

.quick-action:hover {
  background: var(--panel-alt);
  transform: translateX(2px);
}

.quick-action:hover svg {
  color: var(--accent);
}

.quick-action.router-link-active {
  background: rgba(47, 143, 91, .1);
  color: var(--accent-dark);
}

.quick-action.router-link-active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 9px;
  bottom: 9px;
  width: 3px;
  border-radius: 4px;
  background: var(--accent);
}

.quick-action.router-link-active svg {
  color: var(--accent);
}

.quick-action.emergency {
  margin-top: 5px;
  color: #9a6700;
}

.quick-action.emergency svg {
  color: #b8860b;
}

.quick-action.emergency:hover {
  background: rgba(184, 134, 11, .09);
  transform: none;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 8px;
}

.recent-empty {
  margin: 5px 10px;
  color: var(--text-dim);
  font-size: 12px;
}

.recent-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 9px 10px;
  border-radius: 10px;
  color: var(--text);
  text-decoration: none;
  transition: background .18s ease;
}

.recent-item:hover {
  background: var(--panel-alt);
}

.recent-dot {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(47, 143, 91, .07);
}

.recent-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.recent-title {
  overflow: hidden;
  color: var(--text);
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-meta {
  color: var(--text-dim);
  font-size: 11px;
  text-transform: capitalize;
}

/* Chat shell */

.chat-shell {
  min-width: 0;
  min-height: 0;
  height: calc(100vh - 116px);
  background: rgba(255, 255, 255, .94);
  border: 1px solid var(--border);
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 35px rgba(22, 48, 31, .07);
}

/* Chat header */

.chat-header {
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, .92);
}

.chat-avatar {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ink);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 4px 12px rgba(22, 48, 31, .12);
}

.chat-title {
  color: var(--text);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
}

.chat-online {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 3px;
  color: var(--ok);
  font-size: 11px;
  font-weight: 600;
}

.online-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 3px rgba(42, 157, 143, .1);
}

/* Chat body */

.chat-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 24px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background:
    radial-gradient(circle at 50% 0%, rgba(47, 143, 91, .025), transparent 40%),
    #fcfdfb;
  scroll-behavior: smooth;
}

.chat-body::-webkit-scrollbar {
  width: 6px;
}

.chat-body::-webkit-scrollbar-track {
  background: transparent;
}

.chat-body::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 10px;
}

/* Chat hero */

.chat-hero {
  width: min(560px, 100%);
  margin: auto;
  padding: 30px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.chat-hero-avatar {
  width: 62px;
  height: 62px;
  margin-bottom: 14px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ink);
  color: #fff;
  font-size: 19px;
  font-weight: 800;
  box-shadow: 0 10px 25px rgba(22, 48, 31, .13);
}

.chat-hero h2 {
  margin: 0 0 7px;
  color: var(--text);
  font-size: 23px;
  font-weight: 850;
  letter-spacing: -.02em;
}

.chat-hero p {
  max-width: 500px;
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.65;
}

.chat-suggestions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.chat-suggestions.hero {
  margin-top: 20px;
}

.chat-chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 9px 14px;
  background: #fff;
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background .18s ease,
    border-color .18s ease,
    transform .18s ease,
    box-shadow .18s ease;
}

.chat-chip:hover {
  border-color: rgba(47, 143, 91, .35);
  background: var(--panel-alt);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(22, 48, 31, .06);
}

/* Messages */

.chat-row {
  display: flex;
  width: 100%;
}

.chat-row.bot {
  justify-content: flex-start;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-bubble {
  max-width: min(680px, 72%);
  padding: 11px 14px;
  border-radius: 15px;
  font-size: 15px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.chat-bubble.bot {
  background: #f7faf6;
  border: 1px solid var(--border);
  border-bottom-left-radius: 5px;
  color: var(--text);
}

.chat-bubble.user {
  background: var(--accent);
  border-bottom-right-radius: 5px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(47, 143, 91, .12);
}

.bubble-images {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.bubble-images img {
  width: 76px;
  height: 76px;
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, .25);
  border-radius: 9px;
}

/* Complaint summary */

.filed-complaint {
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid rgba(255, 255, 255, .3);
  font-size: 12px;
}

.chat-bubble.bot .filed-complaint {
  border-top-color: var(--border);
}

.filed-complaint-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.filed-complaint-row + .filed-complaint-row {
  margin-top: 5px;
}

.filed-complaint .priority {
  color: var(--accent-dark);
  font-weight: 700;
}

.filed-complaint-view {
  margin-top: 9px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--accent-dark);
  text-decoration: none;
  font-size: 12px;
  font-weight: 700;
}

.filed-complaint-view:hover {
  text-decoration: underline;
}

.chat-bubble.bot .filed-complaint-view {
  color: var(--accent-dark);
}

/* Typing indicator */

.typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 14px 15px;
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-dim);
  opacity: .35;
  animation: saathi-typing 1.2s infinite;
}

.typing span:nth-child(2) {
  animation-delay: .18s;
}

.typing span:nth-child(3) {
  animation-delay: .36s;
}

@keyframes saathi-typing {
  0%, 80%, 100% {
    opacity: .3;
    transform: translateY(0);
  }

  40% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

/* Error */

.saathi-page > .error-text,
.chat-shell > .error-text {
  color: var(--danger);
}

/* Helpline */

.helpline-banner.inline {
  margin: 0 18px 8px;
  padding: 9px 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid rgba(184, 134, 11, .22);
  border-radius: 10px;
  background: rgba(184, 134, 11, .07);
  color: #8a650b;
  font-size: 11px;
  font-weight: 650;
}

.helpline-banner.inline svg {
  flex-shrink: 0;
}

.helpline-banner.inline a {
  color: #8a650b;
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Composer attachments */

.composer-attachments {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 18px 9px;
}

.attachment-thumb {
  position: relative;
  width: 52px;
  height: 52px;
}

.attachment-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border: 1px solid var(--border);
  border-radius: 9px;
}

.attachment-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ink);
  color: #fff;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
}

.location-chip {
  min-height: 34px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid rgba(47, 143, 91, .2);
  border-radius: 999px;
  background: rgba(47, 143, 91, .07);
  color: var(--accent-dark);
  font-size: 11px;
  font-weight: 700;
}

.location-chip .attachment-remove {
  position: static;
  width: 17px;
  height: 17px;
  background: transparent;
  color: var(--text-dim);
}

/* Composer */

.chat-input {
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 11px 16px;
  border-top: 1px solid var(--border);
  background: #fff;
}

.chat-input input[type="text"],
.chat-input input:not([type]) {
  flex: 1;
  min-width: 0;
  height: 44px;
  padding: 11px 17px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: #f8faf7;
  color: var(--text);
  font-size: 15px;
}

.chat-input input::placeholder {
  color: #8a9588;
}

.chat-input input:focus {
  background: #fff;
}

.hidden-file-input {
  display: none;
}

.composer-icon-btn {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: var(--text-dim);
  cursor: pointer;
  transition:
    background .18s ease,
    color .18s ease,
    border-color .18s ease,
    transform .18s ease;
}

.composer-icon-btn:hover {
  border-color: rgba(47, 143, 91, .3);
  background: var(--panel-alt);
  color: var(--accent);
  transform: translateY(-1px);
}

.composer-icon-btn.active {
  border-color: rgba(47, 143, 91, .35);
  background: var(--accent-glow);
  color: var(--accent);
}

.composer-send {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(47, 143, 91, .18);
  transition:
    background .18s ease,
    transform .18s ease,
    box-shadow .18s ease;
}

.composer-send:hover {
  background: var(--accent-dark);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(47, 143, 91, .22);
}

/* Navbar */

.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 22px;
  background: rgba(255, 255, 255, .94);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(22, 48, 31, .035);
  backdrop-filter: blur(12px);
}

.navbar > * {
  flex-shrink: 0;
}

.navbar a {
  text-decoration: none;
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 650;
  padding: 9px 13px;
  border-radius: 999px;
  transition:
    background .18s ease,
    color .18s ease;
}

.navbar a:hover {
  background: var(--panel-alt);
  color: var(--text);
}

.navbar a.router-link-active {
  background: rgba(47, 143, 91, .1);
  color: var(--accent-dark);
  font-weight: 750;
}

.navbar a:first-child {
  margin-right: 12px;
  padding-left: 8px;
  color: var(--ink);
  font-size: 16px;
  font-weight: 850;
  letter-spacing: .04em;
}

.navbar a:first-child:hover {
  background: transparent;
}

.navbar button {
  border: 1px solid var(--border);
  background: #fff;
  color: var(--text-dim);
  cursor: pointer;
  transition:
    background .18s ease,
    border-color .18s ease,
    color .18s ease;
}

.navbar button:hover {
  background: var(--panel-alt);
  border-color: #cbdac7;
  color: var(--ink);
}

/* Footer */

footer {
  margin: 0 8px 8px;
  min-height: 42px;
  border-radius: 14px;
  background: #607568;
  color: rgba(255, 255, 255, .88);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .01em;
}

/* Responsive */

@media (max-width: 1050px) {
  .saathi-layout {
    grid-template-columns: 210px minmax(0, 1fr);
  }

  .chat-bubble {
    max-width: 78%;
  }
}

@media (max-width: 850px) {
  .saathi-page {
    padding: 12px;
  }

  .saathi-layout {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .saathi-sidebar {
    order: 2;
  }

  .chat-shell {
    order: 1;
    height: calc(100vh - 92px);
    min-height: 600px;
  }

  .quick-actions {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }

  .sidebar-heading-row,
  .recent-list {
    display: none;
  }
}

@media (max-width: 600px) {
  .navbar {
    min-height: 60px;
    padding: 0 12px;
    overflow-x: auto;
  }

  .navbar a {
    padding: 8px 9px;
    font-size: 12px;
  }

  .navbar a:first-child {
    margin-right: 3px;
    font-size: 14px;
  }

  .saathi-page {
    padding: 8px;
  }

  .chat-shell {
    height: calc(100vh - 76px);
    min-height: 560px;
    border-radius: 15px;
  }

  .chat-header {
    padding: 11px 14px;
  }

  .chat-body {
    padding: 16px 12px;
  }

  .chat-bubble {
    max-width: 88%;
    font-size: 14px;
  }

  .chat-input {
    padding: 9px 10px;
  }

  .composer-icon-btn {
    width: 37px;
    height: 37px;
  }

  .composer-send {
    width: 40px;
    height: 40px;
  }

  .chat-input input[type="text"],
  .chat-input input:not([type]) {
    padding-left: 14px;
    padding-right: 14px;
  }

  .helpline-banner.inline {
    margin-left: 10px;
    margin-right: 10px;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>