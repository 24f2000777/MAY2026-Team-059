import { defineStore } from 'pinia'
import {
  getSession, loginUser, logoutUser, registerUser,
  requestPasswordReset, resetPassword, updateProfile, changePassword
} from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: getSession()
  }),
  getters: {
    isLoggedIn: (state) => !!state.user,
    role: (state) => (state.user ? state.user.role : null)
  },
  actions: {
    login(credentials) {
      this.user = loginUser(credentials)
      return this.user
    },
    register(details) {
      const user = registerUser(details)
      this.user = user
      return user
    },
    logout() {
      logoutUser()
      this.user = null
    },
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