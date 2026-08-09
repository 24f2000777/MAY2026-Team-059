import { defineStore } from 'pinia'
import {
  registerUser as apiRegister,
  verifyOtp as apiVerifyOtp,
  resendOtp as apiResendOtp,
  loginUser as apiLogin,
  logoutUser as apiLogout,
  forgotPassword as apiForgotPassword,
  resetPassword as apiResetPassword,
  updateProfile as apiUpdateProfile,
  changePassword as apiChangePassword
} from '../api/authApi'

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

    async verifyOtpAndLogin({ email, otp }) {
      // verify-otp logs the account in as part of activating it, no
      // separate login call (and no plaintext password) needed here.
      const data = await apiVerifyOtp({ email, otp })
      return this._applySession(data)
    },

    resendOtp({ email }) {
      return apiResendOtp({ email })
    },

    async login({ email, password }) {
      const data = await apiLogin({ email, password })
      return this._applySession(data)
    },

    _applySession(data) {
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

    requestReset(email) {
      return apiForgotPassword({ email })
    },

    completeReset(email, otp, newPassword) {
      return apiResetPassword({ email, otp, newPassword })
    },

    async updateProfile({ name, phone }) {
      const user = await apiUpdateProfile({ name, phone, accessToken: this.accessToken })
      this.user = user
      writeSession({ user: this.user, accessToken: this.accessToken, refreshToken: this.refreshToken })
      return this.user
    },

    changePassword(currentPassword, newPassword) {
      return apiChangePassword({ currentPassword, newPassword, accessToken: this.accessToken })
    }
  }
})
