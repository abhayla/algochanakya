import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isAuthenticated = ref(false)
  const loading = ref(false)
  const zerodhaLoading = ref(false)
  const angelOneLoading = ref(false)
  const upstoxLoading = ref(false)
  const fyersLoading = ref(false)
  const dhanLoading = ref(false)
  const paytmLoading = ref(false)

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
    zerodhaLoading.value = true
    try {
      const response = await api.get('/api/auth/zerodha/login')
      const loginUrl = response.data.login_url
      window.location.href = loginUrl
      return { success: true }
    } catch (error) {
      zerodhaLoading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to initiate Zerodha login',
      }
    }
  }

  async function initiateAngelOneLogin() {
    angelOneLoading.value = true
    try {
      // AngelOne auth with auto-TOTP can take 20-30 seconds
      const response = await api.post('/api/auth/angelone/login', {}, {
        timeout: 35000  // 35 second timeout
      })
      if (response.data.success && response.data.token) {
        // Store token and redirect
        localStorage.setItem('access_token', response.data.token)
        isAuthenticated.value = true
        // Redirect to callback to complete auth flow
        window.location.href = response.data.redirect_url
        return { success: true }
      } else {
        angelOneLoading.value = false
        return {
          success: false,
          error: response.data.detail || 'Login failed',
        }
      }
    } catch (error) {
      angelOneLoading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to login with Angel One. Make sure SmartAPI credentials are configured in Settings.',
      }
    }
  }

  async function initiateUpstoxLogin() {
    upstoxLoading.value = true
    try {
      const response = await api.get('/api/auth/upstox/login')
      window.location.href = response.data.login_url
      return { success: true }
    } catch (error) {
      upstoxLoading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to initiate Upstox login',
      }
    }
  }

  async function initiateFyersLogin() {
    fyersLoading.value = true
    try {
      const response = await api.get('/api/auth/fyers/login')
      window.location.href = response.data.login_url
      return { success: true }
    } catch (error) {
      fyersLoading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to initiate Fyers login',
      }
    }
  }

  async function initiateDhanLogin(clientId, accessToken) {
    dhanLoading.value = true
    try {
      const response = await api.post('/api/auth/dhan/login', {
        client_id: clientId,
        access_token: accessToken,
      })
      if (response.data.success && response.data.token) {
        localStorage.setItem('access_token', response.data.token)
        isAuthenticated.value = true
        window.location.href = response.data.redirect_url
        return { success: true }
      }
      dhanLoading.value = false
      return { success: false, error: 'Login failed' }
    } catch (error) {
      dhanLoading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to login with Dhan',
      }
    }
  }

  async function initiatePaytmLogin() {
    paytmLoading.value = true
    try {
      const response = await api.get('/api/auth/paytm/login')
      window.location.href = response.data.login_url
      return { success: true }
    } catch (error) {
      paytmLoading.value = false
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to initiate Paytm login',
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
    zerodhaLoading,
    angelOneLoading,
    upstoxLoading,
    fyersLoading,
    dhanLoading,
    paytmLoading,
    login,
    initiateZerodhaLogin,
    initiateAngelOneLogin,
    initiateUpstoxLogin,
    initiateFyersLogin,
    initiateDhanLogin,
    initiatePaytmLogin,
    setToken,
    fetchUser,
    logout,
    checkAuth,
  }
})
