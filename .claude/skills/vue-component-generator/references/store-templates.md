# Pinia Store Templates

Complete Pinia store patterns for AlgoChanakya using **setup syntax**.

---

## Basic CRUD Store

```javascript
// stores/item.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useItemStore = defineStore('item', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const items = ref([])
  const currentItem = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // ============================================================================
  // GETTERS (Computed)
  // ============================================================================

  const activeItems = computed(() => {
    return items.value.filter(item => item.active)
  })

  const itemById = computed(() => (id) => {
    return items.value.find(item => item.id === id)
  })

  const itemCount = computed(() => items.value.length)

  const hasItems = computed(() => items.value.length > 0)

  // ============================================================================
  // ACTIONS
  // ============================================================================

  async function fetchItems(filters = {}) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.get('/api/items', { params: filters })
      items.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch items'
      console.error('Error fetching items:', err)
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchItemById(id) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.get(`/api/items/${id}`)
      currentItem.value = response.data
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch item'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function createItem(data) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.post('/api/items', data)
      items.value.push(response.data)
      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to create item'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function updateItem(itemId, data) {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.put(`/api/items/${itemId}`, data)

      // Update in items array
      const index = items.value.findIndex(item => item.id === itemId)
      if (index !== -1) {
        items.value[index] = response.data
      }

      // Update currentItem if it's the same
      if (currentItem.value?.id === itemId) {
        currentItem.value = response.data
      }

      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to update item'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function deleteItem(itemId) {
    isLoading.value = true
    error.value = null

    try {
      await api.delete(`/api/items/${itemId}`)

      // Remove from items array
      items.value = items.value.filter(item => item.id !== itemId)

      // Clear currentItem if it was deleted
      if (currentItem.value?.id === itemId) {
        currentItem.value = null
      }

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to delete item'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  function setCurrentItem(item) {
    currentItem.value = item
  }

  function clearCurrentItem() {
    currentItem.value = null
  }

  function clearError() {
    error.value = null
  }

  function $reset() {
    items.value = []
    currentItem.value = null
    isLoading.value = false
    error.value = null
  }

  // ============================================================================
  // RETURN (Public API)
  // ============================================================================

  return {
    // State
    items,
    currentItem,
    isLoading,
    error,

    // Getters
    activeItems,
    itemById,
    itemCount,
    hasItems,

    // Actions
    fetchItems,
    fetchItemById,
    createItem,
    updateItem,
    deleteItem,
    setCurrentItem,
    clearCurrentItem,
    clearError,
    $reset
  }
})
```

---

## Store with WebSocket

