---
name: websocket-subscription-flow
description: >
  Implement WebSocket subscriptions in Vue components following the project's 4-step pattern:
  connect with JWT, subscribe to channels, handle messages via Pinia stores, cleanup on unmount.
  Use when adding real-time data to a new Vue view or component.
type: workflow
allowed-tools: "Read Grep Glob"
argument-hint: "<feature-name> [--with-fallback]"
version: "1.0.0"
synthesized: true
private: false
source_hash: "websocket-flow-v1"
---

# WebSocket Subscription Flow

Implement real-time WebSocket data in Vue components using the project's established pattern.

**Request:** $ARGUMENTS

---

## STEP 1: Identify the WebSocket Endpoint

Determine which backend WebSocket endpoint to connect to:

| Endpoint | Path | Purpose |
|----------|------|---------|
| Tick data | `ws://localhost:8001/ws/ticks?token=<jwt>` | Live market prices (LTP, bid, ask, volume) |
| AutoPilot | `ws://localhost:8001/ws/autopilot?token=<jwt>` | Strategy updates, order events, condition triggers |

Read the existing composable for your endpoint type:
- Tick data: `frontend/src/composables/useWebSocket.js` (if it exists)
- AutoPilot: `frontend/src/composables/autopilot/useWebSocket.js`

## STEP 2: Create or Extend the Composable

Follow the 4-step pattern observed in `useWebSocket.js`:

### 2a. Connect with JWT

```javascript
import { ref, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useTickerWebSocket() {
  const socket = ref(null)
  const isConnected = ref(false)
  const authStore = useAuthStore()

  function connect() {
    const token = authStore.token || localStorage.getItem('access_token')
    if (!token) return

    const wsUrl = `ws://localhost:8001/ws/ticks?token=${token}`
    socket.value = new WebSocket(wsUrl)

    socket.value.onopen = () => { isConnected.value = true }
    socket.value.onclose = handleClose
    socket.value.onerror = handleError
    socket.value.onmessage = handleMessage
  }
```

### 2b. Subscribe to Channels

```javascript
  function subscribe(tokens, mode = 'quote') {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) return
    socket.value.send(JSON.stringify({
      action: 'subscribe',
      tokens: tokens,  // Array of instrument tokens (e.g., [256265, 260105])
      mode: mode,       // 'ltp' | 'quote' | 'full'
    }))
  }

  function unsubscribe(tokens) {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) return
    socket.value.send(JSON.stringify({
      action: 'unsubscribe',
      tokens: tokens,
    }))
  }
```

### 2c. Handle Messages and Update Store

```javascript
  function handleMessage(event) {
    const data = JSON.parse(event.data)

    // Route to appropriate handler based on message type
    if (data.type === 'tick') {
      // Update the Pinia store with new tick data
      tickStore.updateTick(data.token, data)
    } else if (data.type === 'error') {
      console.error('WebSocket error:', data.message)
    }
  }
```

### 2d. Cleanup on Unmount

```javascript
  function disconnect() {
    if (socket.value) {
      socket.value.close(1000, 'Component unmounted')
      socket.value = null
    }
    isConnected.value = false
  }

  // CRITICAL: Always clean up to prevent memory leaks
  onUnmounted(() => {
    disconnect()
  })

  return { isConnected, connect, subscribe, unsubscribe, disconnect }
}
```

## STEP 3: Add Reconnection Logic

Implement auto-reconnect with exponential backoff:

```javascript
const reconnectAttempts = ref(0)
const MAX_RECONNECT = 5
let reconnectTimer = null

function handleClose(event) {
  isConnected.value = false
  if (event.code !== 1000 && reconnectAttempts.value < MAX_RECONNECT) {
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
    reconnectTimer = setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, delay)
  }
}
```

If `--with-fallback` is requested, add HTTP polling fallback:

```javascript
let pollInterval = null

function startPollingFallback() {
  pollInterval = setInterval(async () => {
    const res = await api.get('/api/v1/quotes', { params: { tokens: subscribedTokens } })
    res.data.forEach(tick => tickStore.updateTick(tick.token, tick))
  }, 3000)
}
```

## STEP 4: Integrate in Vue Component

```vue
<script setup>
import { onMounted } from 'vue'
import { useTickerWebSocket } from '@/composables/useTickerWebSocket'
import { useTickStore } from '@/stores/ticks'

const { isConnected, connect, subscribe } = useTickerWebSocket()
const tickStore = useTickStore()

onMounted(() => {
  connect()
  // Subscribe after connection is established
  setTimeout(() => {
    subscribe([256265, 260105], 'quote')  // NIFTY, BANKNIFTY
  }, 500)
})
</script>

<template>
  <div>
    <span v-if="isConnected" class="status-connected">Live</span>
    <span v-else class="status-disconnected">Reconnecting...</span>
  </div>
</template>
```

## STEP 5: Verify the Integration

1. Start the backend: `cd backend && python run.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Open browser devtools → Network → WS tab
4. Verify: connection opens, subscribe message sent, tick data received
5. Navigate away from the page → verify WebSocket closes cleanly (no console errors)

---

## CRITICAL RULES

- ALWAYS clean up WebSocket connections in `onUnmounted()` — leaked connections cause memory leaks and stale data
- NEVER import `WebSocket` directly in components — use a composable that handles lifecycle
- ALWAYS use JWT token from auth store for authentication — never hardcode tokens
- ALWAYS use instrument tokens (integers like 256265) from centralized constants — never hardcode
- NEVER use `setInterval` for polling without clearing it in cleanup — use the fallback pattern above
- ALWAYS handle `onclose` and `onerror` events — silent WebSocket failures cause stale UI
