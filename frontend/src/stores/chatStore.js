import { defineStore } from 'pinia'
import { sendChatMessage } from '../api/chatApi'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessionId: null,
    messages: [],
    isTyping: false,
    error: null
  }),
  actions: {
    // Starts a brand new conversation, a fresh session id every time.
    // Nagrik Saathi is meant to open blank on purpose, so a returning
    // citizen lands ready to file a new complaint rather than staring
    // at last time's transcript. Their past complaints are still all
    // there on the dashboard regardless, this only affects the chat
    // window itself, nothing is deleted server side.
    startNewConversation() {
      this.sessionId = crypto.randomUUID()
      this.messages = []
      this.isTyping = false
      this.error = null
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
        this.messages.push({ from: 'bot', text: data.reply, complaint: data.complaint ?? null })
      } catch (e) {
        // Don't fake a bot reply on failure. Store the message for the
        // banner, but re-throw the original error so the component's own
        // catch can inspect e.status (e.g. redirect to /login on a 401).
        this.error = e.message
        throw e
      } finally {
        this.isTyping = false
      }
    }
  }
})
