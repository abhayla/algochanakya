import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isAuthenticated = ref(false)
  const loading = ref(false)

  async function login(credentials) {
    loading.value = true
    try {
      const response = await api.post('/api/auth/broker/login', credentials)
      user.value = response.data.user
      isAuthenticated.value = true
      localStorage.setItem('access_token', response.data.access_token)
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await api.post('/api/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      user.value = null
      isAuthenticated.value = false
      localStorage.removeItem('access_token')
    }
  }

  async function checkAuth() {
    const token = localStorage.getItem('access_token')
    if (token) {
      isAuthenticated.value = true
    }
  }

  return {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
    checkAuth,
  }
})
