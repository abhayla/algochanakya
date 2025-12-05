<template>
  <div class="min-h-screen bg-white">
    <!-- Navigation Bar -->
    <div class="bg-gray-50 border-b border-gray-200 px-4 py-2">
      <div class="flex items-center gap-4">
        <router-link to="/watchlist" class="text-sm text-blue-600 font-semibold">Watchlist</router-link>
        <router-link to="/optionchain" class="text-sm text-gray-600 hover:text-blue-600">Option Chain</router-link>
        <router-link to="/strategy" class="text-sm text-gray-600 hover:text-blue-600">Strategy Builder</router-link>
      </div>
    </div>

    <!-- Index Header Bar -->
    <div class="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
      <div class="flex items-center space-x-8">
        <!-- NIFTY 50 -->
        <div class="flex items-center space-x-2">
          <span class="text-gray-600 font-medium text-sm">NIFTY 50</span>
          <span :class="niftyClass" class="font-semibold">{{ formatPrice(niftyLtp) }}</span>
          <span :class="niftyClass" class="text-sm">{{ formatChange(niftyChange) }}</span>
          <span :class="niftyClass" class="text-sm">({{ formatPercent(niftyChangePct) }})</span>
        </div>

        <!-- NIFTY BANK -->
        <div class="flex items-center space-x-2">
          <span class="text-gray-600 font-medium text-sm">NIFTY BANK</span>
          <span :class="bankNiftyClass" class="font-semibold">{{ formatPrice(bankNiftyLtp) }}</span>
          <span :class="bankNiftyClass" class="text-sm">{{ formatChange(bankNiftyChange) }}</span>
          <span :class="bankNiftyClass" class="text-sm">({{ formatPercent(bankNiftyChangePct) }})</span>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <span class="text-xs text-gray-400">{{ isConnected ? 'Live' : 'Disconnected' }}</span>
        <span
          class="w-2 h-2 rounded-full"
          :class="isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'"
        ></span>
      </div>
    </div>

    <div class="flex">
      <!-- Left Panel: Watchlist -->
      <div class="w-80 border-r border-gray-200 flex flex-col" style="height: calc(100vh - 50px);">

        <!-- Search Box -->
        <div class="p-3 border-b border-gray-200 relative">
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search eg: infy bse, nifty fut..."
              class="w-full pl-8 pr-4 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:border-blue-500"
              @input="handleSearch"
              @focus="showDropdown = true"
            />
            <svg class="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
          </div>

          <!-- Search Results Dropdown -->
          <div v-if="showDropdown && searchQuery.length >= 2 && searchResults.length > 0"
               class="absolute z-50 left-3 right-3 mt-1 bg-white border border-gray-200 rounded shadow-lg max-h-60 overflow-y-auto">
            <div
              v-for="item in searchResults"
              :key="item.instrument_token"
              @click="addToWatchlist(item)"
              class="px-3 py-2 hover:bg-blue-50 cursor-pointer flex justify-between items-center text-sm"
            >
              <div>
                <span class="font-medium">{{ item.tradingsymbol }}</span>
                <span class="ml-2 text-xs text-gray-500">{{ item.exchange }}</span>
              </div>
              <span v-if="isAdded(item.instrument_token)" class="text-xs text-green-600 font-medium">✓ Added</span>
              <span v-else class="text-xs text-blue-600">+ Add</span>
            </div>
          </div>

          <!-- No results -->
          <div v-if="showDropdown && searchQuery.length >= 2 && searchResults.length === 0 && !isSearching"
               class="absolute z-50 left-3 right-3 mt-1 bg-white border border-gray-200 rounded shadow-lg p-4 text-center text-gray-500 text-sm">
            No instruments found
          </div>
        </div>

        <!-- Watchlist Header -->
        <div class="px-3 py-2 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <span class="text-sm font-medium text-gray-700">{{ activeWatchlist?.name || 'Watchlist' }} ({{ instruments.length }}/100)</span>
          <button @click="showCreateModal = true" class="text-sm text-blue-600 hover:text-blue-700 font-medium">
            + New group
          </button>
        </div>

        <!-- Watchlist Tabs -->
        <div class="flex border-b border-gray-200 bg-white overflow-x-auto">
          <button
            v-for="wl in watchlists"
            :key="wl.id"
            @click="selectWatchlist(wl)"
            :class="[
              'px-3 py-2 text-sm whitespace-nowrap border-b-2 transition-colors',
              activeWatchlist?.id === wl.id
                ? 'border-blue-500 text-blue-600 font-medium bg-blue-50'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
            ]"
          >
            {{ wl.name }}
          </button>
          <button @click="showCreateModal = true" class="px-3 py-2 text-gray-400 hover:text-gray-600 text-lg">
            +
          </button>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="flex justify-center items-center py-20 flex-1">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>

        <!-- Instruments List -->
        <div v-else class="flex-1 overflow-y-auto">
          <!-- Empty State -->
          <div v-if="instruments.length === 0" class="flex flex-col items-center justify-center h-full text-gray-400 p-4">
            <div class="w-16 h-16 mb-4 flex items-center justify-center rounded-full bg-gray-100">
              <svg class="w-8 h-8 text-gray-300" width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
              </svg>
            </div>
            <p class="text-sm">No instruments in this watchlist</p>
            <p class="text-xs mt-1">Use search to add instruments</p>
          </div>

          <!-- Instrument Rows -->
          <div v-else>
            <div
              v-for="inst in instruments"
              :key="inst.token"
              class="px-3 py-2.5 border-b border-gray-100 hover:bg-gray-50 cursor-pointer group"
            >
              <div class="flex items-center justify-between">
                <!-- Symbol -->
                <div class="flex items-center">
                  <span :class="[getChangeColor(inst.token), 'font-medium text-sm']">
                    {{ inst.symbol || inst.tradingsymbol }}
                  </span>
                  <span class="ml-2 text-xs text-gray-400 bg-gray-100 px-1 rounded">
                    {{ inst.exchange }}
                  </span>
                </div>

                <!-- Price Info -->
                <div class="flex items-center space-x-3 text-sm">
                  <span :class="getChangeColor(inst.token)">
                    {{ formatChange(getChange(inst.token)) }}
                  </span>
                  <span :class="[getChangeColor(inst.token), 'flex items-center']">
                    {{ formatPercent(getChangePct(inst.token)) }}
                    <span v-if="getChange(inst.token) > 0" class="ml-0.5">↑</span>
                    <span v-else-if="getChange(inst.token) < 0" class="ml-0.5">↓</span>
                  </span>
                  <span :class="[getChangeColor(inst.token), 'font-semibold w-20 text-right']">
                    {{ formatPrice(getLtp(inst.token)) }}
                  </span>

                  <!-- Remove button -->
                  <button
                    @click.stop="removeFromWatchlist(inst.token)"
                    class="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity"
                  >
                    <svg class="w-4 h-4" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Bottom Pagination -->
        <div v-if="watchlists.length > 1" class="px-3 py-2 border-t border-gray-200 flex items-center space-x-1 bg-gray-50">
          <button
            v-for="(wl, idx) in watchlists.slice(0, 7)"
            :key="wl.id"
            @click="selectWatchlist(wl)"
            :class="[
              'w-7 h-7 text-xs rounded flex items-center justify-center',
              activeWatchlist?.id === wl.id
                ? 'bg-blue-100 text-blue-700 font-semibold'
                : 'text-gray-500 hover:bg-gray-100'
            ]"
          >
            {{ idx + 1 }}
          </button>
        </div>
      </div>

      <!-- Right Panel: Content Area -->
      <div class="flex-1 flex items-center justify-center bg-gray-50" style="height: calc(100vh - 50px);">
        <div class="text-center text-gray-400">
          <div class="w-16 h-16 mx-auto mb-4 flex items-center justify-center rounded-full bg-gray-100">
            <svg class="w-8 h-8 text-gray-400" width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          <p class="text-lg">Select an instrument to view chart</p>
          <p class="text-sm mt-2">Or use the Strategy Builder for options trading</p>
        </div>
      </div>
    </div>

    <!-- Create Watchlist Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50" @click.self="showCreateModal = false">
      <div class="bg-white rounded-lg shadow-xl p-6 w-80">
        <h3 class="text-lg font-semibold mb-4">Create New Watchlist</h3>
        <input
          v-model="newWatchlistName"
          type="text"
          placeholder="Enter watchlist name"
          class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          @keyup.enter="createWatchlist"
        />
        <div class="mt-4 flex justify-end space-x-2">
          <button @click="showCreateModal = false" class="px-4 py-2 text-gray-600 hover:text-gray-800">Cancel</button>
          <button @click="createWatchlist" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWatchlistStore } from '../stores/watchlist'

