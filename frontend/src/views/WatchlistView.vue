<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Index Header -->
    <IndexHeader />

    <!-- Watchlist Container -->
    <div class="max-w-7xl mx-auto">
      <!-- Watchlist Tabs -->
      <div class="bg-white border-b border-gray-200">
        <div class="flex items-center justify-between px-4">
          <!-- Tabs -->
          <div class="flex gap-1 overflow-x-auto">
            <button
              v-for="watchlist in watchlists"
              :key="watchlist.id"
              @click="setActiveWatchlist(watchlist.id)"
              class="px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap"
              :class="
                activeWatchlistId === watchlist.id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              "
            >
              {{ watchlist.name }}
            </button>

            <!-- Add Watchlist Button (if less than 5) -->
            <button
              v-if="watchlists.length < 5"
              @click="createNewWatchlist"
              class="px-4 py-3 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
            >
              + Add Watchlist
            </button>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2">
            <button
              @click="showSearchModal = true"
              class="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
            >
              + Add Instrument
            </button>
          </div>
        </div>
      </div>

      <!-- Watchlist Content -->
      <div class="bg-white shadow-sm">
        <!-- Loading State -->
        <div v-if="isLoading" class="flex justify-center items-center py-20">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="text-center py-20">
          <p class="text-red-600">{{ error }}</p>
          <button
            @click="loadWatchlists"
            class="mt-4 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            Retry
          </button>
        </div>

        <!-- Empty State -->
        <div v-else-if="!activeWatchlist || activeInstruments.length === 0" class="text-center py-20">
          <svg
            class="w-16 h-16 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p class="text-gray-600 text-lg mb-2">Your watchlist is empty</p>
          <p class="text-gray-500 text-sm mb-6">Add instruments to start tracking prices</p>
          <button
            @click="showSearchModal = true"
            class="px-6 py-3 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            + Add Instruments
          </button>
        </div>

        <!-- Instrument List -->
        <div v-else>
          <!-- Table Header -->
          <div class="flex items-center px-4 py-3 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600 uppercase tracking-wider">
            <div class="flex-1">Instrument</div>
            <div class="w-32 text-right">LTP</div>
            <div class="w-28 text-right">Chg</div>
            <div class="w-24 text-right">Chg %</div>
            <div class="w-8"></div>
          </div>

          <!-- Instrument Rows -->
          <InstrumentRow
            v-for="instrument in activeInstruments"
            :key="instrument.token"
            :instrument="instrument"
            :tick="instrument.tick"
            @delete="handleRemoveInstrument"
          />
        </div>
      </div>
    </div>

    <!-- Search Modal -->
    <InstrumentSearch
      :is-open="showSearchModal"
      @close="showSearchModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWatchlistStore } from '../stores/watchlist'
import IndexHeader from '../components/watchlist/IndexHeader.vue'
import InstrumentRow from '../components/watchlist/InstrumentRow.vue'
import InstrumentSearch from '../components/watchlist/InstrumentSearch.vue'

const watchlistStore = useWatchlistStore()

// State
const showSearchModal = ref(false)

// Computed
const watchlists = computed(() => watchlistStore.watchlists)
const activeWatchlistId = computed(() => watchlistStore.activeWatchlistId)
const activeWatchlist = computed(() => watchlistStore.activeWatchlist)
const activeInstruments = computed(() => watchlistStore.activeInstruments)
const isLoading = computed(() => watchlistStore.isLoading)
const error = computed(() => watchlistStore.error)

// Methods
const loadWatchlists = async () => {
  await watchlistStore.fetchWatchlists()
}

const setActiveWatchlist = (watchlistId) => {
  watchlistStore.setActiveWatchlist(watchlistId)
}

const createNewWatchlist = async () => {
  const name = prompt('Enter watchlist name:', `Watchlist ${watchlists.value.length + 1}`)
  if (!name) return

  const result = await watchlistStore.createWatchlist(name)
  if (result.success) {
    watchlistStore.setActiveWatchlist(result.data.id)
  } else {
    alert(result.error || 'Failed to create watchlist')
  }
}

const handleRemoveInstrument = async (instrumentToken) => {
  if (!confirm('Remove this instrument from watchlist?')) {
    return
  }

  const watchlistId = activeWatchlistId.value
  if (!watchlistId) return

  const result = await watchlistStore.removeInstrument(watchlistId, instrumentToken)
  if (!result.success) {
    alert(result.error || 'Failed to remove instrument')
  }
}

// Lifecycle
onMounted(async () => {
  // Load watchlists
  await loadWatchlists()

  // Connect to WebSocket for live prices
  watchlistStore.connectWebSocket()
})

onUnmounted(() => {
  // Disconnect WebSocket
  watchlistStore.disconnectWebSocket()
})
</script>
