import { defineStore } from 'pinia'
import { getSession, loginUser, logoutUser, registerUser } from '../api/client'

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
    }
  }
})