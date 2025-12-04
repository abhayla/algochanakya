<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-start justify-center bg-black bg-opacity-50 pt-20"
    @click.self="close"
  >
    <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Search & Add Instruments</h2>
        <button
          @click="close"
          class="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Search Input -->
      <div class="px-6 py-4 border-b border-gray-200">
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          placeholder="Search by symbol or name (e.g., NIFTY, RELIANCE)..."
          class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          autofocus
        />
      </div>

      <!-- Filter Tabs -->
      <div class="flex gap-2 px-6 py-3 border-b border-gray-200 bg-gray-50">
        <button
          v-for="filter in filters"
          :key="filter.value"
          @click="activeFilter = filter.value"
          class="px-4 py-1.5 text-sm font-medium rounded transition-colors"
          :class="
            activeFilter === filter.value
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-100'
          "
        >
          {{ filter.label }}
        </button>
      </div>

      <!-- Results -->
      <div class="max-h-96 overflow-y-auto">
        <!-- Loading -->
        <div v-if="isSearching" class="flex justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>

        <!-- No Query -->
        <div v-else-if="!searchQuery" class="text-center py-12 text-gray-500">
          <svg
            class="w-12 h-12 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <p>Start typing to search instruments</p>
        </div>

        <!-- No Results -->
        <div v-else-if="searchResults.length === 0 && !isSearching" class="text-center py-12 text-gray-500">
          <p>No instruments found for "{{ searchQuery }}"</p>
        </div>

        <!-- Results List -->
        <div v-else>
          <div
            v-for="instrument in searchResults"
            :key="instrument.instrument_token"
            class="flex items-center justify-between px-6 py-3 hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-100"
            @click="addInstrument(instrument)"
          >
            <div class="flex-1">
              <div class="flex items-center gap-2">
                <span class="font-medium text-gray-900">{{ instrument.tradingsymbol }}</span>
                <span class="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                  {{ instrument.exchange }}
                </span>
                <span v-if="instrument.segment" class="text-xs text-gray-500">
                  {{ instrument.segment }}
                </span>
              </div>
              <div class="text-xs text-gray-500 mt-1">
                {{ instrument.name || instrument.tradingsymbol }}
              </div>
            </div>

            <!-- Already Added Badge -->
            <div v-if="isInWatchlist(instrument.instrument_token)">
              <span class="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
                ✓ Added
              </span>
            </div>

            <!-- Add Button -->
            <button
              v-else
              class="px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
              @click.stop="addInstrument(instrument)"
            >
              + Add
            </button>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
        <span class="text-sm text-gray-600">
          {{ instrumentCount }} / 100 instruments
        </span>
        <button
          @click="close"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useWatchlistStore } from '../../stores/watchlist'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['close'])

const watchlistStore = useWatchlistStore()

// State
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
const activeFilter = ref('all')

// Debounce timer
let searchTimeout = null

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Cash', value: 'NSE' },
  { label: 'F&O', value: 'NFO' }
]

// Computed
const instrumentCount = computed(() => {
  return watchlistStore.activeWatchlist?.instruments?.length || 0
})

// Methods
const handleSearch = () => {
  // Clear previous timeout
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }

  // Set new timeout (debounce)
  searchTimeout = setTimeout(async () => {
    if (searchQuery.value.length < 1) {
      searchResults.value = []
      return
    }

    isSearching.value = true

    try {
      const exchange = activeFilter.value !== 'all' ? activeFilter.value : null
      const result = await watchlistStore.searchInstruments(searchQuery.value, exchange)

      if (result.success) {
        searchResults.value = result.data
      } else {
        searchResults.value = []
      }
    } catch (error) {
      console.error('Search error:', error)
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }, 300) // 300ms debounce
}

const addInstrument = async (instrument) => {
  if (isInWatchlist(instrument.instrument_token)) {
    return
  }

  const watchlistId = watchlistStore.activeWatchlistId
  if (!watchlistId) {
    console.error('No active watchlist')
    return
  }

  const result = await watchlistStore.addInstrument(watchlistId, instrument.instrument_token)

  if (result.success) {
    console.log('Instrument added successfully')
  } else {
    console.error('Failed to add instrument:', result.error)
    alert(result.error || 'Failed to add instrument')
  }
}

const isInWatchlist = (instrumentToken) => {
  const watchlist = watchlistStore.activeWatchlist
  if (!watchlist || !watchlist.instruments) return false

  return watchlist.instruments.some(inst => inst.token === instrumentToken)
}

const close = () => {
  emit('close')
  searchQuery.value = ''
  searchResults.value = []
}

// Watch filter changes
watch(activeFilter, () => {
  if (searchQuery.value) {
    handleSearch()
  }
})
</script>