const store = useWatchlistStore()

// Local state
const searchQuery = ref('')
const showDropdown = ref(false)
const isSearching = ref(false)
const showCreateModal = ref(false)
const newWatchlistName = ref('')
const searchResults = ref([])

// Computed from store
const watchlists = computed(() => store.watchlists)
const activeWatchlist = computed(() => store.activeWatchlist)
const instruments = computed(() => store.activeInstruments || [])
const ticks = computed(() => store.ticks)
const isLoading = computed(() => store.isLoading)
const isConnected = computed(() => store.isConnected)

// Index prices
const niftyLtp = computed(() => ticks.value[256265]?.ltp || 0)
const niftyChange = computed(() => ticks.value[256265]?.change || 0)
const niftyChangePct = computed(() => {
  const tick = ticks.value[256265]
  if (tick?.ltp && tick?.close) return ((tick.ltp - tick.close) / tick.close) * 100
  return tick?.change_percent || 0
})
const niftyClass = computed(() => niftyChange.value >= 0 ? 'text-green-600' : 'text-red-600')

const bankNiftyLtp = computed(() => ticks.value[260105]?.ltp || 0)
const bankNiftyChange = computed(() => ticks.value[260105]?.change || 0)
const bankNiftyChangePct = computed(() => {
  const tick = ticks.value[260105]
  if (tick?.ltp && tick?.close) return ((tick.ltp - tick.close) / tick.close) * 100
  return tick?.change_percent || 0
})
const bankNiftyClass = computed(() => bankNiftyChange.value >= 0 ? 'text-green-600' : 'text-red-600')

