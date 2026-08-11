import { defineStore } from 'pinia'
import { sendChatMessage } from '../api/chatApi'
import { uploadAttachment } from '../api/complaintApi'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessionId: null,
    messages: [],
    isTyping: false,
    error: null,

    // GPS coords from the chat's "share location" button, once
    // captured, resent on every message from then on (see sendMessage),
    // since Nagrik Saathi may take several more turns before it has
    // enough to actually file a complaint.
    location: null,

    // Photos picked before a complaint exists to attach them to.
    // Uploaded (via the existing attachment endpoint) the moment a
    // turn actually files a complaint, then cleared. Held as real
    // File objects plus an object URL for the composer preview.
    pendingImages: []
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
      this.location = null
      this.clearPendingImages()
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

    setLocation(coords) {
      this.location = coords
    },

    clearLocation() {
      this.location = null
    },

    addPendingImages(files) {
      for (const file of files) {
        this.pendingImages.push({ file, previewUrl: URL.createObjectURL(file) })
      }
    },

    removePendingImage(index) {
      URL.revokeObjectURL(this.pendingImages[index].previewUrl)
      this.pendingImages.splice(index, 1)
    },

    clearPendingImages() {
      for (const img of this.pendingImages) URL.revokeObjectURL(img.previewUrl)
      this.pendingImages = []
    },

    // Uploads whatever's pending to a complaint that just got filed.
    // Best-effort: the complaint itself is already real at this point,
    // a failed photo upload shouldn't be reported as the whole message
    // having failed. Only the photos that actually made it to the
    // server are cleared from pendingImages though - a silent failure
    // here used to just drop the photo with no way to notice or retry,
    // which is exactly why images could go missing from the staff/admin
    // view despite looking "sent" in the chat. Failures are surfaced via
    // chat.error and the image stays pending so it gets retried on the
    // next turn (or the citizen can remove it manually).
    //
    // Deliberately does NOT revoke the preview object URLs for images
    // that succeeded here: the message this image was attached to
    // (pushed in sendMessage, before this runs) already embeds these
    // exact URL strings to render its thumbnail, revoking now would
    // blank out a photo the citizen can already see they sent. They're
    // only cleaned up once nothing displays them anymore, on the next
    // startNewConversation or explicit removePendingImage.
    async _uploadPendingImages(complaintId, accessToken) {
      if (this.pendingImages.length === 0) return
      const images = this.pendingImages
      const results = await Promise.allSettled(
        images.map((img) => uploadAttachment({ id: complaintId, file: img.file, accessToken }))
      )
      const failedCount = results.filter((r) => r.status === 'rejected').length
      this.pendingImages = images.filter((_, i) => results[i].status === 'rejected')
      if (failedCount > 0) {
        this.error = `Your complaint was filed, but ${failedCount} photo${failedCount > 1 ? 's' : ''} couldn't be attached. Please try again.`
      }
    },

    async sendMessage({ text, accessToken }) {
      this.error = null
      this.messages.push({
        from: 'user',
        text,
        images: this.pendingImages.map((img) => img.previewUrl)
      })
      this.isTyping = true
      try {
        const data = await sendChatMessage({
          sessionId: this.sessionId,
          message: text,
          latitude: this.location?.latitude,
          longitude: this.location?.longitude,
          address: this.location?.address,
          accessToken
        })
        if (data.complaint) {
          await this._uploadPendingImages(data.complaint.id, accessToken)
        }
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
