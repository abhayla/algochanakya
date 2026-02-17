import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'

export const useWatchlistStore = defineStore('watchlist', () => {
  // State
  const watchlists = ref([])
  const activeWatchlistId = ref(null)
  const instruments = ref({}) // token -> full instrument data
  const ticks = ref({}) // token -> latest tick {ltp, change, change_percent}
  const websocket = ref(null)
  const isConnected = ref(false)
  const pingInterval = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const activeWatchlist = computed(() =>
    watchlists.value.find(w => w.id === activeWatchlistId.value)
  )

  const activeInstruments = computed(() => {
    const watchlist = activeWatchlist.value
    if (!watchlist || !watchlist.instruments) return []

    return watchlist.instruments.map(inst => ({
      ...inst,
      ...instruments.value[inst.token],
      tick: ticks.value[inst.token] || { ltp: null, change: null, change_percent: null }
    }))
  })

  const indexTicks = computed(() => ({
    nifty50: ticks.value[256265] || { ltp: null, change: null, change_percent: null },
    niftyBank: ticks.value[260105] || { ltp: null, change: null, change_percent: null },
    finnifty: ticks.value[257801] || { ltp: null, change: null, change_percent: null },
    sensex: ticks.value[265] || { ltp: null, change: null, change_percent: null }
  }))

  // Actions
  async function fetchWatchlists() {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.get('/api/watchlists')
      watchlists.value = response.data

      // Set first watchlist as active if none selected
      if (watchlists.value.length > 0 && !activeWatchlistId.value) {
        activeWatchlistId.value = watchlists.value[0].id
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch watchlists'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function createWatchlist(name) {
    try {
      const response = await api.post('/api/watchlists', { name })
      watchlists.value.push(response.data)
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create watchlist'
      return { success: false, error: error.value }
    }
  }

  async function updateWatchlist(watchlistId, data) {
    try {
      const response = await api.put(`/api/watchlists/${watchlistId}`, data)
      const index = watchlists.value.findIndex(w => w.id === watchlistId)
      if (index !== -1) {
        watchlists.value[index] = response.data
      }
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update watchlist'
      return { success: false, error: error.value }
    }
  }

  async function deleteWatchlist(watchlistId) {
    try {
      await api.delete(`/api/watchlists/${watchlistId}`)
      watchlists.value = watchlists.value.filter(w => w.id !== watchlistId)

      // Set new active watchlist if deleted was active
      if (activeWatchlistId.value === watchlistId && watchlists.value.length > 0) {
        activeWatchlistId.value = watchlists.value[0].id
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete watchlist'
      return { success: false, error: error.value }
    }
  }

  async function addInstrument(watchlistId, instrumentToken) {
    try {
      const response = await api.post(
        `/api/watchlists/${watchlistId}/instruments`,
        { instrument_token: instrumentToken }
      )

      // Update watchlist in store
      const index = watchlists.value.findIndex(w => w.id === watchlistId)
      if (index !== -1) {
        watchlists.value[index] = response.data
      }

      // Subscribe to WebSocket updates for this instrument
      if (isConnected.value) {
        subscribeToTokens([instrumentToken])
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to add instrument'
      return { success: false, error: error.value }
    }
  }

  async function removeInstrument(watchlistId, instrumentToken) {
    try {
      const response = await api.delete(
        `/api/watchlists/${watchlistId}/instruments/${instrumentToken}`
      )

      // Update watchlist in store
      const index = watchlists.value.findIndex(w => w.id === watchlistId)
      if (index !== -1) {
        watchlists.value[index] = response.data
      }

      // Unsubscribe from WebSocket updates
      if (isConnected.value) {
        unsubscribeFromTokens([instrumentToken])
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to remove instrument'
      return { success: false, error: error.value }
    }
  }

  async function searchInstruments(query, exchange = null) {
    try {
      const params = { q: query }
      if (exchange) params.exchange = exchange

      const response = await api.get('/api/instruments/search', { params })
      return { success: true, data: response.data }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || 'Search failed'
      }
    }
  }

  function connectWebSocket() {
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No access token found')
      return
    }

    // Construct WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_WS_URL || 'localhost:8000'
    const wsUrl = `${wsProtocol}//${wsHost}/ws/ticks?token=${token}`

    try {
      websocket.value = new WebSocket(wsUrl)

      websocket.value.onopen = () => {
        console.log('WebSocket connected')
        isConnected.value = true

        // Start keepalive ping every 30 seconds
        if (pingInterval.value) {
          clearInterval(pingInterval.value)
        }
        pingInterval.value = setInterval(() => {
          if (websocket.value && isConnected.value) {
            websocket.value.send(JSON.stringify({ action: 'ping' }))
          }
        }, 30000)

        // Subscribe to indices after a brief delay to ensure connection is ready
        setTimeout(() => {
          subscribeToTokens([256265, 260105], 'quote') // NIFTY 50, NIFTY BANK with full data

          // Subscribe to watchlist instruments
          if (activeWatchlist.value) {
            const tokens = activeWatchlist.value.instruments.map(inst => inst.token)
            if (tokens.length > 0) {
              subscribeToTokens(tokens, 'quote')
            }
          }
        }, 500)
      }

      websocket.value.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          if (message.type === 'ticks') {
            // Update tick data (array of ticks from backend)
            for (const tickData of message.data) {
              ticks.value[tickData.token] = {
                ltp: tickData.ltp,
                change: tickData.change,
                change_percent: tickData.change_percent,
                volume: tickData.volume,
                oi: tickData.oi,
                high: tickData.high,
                low: tickData.low,
                open: tickData.open,
                close: tickData.close
              }
            }
          } else if (message.type === 'connected') {
            console.log('WebSocket connected to backend:', message.message)
            console.log('Kite connected:', message.kite_connected)
          } else if (message.type === 'subscribed') {
            console.log('Subscribed to tokens:', message.tokens)
          } else if (message.type === 'unsubscribed') {
            console.log('Unsubscribed from tokens:', message.tokens)
          } else if (message.type === 'pong') {
            // Keepalive response - no action needed
          } else if (message.type === 'error') {
            console.error('WebSocket error:', message.message)
            error.value = message.message
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      websocket.value.onclose = () => {
        console.log('WebSocket disconnected')
        isConnected.value = false

        // Attempt reconnection after 5 seconds
        setTimeout(() => {
          if (!isConnected.value) {
            console.log('Attempting to reconnect...')
            connectWebSocket()
          }
        }, 5000)
      }

      websocket.value.onerror = (err) => {
        console.error('WebSocket error:', err)
        isConnected.value = false
      }
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err)
      error.value = 'Failed to connect to live data stream'
    }
  }

  function subscribeToTokens(tokens, mode = 'ltp') {
    if (!websocket.value || !isConnected.value) {
      console.warn('WebSocket not connected')
      return
    }

    websocket.value.send(JSON.stringify({
      action: 'subscribe',
      tokens: tokens,
      mode: mode
    }))
  }

  function unsubscribeFromTokens(tokens) {
    if (!websocket.value || !isConnected.value) {
      return
    }

    websocket.value.send(JSON.stringify({
      action: 'unsubscribe',
      tokens: tokens
    }))
  }

  function disconnectWebSocket() {
    if (pingInterval.value) {
      clearInterval(pingInterval.value)
      pingInterval.value = null
    }
    if (websocket.value) {
      // Nullify onclose to prevent the old handler from triggering auto-reconnect
      websocket.value.onclose = null
      websocket.value.close()
      websocket.value = null
      isConnected.value = false
    }
  }

  // Update tick data for a token (used for API fallback when WebSocket isn't available)
  function updateTick(token, tickData) {
    ticks.value[token] = {
      ...ticks.value[token],
      ltp: tickData.ltp,
      change: tickData.change,
      change_percent: tickData.change_percent
    }
  }

  function setActiveWatchlist(watchlistId) {
    // Unsubscribe from old watchlist instruments
    if (activeWatchlist.value) {
      const oldTokens = activeWatchlist.value.instruments.map(inst => inst.token)
      if (oldTokens.length > 0 && isConnected.value) {
        unsubscribeFromTokens(oldTokens)
      }
    }

    // Set new active watchlist
    activeWatchlistId.value = watchlistId

    // Subscribe to new watchlist instruments
    const watchlist = watchlists.value.find(w => w.id === watchlistId)
    if (watchlist) {
      const tokens = watchlist.instruments.map(inst => inst.token)
      if (tokens.length > 0 && isConnected.value) {
        subscribeToTokens(tokens)
      }
    }
  }

  return {
    // State
    watchlists,
    activeWatchlistId,
    instruments,
    ticks,
    isConnected,
    isLoading,
    error,

    // Getters
    activeWatchlist,
    activeInstruments,
    indexTicks,

    // Actions
    fetchWatchlists,
    createWatchlist,
    updateWatchlist,
    deleteWatchlist,
    addInstrument,
    removeInstrument,
    searchInstruments,
    connectWebSocket,
    subscribeToTokens,
    unsubscribeFromTokens,
    disconnectWebSocket,
    setActiveWatchlist,
    updateTick
  }
})
