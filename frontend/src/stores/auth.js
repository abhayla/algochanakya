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

  async function initiateZerodhaLogin() {
    loading.value = true
    try {
      const response = await api.get('/api/auth/zerodha/login')
      const loginUrl = response.data.login_url
      window.location.href = loginUrl
      return { success: true }
    } catch (error) {
      loading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to initiate Zerodha login',
      }
    }
  }

  function setToken(token) {
    localStorage.setItem('access_token', token)
    isAuthenticated.value = true
  }

  async function fetchUser() {
    loading.value = true
    try {
      const response = await api.get('/api/auth/me')
      // Combine user data with broker connection info
      const userData = response.data.user
      const brokerConnections = response.data.broker_connections || []
      const activeBroker = brokerConnections.find(bc => bc.is_active) || brokerConnections[0]

      user.value = {
        ...userData,
        broker_user_id: activeBroker?.broker_user_id || null,
        broker: activeBroker?.broker || null,
        broker_connections: brokerConnections
      }
      isAuthenticated.value = true
      return { success: true }
    } catch (error) {
      user.value = null
      isAuthenticated.value = false
      localStorage.removeItem('access_token')
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to fetch user',
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
      await fetchUser()
    }
  }

  return {
    user,
    isAuthenticated,
    loading,
    login,
    initiateZerodhaLogin,
    setToken,
    fetchUser,
    logout,
    checkAuth,
  }
})