// Methods
const getLtp = (token) => ticks.value[token]?.ltp || 0
const getChange = (token) => ticks.value[token]?.change || 0
const getChangePct = (token) => {
  const tick = ticks.value[token]
  if (tick?.ltp && tick?.close) return ((tick.ltp - tick.close) / tick.close) * 100
  return tick?.change_percent || 0
}
const getChangeColor = (token) => {
  const change = getChange(token)
  if (change > 0) return 'text-green-600'
  if (change < 0) return 'text-red-600'
  return 'text-gray-700'
}

const formatPrice = (val) => {
  if (!val) return '--'
  return val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatChange = (val) => {
  if (val === null || val === undefined) return '--'
  return (val >= 0 ? '+' : '') + val.toFixed(2)
}

const formatPercent = (val) => {
  if (val === null || val === undefined) return '--'
  return (val >= 0 ? '+' : '') + val.toFixed(2) + '%'
}

let searchTimeout = null
const handleSearch = () => {
  clearTimeout(searchTimeout)
  if (searchQuery.value.length >= 2) {
    isSearching.value = true
    searchTimeout = setTimeout(async () => {
      const result = await store.searchInstruments(searchQuery.value)
      if (result.success) {
        searchResults.value = result.data
      } else {
        searchResults.value = []
      }
      isSearching.value = false
    }, 300)
  } else {
    searchResults.value = []
  }
}

const isAdded = (token) => {
  return instruments.value.some(i => i.token === token || i.instrument_token === token)
}

const addToWatchlist = async (item) => {
  if (!isAdded(item.instrument_token)) {
    const watchlistId = activeWatchlist.value?.id || store.activeWatchlistId
    if (watchlistId) {
      const result = await store.addInstrument(watchlistId, item.instrument_token)
      if (result.success) {
        searchQuery.value = ''
        showDropdown.value = false
        searchResults.value = []
      }
    }
  }
}

const removeFromWatchlist = async (token) => {
  if (confirm('Remove this instrument from watchlist?')) {
    const watchlistId = activeWatchlist.value?.id || store.activeWatchlistId
    if (watchlistId) {
      await store.removeInstrument(watchlistId, token)
    }
  }
}

const selectWatchlist = (wl) => {
  store.setActiveWatchlist(wl.id)
}

const createWatchlist = async () => {
  if (newWatchlistName.value.trim()) {
    const result = await store.createWatchlist(newWatchlistName.value.trim())
    if (result.success) {
      store.setActiveWatchlist(result.data.id)
    }
    newWatchlistName.value = ''
    showCreateModal.value = false
  }
}

// Click outside to close dropdown
const handleClickOutside = (e) => {
  if (!e.target.closest('.relative')) {
    showDropdown.value = false
  }
}

// Lifecycle
onMounted(async () => {
  await store.fetchWatchlists()
  store.connectWebSocket()
  // Subscribe to indices
  setTimeout(() => {
    store.subscribeToTokens([256265, 260105], 'quote')
  }, 1000)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  store.disconnectWebSocket()
  document.removeEventListener('click', handleClickOutside)
})
</script>
