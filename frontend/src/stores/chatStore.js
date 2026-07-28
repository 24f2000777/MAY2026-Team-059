import { defineStore } from 'pinia'
import { sendChatMessage, getChatHistory } from '../api/chatApi'

// Namespaced per user (not a single shared key) so two different
// accounts logged into the same browser never collide or leak each
// other's conversation history.
function sessionKeyFor(userId) {
  return `nagrik_chat_session_${userId}`
}

function mapHistoryMessage(m) {
  return { from: m.role === 'assistant' ? 'bot' : 'user', text: m.message, createdAt: m.created_at }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessionId: null,
    messages: [],
    isTyping: false,
    error: null,
    historyLoaded: false
  }),
  actions: {
    initSession(userId) {
      const key = sessionKeyFor(userId)
      let sessionId = localStorage.getItem(key)
      if (!sessionId) {
        sessionId = crypto.randomUUID()
        localStorage.setItem(key, sessionId)
      }
      this.sessionId = sessionId
    },

    async loadHistory({ accessToken }) {
      // Fails soft for most errors (a down backend, a hiccup) — the
      // user can still start chatting fresh (the greeting/suggestions
      // just show as if there were no prior history). A 401 specifically
      // is re-thrown: the page is only reachable while logged in, so an
      // expired/invalid token here means the caller should redirect to
      // /login instead of silently showing a "fresh" conversation.
      try {
        const data = await getChatHistory({ sessionId: this.sessionId, accessToken })
        this.messages = data.messages.map(mapHistoryMessage)
      } catch (e) {
        this.error = e.message
        if (e.status === 401) throw e
      } finally {
        this.historyLoaded = true
      }
    },

    // Seeds the role-specific greeting as a real message once, only on a
    // genuinely fresh conversation (no history came back). Doing this
    // here rather than as a component-side fallback means the greeting
    // stays put as the conversation's first line once messages start
    // arriving, instead of disappearing the moment a real message exists.
    seedGreetingIfEmpty(text) {
      if (this.messages.length === 0) {
        this.messages.push({ from: 'bot', text })
      }
    },

    async sendMessage({ text, accessToken }) {
      this.error = null
      this.messages.push({ from: 'user', text })
      this.isTyping = true
      try {
        const data = await sendChatMessage({ sessionId: this.sessionId, message: text, accessToken })
        this.messages.push({ from: 'bot', text: data.reply })
      } catch (e) {
        // Don't fake a bot reply on failure. Store the message for the
        // banner, but re-throw the original error so the component's own
        // catch can inspect e.status (e.g. redirect to /login on a 401).
        this.error = e.message
        throw e
      } finally {
        this.isTyping = false
      }
    },

    reset() {
      this.sessionId = null
      this.messages = []
      this.isTyping = false
      this.error = null
      this.historyLoaded = false
    }
  }
})
