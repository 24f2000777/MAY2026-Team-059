import { defineStore } from 'pinia'
import {
  requestPasswordReset, resetPassword, updateProfile, changePassword
} from '../api/client'
import {
  registerUser as apiRegister,
  verifyOtp as apiVerifyOtp,
  loginUser as apiLogin,
  logoutUser as apiLogout
} from '../api/authApi'

// Login/register/logout now hit the real backend (see api/authApi.js).
// Profile/password-reset actions below are still on the localStorage
// mock (api/client.js) and haven't been wired up yet.
const SESSION_KEY = 'nagrik_session'

function readSession() {
  const raw = localStorage.getItem(SESSION_KEY)
  return raw ? JSON.parse(raw) : null
}
function writeSession(session) {
  if (session) localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  else localStorage.removeItem(SESSION_KEY)
}

const stored = readSession()

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: stored?.user || null,
    accessToken: stored?.accessToken || null,
    refreshToken: stored?.refreshToken || null
  }),
  getters: {
    isLoggedIn: (state) => !!state.user && !!state.accessToken,
    role: (state) => (state.user ? state.user.role : null)
  },
  actions: {
    async register({ name, phone, email, password }) {
      await apiRegister({ name, phone, email, password })
      // Registration only creates the (unverified) account and sends an
      // email OTP, it doesn't return tokens. Verification + first login
      // happen in verifyOtpAndLogin below.
    },

    async verifyOtpAndLogin({ email, otp, password }) {
      await apiVerifyOtp({ email, otp })
      // verify-otp activates the account but doesn't log the user in;
      // log in right after so the signup flow still ends up authenticated,
      // matching the previous mock behavior.
      return this.login({ email, password })
    },

    async login({ email, password }) {
      const data = await apiLogin({ email, password })
      this.user = data.user
      this.accessToken = data.access_token
      this.refreshToken = data.refresh_token
      writeSession({ user: this.user, accessToken: this.accessToken, refreshToken: this.refreshToken })
      return this.user
    },

    async logout() {
      // Clear local state synchronously (before the first await) so a
      // caller that doesn't await this — navbar.vue calls auth.logout()
      // and immediately router.push('/login') — doesn't race the router
      // guard's isLoggedIn check against a still-pending network call.
      const accessToken = this.accessToken
      const refreshToken = this.refreshToken
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      writeSession(null)
      if (accessToken) {
        try {
          await apiLogout({ accessToken, refreshToken })
        } catch {
          // Local session is already cleared regardless, a failed revoke
          // call just means the token outlives its session server-side
          // until its own expiry, not a stuck "can't log out" screen.
        }
      }
    },

    // --- Not yet wired to the real backend ---
    requestReset(email) {
      return requestPasswordReset(email)
    },
    completeReset(email, newPassword) {
      return resetPassword(email, newPassword)
    },
    updateProfile(details) {
      this.user = updateProfile(this.user.id, details)
      return this.user
    },
    changePassword(currentPassword, newPassword) {
      this.user = changePassword(this.user.id, currentPassword, newPassword)
      return this.user
    }
  }
})