```javascript
// stores/liveData.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useLiveDataStore = defineStore('liveData', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const websocket = ref(null)
  const isConnected = ref(false)
  const ticks = ref({})  // token -> tick data
  const subscriptions = ref(new Set())
  const pingInterval = ref(null)
  const reconnectTimeout = ref(null)

  // ============================================================================
  // GETTERS
  // ============================================================================

  const getTickByToken = computed(() => (token) => {
    return ticks.value[token] || null
  })

  const subscriptionCount = computed(() => subscriptions.value.size)

  // ============================================================================
  // ACTIONS
  // ============================================================================

  function connectWebSocket() {
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No access token found')
      return
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_WS_URL || 'localhost:8000'
    const wsUrl = `${wsProtocol}//${wsHost}/ws/ticks?token=${token}`

    try {
      websocket.value = new WebSocket(wsUrl)

      websocket.value.onopen = handleOpen
      websocket.value.onmessage = handleMessage
      websocket.value.onclose = handleClose
      websocket.value.onerror = handleError
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err)
    }
  }

  function handleOpen() {
    console.log('WebSocket connected')
    isConnected.value = true

    // Start keepalive ping
    if (pingInterval.value) {
      clearInterval(pingInterval.value)
    }
    pingInterval.value = setInterval(() => {
      if (websocket.value && isConnected.value) {
        sendMessage({ action: 'ping' })
      }
    }, 30000)

    // Re-subscribe to existing subscriptions
    if (subscriptions.value.size > 0) {
      subscribe(Array.from(subscriptions.value))
    }
  }

  function handleMessage(event) {
    try {
      const message = JSON.parse(event.data)

      switch (message.type) {
        case 'ticks':
          updateTicks(message.data)
          break
        case 'connected':
          console.log('WebSocket connected to backend')
          break
        case 'subscribed':
          console.log('Subscribed to tokens:', message.tokens)
          break
        case 'pong':
          // Keepalive response
          break
        case 'error':
          console.error('WebSocket error:', message.message)
          break
        default:
          console.warn('Unknown message type:', message.type)
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err)
    }
  }

  function handleClose() {
    console.log('WebSocket disconnected')
    isConnected.value = false

    if (pingInterval.value) {
      clearInterval(pingInterval.value)
      pingInterval.value = null
    }

    // Attempt reconnection
    reconnectTimeout.value = setTimeout(() => {
      console.log('Attempting to reconnect...')
      connectWebSocket()
    }, 5000)
  }

  function handleError(err) {
    console.error('WebSocket error:', err)
    isConnected.value = false
  }

  function sendMessage(data) {
    if (websocket.value && isConnected.value) {
      websocket.value.send(JSON.stringify(data))
    }
  }

  function subscribe(tokens, mode = 'ltp') {
    if (!Array.isArray(tokens)) {
      tokens = [tokens]
    }

    // Add to subscriptions set
    tokens.forEach(token => subscriptions.value.add(token))

    // Send subscribe message if connected
    if (isConnected.value) {
      sendMessage({
        action: 'subscribe',
        tokens,
        mode
      })
    }
  }

  function unsubscribe(tokens) {
    if (!Array.isArray(tokens)) {
      tokens = [tokens]
    }

    // Remove from subscriptions set
    tokens.forEach(token => subscriptions.value.delete(token))

    // Send unsubscribe message if connected
    if (isConnected.value) {
      sendMessage({
        action: 'unsubscribe',
        tokens
      })
    }

    // Remove tick data for unsubscribed tokens
    tokens.forEach(token => {
      delete ticks.value[token]
    })
  }

  function updateTicks(ticksData) {
    ticksData.forEach(tick => {
      ticks.value[tick.token] = {
        ltp: tick.ltp,
        change: tick.change,
        change_percent: tick.change_percent,
        volume: tick.volume,
        oi: tick.oi,
        high: tick.high,
        low: tick.low,
        open: tick.open,
        close: tick.close,
        last_updated: Date.now()
      }
    })
  }

  function disconnect() {
    if (pingInterval.value) {
      clearInterval(pingInterval.value)
      pingInterval.value = null
    }

    if (reconnectTimeout.value) {
      clearTimeout(reconnectTimeout.value)
      reconnectTimeout.value = null
    }

    if (websocket.value) {
      websocket.value.close()
      websocket.value = null
    }

    isConnected.value = false
    subscriptions.value.clear()
    ticks.value = {}
  }

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    isConnected,
    ticks,
    subscriptions,

    // Getters
    getTickByToken,
    subscriptionCount,

    // Actions
    connectWebSocket,
    disconnect,
    subscribe,
    unsubscribe,
    updateTicks
  }
})
```

---

## Store with Pagination

```javascript
// stores/paginatedItems.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const usePaginatedItemsStore = defineStore('paginatedItems', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const items = ref([])
  const currentPage = ref(1)
  const pageSize = ref(20)
  const totalItems = ref(0)
  const isLoading = ref(false)
  const error = ref(null)
  const filters = ref({})
  const sortBy = ref('created_at')
  const sortOrder = ref('desc')

  // ============================================================================
  // GETTERS
  // ============================================================================

  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value))

  const hasNextPage = computed(() => currentPage.value < totalPages.value)

  const hasPrevPage = computed(() => currentPage.value > 1)

  const startIndex = computed(() => (currentPage.value - 1) * pageSize.value + 1)

  const endIndex = computed(() => Math.min(currentPage.value * pageSize.value, totalItems.value))

  // ============================================================================
  // ACTIONS
  // ============================================================================

  async function fetchPage(page = currentPage.value) {
    isLoading.value = true
    error.value = null

    try {
      const params = {
        page,
        page_size: pageSize.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        ...filters.value
      }

      const response = await api.get('/api/items', { params })

      items.value = response.data.data || response.data.items || response.data
      currentPage.value = response.data.page || page
      totalItems.value = response.data.total || 0
      pageSize.value = response.data.page_size || pageSize.value

      return { success: true, data: response.data }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch items'
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function goToPage(page) {
    if (page < 1 || page > totalPages.value) return
    return await fetchPage(page)
  }

  async function nextPage() {
    if (!hasNextPage.value) return
    return await fetchPage(currentPage.value + 1)
  }

  async function prevPage() {
    if (!hasPrevPage.value) return
    return await fetchPage(currentPage.value - 1)
  }

  async function setFilters(newFilters) {
    filters.value = { ...newFilters }
    currentPage.value = 1  // Reset to first page when filters change
    return await fetchPage(1)
  }

  async function setSorting(field, order = 'asc') {
    sortBy.value = field
    sortOrder.value = order
    currentPage.value = 1  // Reset to first page when sorting changes
    return await fetchPage(1)
  }

  async function setPageSize(size) {
    pageSize.value = size
    currentPage.value = 1  // Reset to first page when page size changes
    return await fetchPage(1)
  }

  async function refresh() {
    return await fetchPage(currentPage.value)
  }

  function $reset() {
    items.value = []
    currentPage.value = 1
    pageSize.value = 20
    totalItems.value = 0
    isLoading.value = false
    error.value = null
    filters.value = {}
    sortBy.value = 'created_at'
    sortOrder.value = 'desc'
  }

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    items,
    currentPage,
    pageSize,
    totalItems,
    isLoading,
    error,
    filters,
    sortBy,
    sortOrder,

    // Getters
    totalPages,
    hasNextPage,
    hasPrevPage,
    startIndex,
    endIndex,

    // Actions
    fetchPage,
    goToPage,
    nextPage,
    prevPage,
    setFilters,
    setSorting,
    setPageSize,
    refresh,
    $reset
  }
})
```

---

## Store with Local State Management

```javascript
// stores/ui.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const sidebarOpen = ref(true)
  const modals = ref({})  // modalName -> isOpen
  const toasts = ref([])
  const theme = ref(localStorage.getItem('theme') || 'light')
  const loading = ref({})  // componentName -> isLoading

  // ============================================================================
  // GETTERS
  // ============================================================================

  const isModalOpen = computed(() => (modalName) => {
    return modals.value[modalName] || false
  })

  const isLoading = computed(() => (componentName) => {
    return loading.value[componentName] || false
  })

  const isDarkMode = computed(() => theme.value === 'dark')

  const activeToasts = computed(() => toasts.value)

  // ============================================================================
  // ACTIONS
  // ============================================================================

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function openModal(modalName) {
    modals.value[modalName] = true
  }

  function closeModal(modalName) {
    modals.value[modalName] = false
  }

  function toggleModal(modalName) {
    modals.value[modalName] = !modals.value[modalName]
  }

  function showToast(message, type = 'info', duration = 3000) {
    const id = Date.now()
    const toast = { id, message, type }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  function removeToast(id) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function setLoading(componentName, isLoading) {
    loading.value[componentName] = isLoading
  }

  function setTheme(newTheme) {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)

    // Update document class for Tailwind dark mode
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleTheme() {
    setTheme(theme.value === 'light' ? 'dark' : 'light')
  }

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    sidebarOpen,
    modals,
    toasts,
    theme,
    loading,

    // Getters
    isModalOpen,
    isLoading,
    isDarkMode,
    activeToasts,

    // Actions
    toggleSidebar,
    openModal,
    closeModal,
    toggleModal,
    showToast,
    removeToast,
    setLoading,
    setTheme,
    toggleTheme
  }
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'ui-preferences',
        storage: localStorage,
        paths: ['theme', 'sidebarOpen']
      }
    ]
  }
})
```

**Note:** Persistence requires `pinia-plugin-persistedstate` package.

---

## Best Practices

1. **Use Setup Syntax** - Always use `defineStore('name', () => { ... })`
2. **Organize with Comments** - Separate STATE, GETTERS, ACTIONS sections
3. **Return Everything** - Always return state, getters, and actions in return object
4. **Error Handling** - Use try-catch in all async actions
5. **Return Pattern** - Return `{ success, data/error }` from async actions
6. **Computed for Getters** - Use `computed()` for derived state
7. **Ref for State** - Use `ref()` for reactive state
8. **Clear Errors** - Provide actions to clear errors
9. **Reset Function** - Include `$reset()` for resetting state
10. **Use storeToRefs** - In components, destructure with `storeToRefs()` to maintain reactivity

---

## Using Stores in Components

```vue
<script setup>
import { storeToRefs } from 'pinia'
import { useMyStore } from '@/stores/mystore'

// Get store instance
const myStore = useMyStore()

// Destructure state and getters (MUST use storeToRefs for reactivity)
const { items, isLoading, error } = storeToRefs(myStore)

// Actions can be destructured directly (no storeToRefs needed)
const { fetchItems, createItem } = myStore

// Or call actions on store instance
onMounted(() => {
  myStore.fetchItems()
})
</script>
```
